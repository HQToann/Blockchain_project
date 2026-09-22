# HỆ THỐNG BỎ PHIẾU PHI TẬP TRUNG TRÊN BLOCKCHAIN
### *Decentralized Voting DApp — Hybrid Architecture*

> **Phiên bản tài liệu:** 2.0 — Cập nhật theo trạng thái thực tế của dự án (09/2026)

---

## 1.1. Bài Toán & Giải Pháp

### Vấn đề thực tế
Các hệ thống bỏ phiếu truyền thống (giấy tờ, web tập trung) tồn tại những rủi ro:
- **Gian lận phiếu:** Phiếu bầu có thể bị tráo đổi, thêm bớt mà không để lại dấu vết.
- **Thiếu minh bạch:** Người bỏ phiếu không thể tự kiểm chứng phiếu của mình đã được ghi nhận đúng không.
- **Điểm tập trung dễ tấn công:** Toàn bộ dữ liệu nằm trong một Server, Admin có thể tự ý sửa đổi.
- **Bầu hai lần:** Khó kiểm soát trong hệ thống giấy tờ hoặc Web truyền thống.

### Giải pháp Blockchain
Hệ thống mã hóa **mỗi lá phiếu thành một giao dịch (Transaction)** được ghi vĩnh viễn lên mạng Ethereum:
- ✅ **Bất biến:** Không ai — kể cả Admin — có thể sửa hay xóa phiếu đã bầu.
- ✅ **Minh bạch:** Ai cũng có thể dán `TxHash` lên Etherscan để tự xác minh phiếu của mình.
- ✅ **Công bằng:** Smart Contract tự động chặn mỗi ví chỉ bỏ đúng 1 phiếu trong 1 cuộc bầu cử.
- ✅ **Giả danh (Pseudonymous):** Lá phiếu công khai trên chain, nhưng danh tính thực đằng sau ví được bảo vệ.

---

## 1.2. Kiến Trúc Hệ Thống (5 Tầng)

```
┌──────────────────────────────────────────────────────────────┐
│  TẦNG 1: FRONTEND (HTML + Vanilla JS + Ethers.js v6.7)       │
│  3 trang: Trang chủ · Chi tiết bầu cử · Xác minh phiếu      │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST API (JSON) + WebSocket
┌───────────────────────────▼──────────────────────────────────┐
│  TẦNG 2: BACKEND (Django 5 + Daphne ASGI)                    │
│  API JSON · Web3 Auth (SIWE) · Quản lý Admin · WebSocket     │
│  Background Task: django-rq (Redis Queue)                    │
└───────────┬───────────────────────────┬──────────────────────┘
            │ ORM                       │ HTTP Webhook nội bộ
┌───────────▼──────────┐    ┌───────────▼──────────────────────┐
│  TẦNG 3a: Database   │    │  TẦNG 3b: IPFS (Pinata)          │
│  PostgreSQL (Supabase│    │  Lưu ảnh ứng viên phi tập trung  │
│  hoặc SQLite local)  │    └──────────────────────────────────┘
└───────────┬──────────┘
            │ notify_vote webhook
┌───────────▼──────────────────────────────────────────────────┐
│  TẦNG 4: BLOCKCHAIN INDEXER (Python + Web3.py)               │
│  Script chạy ngầm, lắng nghe sự kiện on-chain 24/7          │
│  Đồng bộ kết quả bầu cử vào Database                        │
└───────────────────────────┬──────────────────────────────────┘
                            │ Đọc Event logs
┌───────────────────────────▼──────────────────────────────────┐
│  TẦNG 5: BLOCKCHAIN (Ethereum Sepolia Testnet)                │
│  ElectionFactory.sol · Election.sol · MetaMask               │
└──────────────────────────────────────────────────────────────┘
```

---

## 1.3. Luồng Dữ Liệu

### Luồng 1 — Tải Trang (không tốn Gas)
```
Cử tri mở trình duyệt
  → Frontend kết nối WebSocket tới Django Channels
  → Frontend gọi GET /api/elections/
  → Django trả danh sách bầu cử từ Database (cực nhanh)
  → Frontend render biểu đồ Chart.js
```

### Luồng 2 — Admin Đăng Nhập (Web3 Auth, không mật khẩu)
```
Admin bấm "Đăng nhập"
  → GET /api/auth/nonce/ → lấy chuỗi ngẫu nhiên (nonce)
  → Admin ký nonce bằng MetaMask
  → POST /api/auth/verify/ → Django kiểm tra chữ ký bằng eth_account
  → Nếu ví khớp danh sách AdminWallet trong DB → Cấp Django Session
  → Redirect vào /admin/
```

### Luồng 3 — Bỏ Phiếu (tốn phí Gas nhỏ)
```
Cử tri chọn ứng viên
  → Ethers.js yêu cầu MetaMask xác nhận giao dịch
  → Cử tri ký, đẩy TX lên mạng Sepolia
  → Smart Contract Election.sol lưu dữ liệu & phát Event VoteCast
```

### Luồng 4 — Đồng Bộ Real-time
```
Smart Contract phát Event VoteCast
  → Indexer (chạy ngầm) bắt được Event
  → Indexer gọi POST /api/internal/notify_vote/ kèm X-Internal-Secret
  → Django cộng phiếu vào DB + phát WebSocket tới TẤT CẢ trình duyệt
  → Chart.js cập nhật % ngay lập tức (không cần F5)
```

### Luồng 5 — Xác Minh Phiếu (Minh bạch)
```
Cử tri vào trang /verify/
  → Nhập TxHash của giao dịch bỏ phiếu
  → Hệ thống tra cứu trên Blockchain qua Alchemy RPC
  → Hiển thị: Cuộc bầu cử · Ví bỏ phiếu · Block · Thời gian (UTC+7)
```

---

## 1.4. Tính Năng Đầy Đủ

### Dành cho Cử Tri
| Tính năng | Mô tả |
|:---|:---|
| Xem danh sách bầu cử | Trang chủ với badge trạng thái và thống kê nhanh |
| Xem chi tiết | Ứng viên, biểu đồ cột, số phiếu real-time |
| Kết nối MetaMask | Kiểm tra đúng mạng Sepolia (Chain ID 11155111) |
| Bỏ phiếu | Ký giao dịch qua MetaMask, nhận TxHash xác nhận |
| Xem danh sách cử tri | Bảng ví đã tham gia (bảo mật, không lộ lựa chọn) |
| Xác minh phiếu | Trang `/verify/` — tra cứu TxHash bất kỳ lúc nào |
| Real-time | Biểu đồ tự cập nhật qua WebSocket không cần F5 |

### Dành cho Admin
| Tính năng | Mô tả |
|:---|:---|
| Đăng nhập Web3 | Ký bằng MetaMask, không cần mật khẩu |
| Tạo cuộc bầu cử | Deploy smart contract qua Django Admin UI |
| Thêm ứng viên | Upload ảnh lên IPFS (Pinata), lưu CID vào DB |
| Mở/Đóng bầu cử | Gửi lệnh on-chain `startElection()` / `stopElection()` |
| Quản lý Whitelist | Thêm/retry ví cử tri cho hòm phiếu kín |
| Quản lý Admin | Thêm/xóa/tắt ví Admin trực tiếp từ UI (không cần sửa `.env`) |
| Theo dõi TX | Badge trạng thái: pending → broadcasted → confirmed/failed |
| System Logs | Trang `/logs/` xem log hoạt động hệ thống theo thời gian thực |

### Hai Chế Độ Bầu Cử
- 🔓 **Public Poll:** Bất kỳ ví MetaMask nào cũng có thể vote tự do.
- 🔒 **Private Poll:** Chỉ ví nằm trong Whitelist (do Admin thêm on-chain) mới được bỏ phiếu.

---

## 1.5. Tài Liệu Liên Quan

| File | Nội dung |
|:---|:---|
| [2_Smart_Contract.md](./2_Smart_Contract.md) | Thiết kế `ElectionFactory.sol` và `Election.sol` |
| [3_Backend_API.md](./3_Backend_API.md) | Django Models, API Endpoints, Web3 Auth, Tasks |
| [4_Frontend_Web3.md](./4_Frontend_Web3.md) | Ethers.js, MetaMask flow, Chart.js, WebSockets |
| [5_Cong_Cu_Va_Thu_Vien.md](./5_Cong_Cu_Va_Thu_Vien.md) | Tech Stack, cấu trúc thư mục, biến môi trường |
| [6_Huong_Dan_Chay_Local.md](./6_Huong_Dan_Chay_Local.md) | Cài đặt và chạy dự án trên máy cục bộ |
| [7_Huong_Phat_Trien.md](./7_Huong_Phat_Trien.md) | Hướng nâng cấp tương lai (L2, ZKP, DAO) |
