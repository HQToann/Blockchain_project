# 🟢 NGÀY 7: THIẾT KẾ INDEXER ĐỂ LẮNG NGHE BLOCKCHAIN

Hôm nay là sự kết hợp giữa **Kỹ sư Blockchain** và **Kỹ sư Backend**. Indexer là một "cỗ máy" chạy ngầm, không ngừng theo dõi mạng lưới Blockchain, và cập nhật Database ngay lập tức khi phát hiện có giao dịch bầu cử.

> 🛠️ **Mẹo:** Bài toán hóc búa nhất của Indexer là làm sao để khi hệ thống sập nguồn bật lại, nó không cộng phiếu 2 lần cho 1 giao dịch. Chúng ta sẽ dùng `transaction.atomic()` của Django để giải quyết.

---

## BƯỚC 1: Lấy URL RPC từ Alchemy
Để Python "Nói chuyện" được với mạng Sepolia, chúng ta cần đi qua cầu nối Alchemy.

1. Vào [Alchemy.com](https://www.alchemy.com/), tạo tài khoản.
2. Tạo App mới: Chain = Ethereum, Network = Sepolia.
3. Lấy chuỗi **HTTPS URL** (Ví dụ: `https://eth-sepolia.g.alchemy.com/v2/XYZ...`) và lưu vào file `.env`:

```env
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/xyz...
```

---

## BƯỚC 2: Cài đặt Indexer Script

Tạo một thư mục `indexer` ngay trong thư mục gốc của dự án (`decentralized_voting`), ngang hàng với file `manage.py`.
Bên trong thư mục `indexer`, tạo 2 file: `indexer.py` và `last_block.txt`.

> ⚠️ **QUAN TRỌNG — KHÔNG điền số `1` vào `last_block.txt`!**
> Nếu điền số `1`, Indexer sẽ cố quét từ Block số 1 của Sepolia (từ năm 2022) đến hiện tại → mất vài tiếng và bị Alchemy chặn vì vượt Rate Limit.

**Cách lấy số block hiện tại để điền vào:**
1. Đảm bảo đã điền `ALCHEMY_RPC_URL` vào file `.env` (xem Bước 1).
2. Kích hoạt môi trường ảo (`pipenv shell`) rồi chạy lệnh sau:
```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import os; from web3 import Web3; w3=Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL'))); print('Block hiện tại:', w3.eth.block_number)"
```
3. Copy số block in ra và dán vào file `last_block.txt` rồi lưu lại.

---

## BƯỚC 3: Viết logic Indexer (Đoạn code "Ăn Tiền")

Mở file `indexer/indexer.py` và dán mã sau:

```python
import os
import sys
import time
import requests
import django
from web3 import Web3
from django.db.models import F  # Import F để cộng phiếu an toàn (tránh race condition)

# Cấu hình để script chạy độc lập có thể truy cập Database của Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import transaction
from election.models import Election, Candidate, VoteRecord

# Tải cấu hình từ .env
from dotenv import load_dotenv
load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))

# TODO: Thay thế bằng địa chỉ Factory và ABI bạn đã lưu ở Ngày 1
FACTORY_ADDRESS = "0x..." 
FACTORY_ABI = '[...]' 
ELECTION_ABI = '[...]'

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
    from_block = get_last_processed_block()
    current_block = w3.eth.block_number
    
    if from_block > current_block:
        return
        
    print(f"[*] Quét từ block {from_block} đến {current_block}...")
    has_error = False  # Cờ theo dõi lỗi để tránh mất event (Lỗi #9)

    # 1. Lắng nghe Event: Tạo hòm phiếu mới (ElectionCreated)
    try:
        election_events = factory_contract.events.ElectionCreated.get_logs(fromBlock=from_block, toBlock=current_block)
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
    except Exception as e:
        print("Lỗi quét Factory:", e)
        has_error = True

    # 2. Lắng nghe Event: Bỏ phiếu (VoteCast) trên tất cả hòm phiếu
    elections = Election.objects.all()
    for election in elections:
        poll_contract = w3.eth.contract(address=election.contract_addr, abi=ELECTION_ABI)
        try:
            vote_events = poll_contract.events.VoteCast.get_logs(fromBlock=from_block, toBlock=current_block)
            
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
                        
                        # BÁO CÁO QUA WEBHOOK CHO DJANGO (Giải quyết lỗi Cross-Process trên Production)
                        try:
                            # Django Server chạy ở cổng 8000
                            requests.post(
                                "http://127.0.0.1:8000/api/internal/notify_vote/",
                                json={"election_id": election.id},
                                timeout=2
                            )
                        except Exception as req_err:
                            print("Lỗi khi gọi Webhook WebSocket:", req_err)
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
        process_events()
        time.sleep(5) # Nghỉ 5 giây tránh dính rate-limit của Alchemy
```

---
## BƯỚC 4: Chạy thử
1. Mở một Terminal mới (Nhớ kích hoạt `pipenv shell`).
2. Gõ lệnh: `python indexer/indexer.py`.
3. Nếu bạn thấy màn hình hiện *"🚀 Khởi động Indexer..."* và quét block, tức là hệ thống tim đập của bạn đã sống!

Vào lúc này, nếu bạn vào trang **Admin Dashboard** (`/dashboard/`), đăng nhập Web3 và bấm **"Tạo cuộc bầu cử mới"**, Indexer sẽ chộp được ngay và tự động chèn vào PostgreSQL!
