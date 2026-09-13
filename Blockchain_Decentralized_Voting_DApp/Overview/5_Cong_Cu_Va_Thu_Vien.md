# 5. CÔNG CỤ & THƯ VIỆN SỬ DỤNG (TECH STACK)

---

## 5.1. Bảng Tech Stack Đầy Đủ

### 🔗 Tầng Blockchain (On-chain)
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Solidity** | ^0.8.20 | Ngôn ngữ viết Smart Contract |
| **OpenZeppelin Contracts** | v5 | Thư viện bảo mật chuẩn công nghiệp (`Ownable`, `Pausable`) |
| **Hardhat** | ^2.22.x | Môi trường viết, compile và deploy Contract trực tiếp trên VS Code |
| **Sepolia Testnet** | — | Mạng Ethereum thử nghiệm, phí Gas là tiền giả (faucet) |
| **MetaMask** | Latest | Ví điện tử để ký giao dịch, đóng vai Cử tri và Admin |
| **Alchemy** | — | Nhà cung cấp RPC Node kết nối vào mạng Sepolia |

### 🖥️ Tầng Backend (Off-chain)
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Python** | >= 3.11 | Ngôn ngữ lập trình chính cho Backend và Indexer |
| **Django** | 5.x | Web Framework xây dựng API thuần bằng `JsonResponse` và `View` |
| **PostgreSQL** | 16.x | Hệ quản trị CSDL lưu dữ liệu Off-chain |
| **psycopg2-binary** | Latest | Driver kết nối Django với PostgreSQL |
| **Web3.py** | 7.x | Thư viện Python kết nối Blockchain cho script Indexer |
| **requests** | Latest | Gọi API Pinata để upload ảnh lên IPFS |
| **python-dotenv** | Latest | Tải biến môi trường bảo mật từ file `.env` |
| **Pipenv** | Latest | Quản lý môi trường ảo và thư viện Python |

### 🎨 Tầng Frontend
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **HTML5 + CSS3** | — | Khung giao diện web |
| **Vanilla JavaScript** | ES2022+ | Xử lý logic, gọi API |
| **Ethers.js** | v6 (CDN) | Kết nối MetaMask, gọi hàm Smart Contract |
| **Chart.js** | v4 (CDN) | Vẽ biểu đồ cột/tròn kết quả Real-time |

### ☁️ Dịch vụ Ngoài
| Dịch vụ | Vai trò |
|:---|:---|
| **Pinata Cloud (IPFS)** | Lưu trữ ảnh ứng viên phân tán (Chống kiểm duyệt) |
| **Django Channels + Redis** | Hỗ trợ WebSockets, đẩy dữ liệu Real-time xuống trình duyệt |
| **eth-account** | Xác thực chữ ký số MetaMask (Web3 Auth) tại Backend |
| **Etherscan (Sepolia)** | Tra cứu công khai giao dịch bỏ phiếu |

---

## 5.2. Cấu Trúc Thư Mục Chuẩn Mực

Dựa trên chuẩn cấu trúc dự án Django thực tế, hệ thống sẽ gộp Frontend và Backend chung vào một thư mục dự án duy nhất. Django sẽ đóng vai trò phục vụ (serve) các file HTML/JS từ thư mục `templates` và `static`, đồng thời cung cấp API qua ứng dụng `election`.

```text
decentralized_voting/                 # Thư mục gốc dự án
│
├── core/                             # Thư mục cấu hình Project chính
│   ├── settings.py                   # Cấu hình chính: DB, CORS, ASGI, Channel Layer
│   ├── urls.py                       # Router chính của toàn ứng dụng
│   ├── asgi.py                       # Cấu hình ASGI — Cần thiết cho WebSockets!
│   └── wsgi.py                       # Cấu hình WSGI truyền thống (không dùng khi chạy daphne)
│
├── election/                         # App nghiệp vụ bầu cử
│   ├── models.py                     # Election, Candidate, VoteRecord, WhitelistVoter
│   ├── selectors.py                  # Logic đọc DB (VD: đếm phiếu, tính %)
│   ├── services.py                   # Logic nghiệp vụ (VD: gọi API Pinata)
│   ├── views.py                      # CHỄ xử lý HTTP Request/Response (JSON)
│   ├── consumers.py                  # Xử lý kết nối WebSocket (Django Channels)
│   ├── routing.py                    # Định tuyến WebSocket (ws/election/<id>/)
│   ├── urls.py                       # Định tuyến /api/elections/...
│   └── admin.py                      # Đăng ký vào trang Django Admin
│
├── indexer/                          # Thư mục chứa script độc lập
│   ├── indexer.py                    # Script chạy ngầm nghe Event Blockchain
│   └── last_block.txt                # Checkpoint số block đã xử lý (KHÔNG điền số 1!)
│
├── templates/                        # Giao diện người dùng (HTML)
│   ├── index.html                    # Trang danh sách cuộc bầu cử
│   ├── detail.html                   # Trang chi tiết bỏ phiếu + biểu đồ
│   └── admin_dashboard.html          # Trang quản trị tùy chỉnh
│
├── static/                           # File tĩnh (JS, CSS, Ảnh)
│   └── js/
│       ├── app.js                    # Logic Ethers.js + Fetch API chính
│       ├── charts.js                 # Logic Chart.js
│       └── config.js                 # CONTRACT_ADDRESS, ABI (import từ JSON)
│
├── contracts/                        # Nơi lưu trữ code Solidity
│   ├── VotingSystem.sol              # Chứa cả ElectionFactory + Election
│   ├── Factory_ABI.json              # ABI của ElectionFactory
│   └── Election_ABI.json             # ABI của hợp đồng con Election
│
├── .env                              # Biến bảo mật (KHÔNG đẩy lên GitHub)
├── .env.example                      # Mẫu biến môi trường
├── .gitignore                        # Liệt kê: .env, __pycache__
├── manage.py                         # File chạy lệnh Django
├── Pipfile                           # Quản lý thư viện Pipenv
└── Pipfile.lock                      # Khóa phiên bản thư viện
```

---

## 5.3. Biến Môi Trường (File `.env`)

```env
# === DJANGO ===
SECRET_KEY=django-insecure-xxxxxxxxxxxxx
DEBUG=True

# === DATABASE ===
DB_NAME=voting_db
DB_USER=postgres
DB_PASSWORD=mat_khau_postgres_cua_ban
DB_HOST=localhost
DB_PORT=5432

# === IPFS (Pinata) ===
# Dùng JWT Token (không dùng api_key cũ nữa)
PINATA_JWT=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# === BLOCKCHAIN (Alchemy) ===
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/ma_api_key_cua_ban
FACTORY_CONTRACT_ADDRESS=0xDia_chi_ElectionFactory_sau_khi_deploy
ADMIN_WALLET_ADDRESS=0xDiaChiMetaMask_CuaAdmin_CuaBan
```

---

## 5.4. Lệnh Cài Đặt Nhanh

```bash
# 1. Cài Pipenv (nếu chưa có)
pip install pipenv

# 2. Cài toàn bộ thư viện cần thiết
pipenv install django psycopg2-binary web3 requests python-dotenv channels channels-redis daphne eth-account

# 3. Kích hoạt môi trường ảo
pipenv shell

# 4. Khởi tạo dự án Django tại thư mục hiện tại (.)
django-admin startproject core .
python manage.py startapp election
mkdir indexer
mkdir templates
mkdir static

# 5. Tạo bảng Database
python manage.py makemigrations
python manage.py migrate

# 6. Tạo tài khoản Admin
python manage.py createsuperuser

# 7. Chạy Server (Phải dùng daphne để WebSockets hoạt động!)
daphne -p 8000 core.asgi:application

# (Tuỳ chọn) Để chạy Indexer song song, mở Terminal 2:
python indexer/indexer.py
```
