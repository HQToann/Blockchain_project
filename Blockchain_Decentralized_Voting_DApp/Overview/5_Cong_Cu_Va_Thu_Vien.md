# 5. CÔNG CỤ & THƯ VIỆN SỬ DỤNG (TECH STACK)

> **Cập nhật:** 09/2026 — Phiên bản Production hiện tại

---

## 5.1. Bảng Tech Stack Đầy Đủ

### 🔗 Tầng Blockchain (On-chain)
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Solidity** | ^0.8.20 | Ngôn ngữ viết Smart Contract |
| **Hardhat** | ^2.22.x | Compile, test, deploy Contract |
| **Sepolia Testnet** | — | Mạng Ethereum thử nghiệm (Gas là tiền giả) |
| **MetaMask** | Latest | Ví điện tử để ký giao dịch |
| **Alchemy** | — | RPC Node kết nối vào mạng Sepolia |

### 🖥️ Tầng Backend (Off-chain)
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **Python** | >= 3.11 | Ngôn ngữ chính cho Backend và Indexer |
| **Django** | 5.x | Web Framework — API JSON + Django Admin |
| **Daphne** | 4.x | ASGI Server hỗ trợ WebSockets |
| **Django Channels** | 4.x | Xử lý WebSocket real-time |
| **channels-redis** | 4.x | Channel Layer kết nối qua Redis |
| **django-rq** | Latest | Background Task Queue (dùng Redis) |
| **Web3.py** | 8.x | Kết nối Blockchain cho Indexer |
| **eth-account** | Latest | Xác thực chữ ký MetaMask (Web3 Auth) |
| **psycopg2-binary** | Latest | Driver kết nối PostgreSQL |
| **dj-database-url** | Latest | Parse DATABASE_URL từ biến môi trường |
| **WhiteNoise** | 6.x | Phục vụ static files (CSS/JS) trên Production |
| **django-jazzmin** | 3.x | Giao diện Django Admin Dark Mode đẹp |
| **Gunicorn** | Latest | WSGI fallback (Daphne là ASGI chính) |
| **python-dotenv** | Latest | Load biến môi trường từ `.env` |

### 🎨 Tầng Frontend
| Công cụ | Phiên bản | Vai trò |
|:---|:---|:---|
| **HTML5 + CSS3** | — | Cấu trúc và giao diện |
| **Vanilla JavaScript** | ES2022+ | Logic giao diện, gọi API |
| **Ethers.js** | v6.7.0 (CDN + SRI) | Kết nối MetaMask, gọi Smart Contract |
| **Chart.js** | v4.4.3 (CDN) | Biểu đồ kết quả real-time |
| **Toastify.js** | v1.12.0 (CDN) | Thông báo toast không dùng `alert()` |

### ☁️ Dịch Vụ Cloud
| Dịch vụ | Vai trò |
|:---|:---|
| **Render** | Deploy Web Server + Background Worker (Indexer) |
| **Supabase** | PostgreSQL đám mây |
| **Redis** | Message Broker cho WebSocket và Task Queue |
| **Pinata (IPFS)** | Lưu ảnh ứng viên phi tập trung |
| **Etherscan Sepolia** | Tra cứu giao dịch công khai |

---

## 5.2. Cấu Trúc Thư Mục Thực Tế

```text
Blockchain_Project/                   # Thư mục gốc
│
├── 📁 Blockchain_Decentralized_Voting_DApp/  # Tài liệu dự án
│   ├── Overview/                     # Tài liệu kiến trúc & thiết kế
│   └── State/                        # Nhật ký tiến độ theo từng ngày
│
├── 📁 core/                          # Cấu hình Django Project
│   ├── settings.py                   # DB, Cache, CORS, Channels, Jazzmin
│   ├── urls.py                       # Router chính
│   ├── asgi.py                       # ASGI (bắt buộc cho WebSockets)
│   └── wsgi.py
│
├── 📁 election/                      # App nghiệp vụ bầu cử (Django)
│   ├── models.py                     # Election, Candidate, VoteRecord,
│   │                                 # WhitelistVoter, SystemLog,
│   │                                 # IndexerState, AdminWallet
│   ├── views.py                      # API JSON + Web3 Auth + Rate Limiting
│   ├── admin.py                      # Django Admin UI + Actions
│   ├── tasks.py                      # Background Tasks (RQ): deploy, vote, whitelist
│   ├── consumers.py                  # WebSocket Consumer (Django Channels)
│   ├── routing.py                    # WebSocket URL routing
│   ├── services.py                   # Upload ảnh lên IPFS Pinata
│   ├── utils.py                      # Helper (factory address, ...)
│   ├── tests.py                      # Unit Tests (3 test cases)
│   └── migrations/                   # Migration files
│
├── 📁 indexer/                       # Blockchain Indexer (script độc lập)
│   └── indexer.py                    # Lắng nghe Event on-chain 24/7
│
├── 📁 templates/                     # Giao diện HTML
│   ├── index.html                    # Trang chủ — danh sách bầu cử
│   ├── detail.html                   # Trang chi tiết + bỏ phiếu + whitelist
│   ├── verify.html                   # Trang xác minh phiếu bằng TxHash
│   └── logs.html                     # Trang System Logs (Admin only)
│
├── 📁 static/                        # File tĩnh
│   ├── css/style.css                 # Toàn bộ CSS (Dark mode, badges, animations)
│   ├── js/app.js                     # Logic Frontend (Ethers.js, WebSocket, CSRF)
│   └── img/                          # Favicon, placeholder icons
│
├── 📁 contracts/                     # Solidity Smart Contracts
│   └── VotingSystem.sol              # ElectionFactory + Election
│
├── 📁 ignition/modules/              # Hardhat deploy scripts
├── 📁 test/                          # Hardhat unit tests (JS)
├── 📁 artifacts/                     # Build output của Hardhat (gitignore)
├── 📁 cache/                         # Cache Hardhat (gitignore)
├── 📁 node_modules/                  # Node dependencies (gitignore)
│
├── Election_ABI.json                 # ABI hợp đồng Election (dùng cho tasks.py + indexer)
├── Factory_ABI.json                  # ABI ElectionFactory (dùng cho tasks.py + indexer)
├── hardhat.config.js                 # Cấu hình Hardhat
├── package.json                      # Node dependencies
│
├── manage.py                         # CLI Django
├── Pipfile / Pipfile.lock            # Quản lý dependencies local
├── requirements.txt                  # Dependencies cho Deploy (Render)
│
├── render.yaml                       # Infrastructure as Code cho Render
├── build.sh                          # Script tự động chạy khi deploy Render
├── start.sh                          # Script khởi động Production (Daphne + Indexer)
├── start_local.bat                   # Script khởi động Local Windows (3 cửa sổ)
│
├── .env                              # Biến môi trường (KHÔNG đẩy lên Git)
├── .env.example                      # Mẫu biến môi trường
└── .gitignore
```

---

## 5.3. Biến Môi Trường (File `.env`)

```env
# === WEB3 BLOCKCHAIN ===
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
PRIVATE_KEY=0x_private_key_cua_vi_admin_chi_gas        # TUYỆT ĐỐI KHÔNG LỘ!

# === ADMIN WALLETS (nhiều admin, phân cách bằng dấu phẩy) ===
ADMIN_WALLET_ADDRESSES=0xAdminWallet1,0xAdminWallet2

# === PINATA IPFS ===
PINATA_JWT=eyJhbGci...

# === DATABASE ===
USE_SQLITE=False                                        # True để test local không cần Supabase
DATABASE_URL=postgresql://user:pass@host:5432/dbname    # Supabase connection string

# === DJANGO ===
DJANGO_SECRET_KEY=chuoi_bi_mat_bat_ky_dai_hon_50_ky_tu
INTERNAL_API_SECRET=secret_rieng_indexer_thong_bao_django   # Khác với SECRET_KEY!
SESSION_COOKIE_AGE=86400                                # Session sống 24 giờ
```

---

## 5.4. Lệnh Khởi Động

### Chạy Local (Windows)
```bat
:: Chạy file batch — tự động mở 3 cửa sổ Terminal
start_local.bat
```
Hoặc thủ công trên 3 Terminal riêng:
```bash
# Terminal 1: Django Web Server
pipenv run daphne -b 127.0.0.1 -p 8000 core.asgi:application

# Terminal 2: RQ Worker (xử lý background tasks)
pipenv run python manage.py rqworker default

# Terminal 3: Blockchain Indexer
pipenv run python indexer/indexer.py
```

### Deploy Production (Render)
```bash
# Push code lên GitHub → Render tự động chạy build.sh
git push origin main
```
Render sẽ khởi động 3 service theo `render.yaml`:
1. **Web** — Daphne ASGI Server
2. **Worker** — RQ Worker (background tasks)
3. **Indexer** — Blockchain sync script

### Migrate Database
```bash
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic --noinput  # Production
```
