import os
import sys
import time
import json
import logging
import django
from web3 import Web3
from django.db.models import F
import requests

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Output ra console (Render logs)
    ]
)
logger = logging.getLogger('indexer')

# Cấu hình để script chạy độc lập có thể truy cập Database của Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import transaction, close_old_connections
from election.models import Election, Candidate, VoteRecord, SystemLog, IndexerState, WhitelistVoter

from dotenv import load_dotenv
load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))

# Tải ABI từ file JSON tĩnh ở thư mục gốc
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    with open(os.path.join(BASE_DIR, "Factory_ABI.json"), "r", encoding="utf-8") as f:
        FACTORY_ABI = json.load(f)

    with open(os.path.join(BASE_DIR, "Election_ABI.json"), "r", encoding="utf-8") as f:
        ELECTION_ABI = json.load(f)
except FileNotFoundError:
    logger.critical("❌ Không tìm thấy file Factory_ABI.json hoặc Election_ABI.json ở thư mục gốc!")
    sys.exit(1)

# Địa chỉ Factory Contract (tự động trích xuất từ file deployed_addresses.json)
from election.utils import get_factory_address
FACTORY_ADDRESS = get_factory_address()

factory_contract = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)

def get_last_processed_block():
    try:
        state, created = IndexerState.objects.get_or_create(key='main')
        if created or state.last_block == 0:
            # Nếu chưa có trạng thái, lấy từ biến môi trường START_BLOCK (nếu có), không thì lấy current block
            start_block = os.environ.get('START_BLOCK')
            if start_block and start_block.isdigit():
                return int(start_block)
            return w3.eth.block_number
        return state.last_block
    except Exception as e:
        logger.error(f"Lỗi lấy trạng thái Indexer từ DB: {e}")
        return w3.eth.block_number

def update_last_block(block_num):
    try:
        IndexerState.objects.filter(key='main').update(last_block=block_num)
    except Exception as e:
        logger.error(f"Lỗi lưu trạng thái Indexer vào DB: {e}")

from web3.exceptions import TransactionNotFound

def check_broadcasted_transactions():
    # Giới hạn 50 bản ghi mỗi vòng để tránh ngốn RPC calls khi nhiều tx stuck
    # 1. Election
    for election in Election.objects.filter(tx_status='broadcasted')[:50]:
        try:
            receipt = w3.eth.get_transaction_receipt(election.tx_hash)
            if receipt.status == 1:
                election.tx_status = 'confirmed'

                # TH1: Tạo hòm phiếu mới (chưa có contract_addr)
                if not election.contract_addr:
                    logs = factory_contract.events.ElectionCreated().process_receipt(receipt)
                    if logs:
                        election.contract_addr = logs[0]['args']['electionAddress']
                        SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Tạo hòm phiếu {election.name} thành công. Contract: {election.contract_addr}')

                # TH2: Đổi trạng thái hòm phiếu (dùng event ElectionStatusChanged — KHÔNG dùng hack tx_error)
                else:
                    election_contract = w3.eth.contract(
                        address=election.contract_addr, abi=ELECTION_ABI
                    )
                    status_logs = election_contract.events.ElectionStatusChanged().process_receipt(receipt)
                    if status_logs:
                        is_open = status_logs[0]['args']['isOpen']
                        new_status = 'active' if is_open else 'closed'
                        election.status = new_status
                        election.tx_error = ''
                        SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Đổi trạng thái hòm phiếu {election.name} thành "{new_status}" qua event.')
                        from election.tasks import broadcast_update
                        broadcast_update(election.id)
            else:
                election.tx_status = 'failed'
                election.tx_error = 'Transaction Reverted on-chain'
                SystemLog.objects.create(level='ERROR', module='BLOCKCHAIN', message=f'Giao dịch Election {election.name} bị Reverted!')
            election.save()
        except TransactionNotFound:
            pass  # Vẫn đang pending
        except Exception as e:
            logger.error(f"Lỗi kiểm tra receipt Election: {e}")

    # 2. Candidate
    for candidate in Candidate.objects.filter(tx_status='broadcasted')[:50]:
        try:
            receipt = w3.eth.get_transaction_receipt(candidate.tx_hash)
            if receipt.status == 1:
                candidate.tx_status = 'confirmed'
                election_contract = w3.eth.contract(address=candidate.election.contract_addr, abi=ELECTION_ABI)
                logs = election_contract.events.CandidateAdded().process_receipt(receipt)
                if logs:
                    candidate.candidate_id = logs[0]['args']['candidateId']
                SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Thêm ứng viên {candidate.name} thành công.')
                from election.tasks import broadcast_update
                broadcast_update(candidate.election.id)
            else:
                candidate.tx_status = 'failed'
                candidate.tx_error = 'Transaction Reverted on-chain'
                SystemLog.objects.create(level='ERROR', module='BLOCKCHAIN', message=f'Giao dịch thêm ứng viên {candidate.name} bị Reverted!')
            candidate.save()
        except TransactionNotFound:
            pass
        except Exception as e:
            logger.error(f"Lỗi kiểm tra receipt Candidate: {e}")

    # 3. WhitelistVoter
    for wl in WhitelistVoter.objects.filter(tx_status='broadcasted')[:50]:
        try:
            receipt = w3.eth.get_transaction_receipt(wl.tx_hash)
            if receipt.status == 1:
                wl.tx_status = 'confirmed'
                SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Thêm whitelist {wl.voter_address} thành công.')
            else:
                wl.tx_status = 'failed'
                wl.tx_error = 'Transaction Reverted on-chain'
                SystemLog.objects.create(level='ERROR', module='BLOCKCHAIN', message=f'Giao dịch thêm whitelist {wl.voter_address} bị Reverted!')
            wl.save()
        except TransactionNotFound:
            pass
        except Exception as e:
            logger.error(f"Lỗi kiểm tra receipt Whitelist: {e}")

def process_events():
    check_broadcasted_transactions()
    try:
        from_block = get_last_processed_block()
        current_block = w3.eth.block_number
    except Exception as e:
        logger.error(f"Lỗi kết nối RPC (Alchemy): {e}")
        return
    
    if from_block > current_block:
        return
        
    # Giới hạn Alchemy Free Tier: Chỉ cho phép quét tối đa 10 block mỗi lần (tính cả 2 đầu)
    MAX_BLOCK_RANGE = 9
    if current_block - from_block > MAX_BLOCK_RANGE:
        current_block = from_block + MAX_BLOCK_RANGE
        
    logger.info(f"Quét từ block {from_block} → {current_block}...")
    has_error = False

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
            logger.info(f"✅ Hòm phiếu mới: {name} tại {contract_addr}")
            SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Event ElectionCreated: Hòm phiếu {name} được tạo tại {contract_addr[:10]}...')
    except Exception as e:
        logger.error(f"Lỗi quét Factory: {e}")
        has_error = True

    # 2. Lắng nghe Event: Bỏ phiếu (VoteCast) trên tất cả hòm phiếu đang hoạt động
    elections = Election.objects.exclude(status='closed').exclude(contract_addr__isnull=True)
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
                        
                        # Lấy voter address trực tiếp từ event (KHÔNG cần gọi get_transaction() — tiết kiệm 1 RPC call/phiếu)
                        voter_address = evt.args.voter
                        
                        # KIỂM TRA: Ứng viên phải tồn tại trong DB, nếu không thì bỏ qua phiếu này (Ngăn lỗi nuốt phiếu)
                        if not Candidate.objects.filter(election=election, candidate_id=candidate_id).exists():
                            logger.warning(f"⚠️  Candidate ID {candidate_id} chưa có trong DB, bỏ qua tx {tx_hash[:10]}")
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
                        
                        logger.info(f"🔥 Phếu mới xác nhận: Tx {tx_hash[:10]}... (Candidate {candidate_id})")
                        SystemLog.objects.create(level='SUCCESS', module='BLOCKCHAIN', message=f'Event VoteCast: Có phiếu mới cho Ứng viên ID {candidate_id}. Tx: {tx_hash[:10]}...')
                        
                        # --- Bắn tín hiệu WebSocket (Real-time) cho Frontend qua API ---
                        try:
                            server_port = os.environ.get('PORT', 8000)
                            # FIX: ưu tiên INTERNAL_API_SECRET, fallback về DJANGO_SECRET_KEY
                            secret = os.environ.get('INTERNAL_API_SECRET') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default')
                            requests.post(f"http://127.0.0.1:{server_port}/api/internal/notify_vote/", json={
                                "election_id": election.id,
                                "candidate_id": candidate_id,
                                "tx_hash": tx_hash
                            }, headers={'X-Internal-Secret': secret}, timeout=2)
                        except Exception as req_err:
                            logger.warning(f"Lỗi gọi Webhook notify_vote: {req_err}")
                except Exception as db_err:
                    logger.error(f"Lỗi Database Transaction khi xử lý phiếu: {db_err}")
                    has_error = True
                    
        except Exception as e:
            logger.error(f"Lỗi quét Election {election.id}: {e}")
            has_error = True

    # Chỉ cập nhật block nếu không có lỗi nào xảy ra (Tránh nhảy block khi bị RPC Rate Limit)
    if not has_error:
        update_last_block(current_block + 1)

# Vòng lập chạy vô hạn 24/7
if __name__ == "__main__":
    logger.info("🚀 Indexer khởi động thành công")
    while True:
        close_old_connections()
        process_events()
        time.sleep(5)  # Nghỉ 5 giây tránh rate-limit Alchemy
