import os
import sys
import time
import django
from web3 import Web3
from django.db.models import F  # Import F để cộng phiếu an toàn (tránh race condition)
import requests

# Cấu hình để script chạy độc lập có thể truy cập Database của Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import transaction, close_old_connections
from election.models import Election, Candidate, VoteRecord, SystemLog

# Tải cấu hình từ .env
from dotenv import load_dotenv
load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))

import json

# Tự động tải ABI từ thư mục artifacts do Hardhat sinh ra
try:
    with open("artifacts/contracts/VotingSystem.sol/ElectionFactory.json", "r", encoding="utf-8") as f:
        FACTORY_ABI = json.load(f)["abi"]

    with open("artifacts/contracts/VotingSystem.sol/Election.json", "r", encoding="utf-8") as f:
        ELECTION_ABI = json.load(f)["abi"]
except FileNotFoundError:
    print("❌ Lỗi: Không tìm thấy file ABI! Bạn cần chạy 'npx hardhat compile' trước.")
    sys.exit(1)

# Địa chỉ Factory Contract (tự động trích xuất từ file deployed_addresses.json)
FACTORY_ADDRESS = "0x44F8Db431EA5049D60547777Af54a0D7E46D12DE"

factory_contract = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)

def get_last_processed_block():
    try:
        with open("indexer/last_block.txt", "r") as f:
            return int(f.read().strip())
    except:
        return w3.eth.block_number

def update_last_block(block_num):
    with open("indexer/last_block.txt", "w") as f:
        f.write(str(block_num))

def process_events():
    try:
        from_block = get_last_processed_block()
        current_block = w3.eth.block_number
    except Exception as e:
        print("Lỗi kết nối RPC (Alchemy):", e)
        return
    
    if from_block > current_block:
        return
        
    # Giới hạn Alchemy Free Tier: Chỉ cho phép quét tối đa 10 block mỗi lần (tính cả 2 đầu)
    MAX_BLOCK_RANGE = 9
    if current_block - from_block > MAX_BLOCK_RANGE:
        current_block = from_block + MAX_BLOCK_RANGE
        
    print(f"[*] Quét từ block {from_block} đến {current_block}...")
    has_error = False  # Cờ theo dõi lỗi để tránh mất event (Lỗi #9)

    # 1. Lắng nghe Event: Tạo hòm phiếu mới (ElectionCreated)
    try:
        election_events = factory_contract.events.ElectionCreated.get_logs(from_block=from_block, to_block=current_block)
        for evt in election_events:
            contract_addr = evt.args.electionAddress
            name = evt.args.name
            is_private = evt.args.isPrivate # Lấy từ event (Lỗi #10)
            
            # Lưu vào Database
            Election.objects.get_or_create(
                contract_addr=contract_addr,
                defaults={'name': name, 'status': 'pending', 'is_private': is_private}
            )
            print(f"✅ Đã tạo cuộc bầu cử mới: {name} ở địa chỉ {contract_addr}")
            SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Event ElectionCreated: Hòm phiếu {name} được tạo tại {contract_addr[:10]}...')
    except Exception as e:
        print("Lỗi quét Factory:", e)
        has_error = True

    # 2. Lắng nghe Event: Bỏ phiếu (VoteCast) trên tất cả hòm phiếu
    elections = Election.objects.all()
    for election in elections:
        poll_contract = w3.eth.contract(address=election.contract_addr, abi=ELECTION_ABI)
        try:
            vote_events = poll_contract.events.VoteCast.get_logs(from_block=from_block, to_block=current_block)
            
            for evt in vote_events:
                tx_hash = evt.transactionHash.hex()
                block_num = evt.blockNumber
                candidate_id = evt.args.candidateId
                
                # --- PHẦN BẢO MẬT: TRANSACTION ATOMIC ---
                try:
                    with transaction.atomic():
                        # Kiểm tra xem tx_hash này đã được xử lý chưa (chống cộng trùng phiếu)
                        if VoteRecord.objects.filter(tx_hash=tx_hash).exists():
                            continue # Bỏ qua nếu đã xử lý
                        
                        # (Tuỳ chọn) Gọi get_transaction để lấy địa chỉ người vote
                        # Tránh lạm dụng để không dính Rate Limit
                        tx_info = w3.eth.get_transaction(tx_hash)
                        voter_address = tx_info['from']
                        
                        # KIỂM TRA: Ứng viên phải tồn tại trong DB, nếu không thì bỏ qua phiếu này (Ngăn lỗi nuốt phiếu)
                        if not Candidate.objects.filter(election=election, candidate_id=candidate_id).exists():
                            print(f"⚠️ Cảnh báo: Candidate {candidate_id} chưa tồn tại trong DB, bỏ qua tx {tx_hash}")
                            continue

                        # Ghi nhận lịch sử (KHÔNG lưu candidate_id)
                        VoteRecord.objects.create(
                            election=election,
                            voter_address=voter_address,
                            tx_hash=tx_hash,
                            block_number=block_num
                        )
                        
                        # Cộng phiếu (dùng F() để tránh race condition khi nhiều vote đến cùng lúc)
                        Candidate.objects.filter(
                            election=election,
                            candidate_id=candidate_id
                        ).update(vote_count=F('vote_count') + 1)
                        
                        print(f"🔥 Cập nhật phiếu thành công cho Tx: {tx_hash}")
                        SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Event VoteCast: Có phiếu mới cho Ứng viên ID {candidate_id}. Tx: {tx_hash[:10]}...')
                        
                        # --- Bắn tín hiệu WebSocket (Real-time) cho Frontend qua API ---
                        try:
                            requests.post(f"http://127.0.0.1:8000/api/internal/notify_vote/", json={
                                "election_id": election.id,
                                "candidate_id": candidate_id,
                                "tx_hash": tx_hash
                            }, timeout=2)
                        except Exception as req_err:
                            print(f"Lỗi gọi API Webhook: {req_err}")
                except Exception as db_err:
                    print(f"Lỗi Database Transaction: {db_err}")
                    has_error = True
                    
        except Exception as e:
            print("Lỗi quét Election:", e)
            has_error = True

    # Chỉ cập nhật block nếu không có lỗi nào xảy ra (Tránh nhảy block khi bị RPC Rate Limit)
    if not has_error:
        update_last_block(current_block + 1)

# Vòng lặp chạy vô hạn 24/7
if __name__ == "__main__":
    print("🚀 Khởi động Indexer...")
    while True:
        # Đóng các kết nối CSDL đã cũ để tránh lỗi "server closed the connection unexpectedly" trên PostgreSQL
        close_old_connections()
        
        process_events()
        time.sleep(5) # Nghỉ 5 giây tránh dính rate-limit của Alchemy
