# 6. HƯỚNG DẪN CÀI ĐẶT & CHẠY LOCAL

> Tài liệu này dành cho người muốn chạy toàn bộ hệ thống trên máy cá nhân (Windows).

---

## Yêu Cầu Hệ Thống

| Phần mềm | Phiên bản | Ghi chú |
|:---|:---|:---|
| **Python** | >= 3.11 | Bắt buộc |
| **Node.js** | >= 18.x | Dành cho Hardhat (compile contract) |
| **Pipenv** | Latest | `pip install pipenv` |
| **Redis** | Latest | Cần thiết cho RQ Worker + WebSocket |
| **MetaMask** | Extension Chrome/Firefox | Kết nối ví |
| **Alchemy Account** | Free | Lấy RPC URL Sepolia |
| **Supabase Account** | Free | PostgreSQL đám mây (hoặc dùng SQLite local) |
| **Pinata Account** | Free | IPFS lưu ảnh ứng viên |

---

## Bước 1: Clone & Cài Thư Viện

```bash
# Clone dự án
git clone https://github.com/YOUR_USERNAME/Blockchain_Project.git
cd Blockchain_Project

# Cài Python dependencies
pipenv install

# Kích hoạt môi trường ảo
pipenv shell

# Cài Node dependencies (cho Hardhat)
npm install
```

---

## Bước 2: Cấu Hình File `.env`

Tạo file `.env` ở thư mục gốc (copy từ `.env.example`):

```bash
copy .env.example .env   # Windows
```

Điền các giá trị sau:

```env
# Lấy từ Alchemy (tạo App → Sepolia)
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY

# Lấy từ MetaMask (Account Details → Export Private Key)
# ⚠️ TUYỆT ĐỐI không dùng ví có tiền thật!
PRIVATE_KEY=your_private_key_here

# Địa chỉ ví công khai của admin (để đăng nhập)
ADMIN_WALLET_ADDRESSES=0xYourWalletAddress

# Lấy từ Pinata Cloud (API Keys → New Key → Generate JWT)
PINATA_JWT=eyJhbGci...

# Dùng SQLite để test local không cần Supabase
USE_SQLITE=True

# Django Secret Key (tạo ngẫu nhiên)
DJANGO_SECRET_KEY=django-insecure-xxxxxxxxxxxxxxxxxxxxx

# Secret nội bộ (khác với DJANGO_SECRET_KEY)
INTERNAL_API_SECRET=random_secret_string_here

SESSION_COOKIE_AGE=86400
```

---

## Bước 3: Khởi Tạo Database

```bash
# Tạo bảng
python manage.py migrate

# (Tuỳ chọn) Tạo superuser để vào Django Admin
python manage.py createsuperuser
```

---

## Bước 4: Deploy Smart Contract lên Sepolia

```bash
# Compile contract
npx hardhat compile

# Deploy lên Sepolia (cần ETH testnet trong ví admin)
npx hardhat ignition deploy ignition/modules/VotingSystem.js --network sepolia
```

Sau khi deploy, lấy địa chỉ `ElectionFactory` và cập nhật vào database qua Django Admin hoặc file `utils.py`.

---

## Bước 5: Cài Redis (Windows)

**Cách 1 — WSL (Khuyến nghị):**
```bash
# Trong WSL Ubuntu
sudo apt install redis-server
sudo service redis-server start
```

**Cách 2 — Redis cho Windows:**
Tải từ [https://github.com/microsoftarchive/redis/releases](https://github.com/microsoftarchive/redis/releases)

---

## Bước 6: Khởi Động Hệ Thống

### Cách nhanh (1 click):
```bat
start_local.bat
```
→ Tự động mở 3 cửa sổ Terminal: Django · RQ Worker · Indexer

### Thủ công (3 Terminal riêng):
```bash
# Terminal 1 — Web Server
pipenv run daphne -b 127.0.0.1 -p 8000 core.asgi:application

# Terminal 2 — Background Task Worker
pipenv run python manage.py rqworker default

# Terminal 3 — Blockchain Indexer
pipenv run python indexer/indexer.py
```

---

## Bước 7: Truy Cập Hệ Thống

| URL | Mô tả |
|:---|:---|
| `http://127.0.0.1:8000/` | Trang chủ — Danh sách bầu cử |
| `http://127.0.0.1:8000/election/<id>/` | Trang chi tiết bầu cử |
| `http://127.0.0.1:8000/verify/` | Xác minh phiếu bằng TxHash |
| `http://127.0.0.1:8000/admin/` | Django Admin Panel |
| `http://127.0.0.1:8000/logs/` | System Logs (Admin only) |

---

## Lưu Ý Quan Trọng

> [!WARNING]
> **MetaMask:** Đảm bảo đang kết nối mạng **Sepolia Testnet** (Chain ID: 11155111). Nếu dùng mạng khác, hệ thống sẽ từ chối kết nối.

> [!NOTE]
> **Lần đầu đăng nhập Admin:** Hệ thống sẽ tự động seed địa chỉ ví từ `ADMIN_WALLET_ADDRESSES` vào Database khi Admin đăng nhập lần đầu. Sau đó có thể quản lý thêm/bớt admin trực tiếp từ trang `/admin/election/adminwallet/`.

> [!TIP]
> **Không có Redis?** Đặt `USE_SQLITE=True` trong `.env` và bỏ qua Terminal 2 (RQ Worker). Hệ thống vẫn chạy nhưng các tác vụ blockchain sẽ không được xử lý ngầm.

---

## Chạy Unit Tests

```bash
pipenv run python manage.py test election.tests --keepdb
```

3 test cases hiện có:
1. `test_get_election_detail` — Kiểm tra API trả đúng dữ liệu (kể cả `voters` và `is_private`)
2. `test_internal_notify_vote` — Kiểm tra bảo mật webhook nội bộ
3. `test_check_broadcasted_transactions_confirmed` — Kiểm tra Indexer xử lý đúng TX confirmed
