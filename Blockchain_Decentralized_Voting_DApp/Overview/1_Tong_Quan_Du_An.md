# 1. TỔNG QUAN DỰ ÁN: HỆ THỐNG BỎ PHIẾU PHI TẬP TRUNG
### *Decentralized Voting DApp — Hybrid Architecture*

---

## 1.1. Bài Toán & Giải Pháp

### Vấn đề thực tế
Các hệ thống bỏ phiếu truyền thống (giấy tờ, web tập trung) đều tồn tại những rủi ro cố hữu:
- **Gian lận phiếu:** Phiếu bầu có thể bị tráo đổi, thêm bớt hoặc hủy mà không để lại dấu vết.
- **Thiếu minh bạch:** Người bỏ phiếu không thể tự mình kiểm chứng lá phiếu của mình có được ghi nhận đúng không.
- **Điểm tập trung dễ tấn công:** Toàn bộ dữ liệu bầu cử nằm trong một Server, một người có quyền cao nhất có thể tự ý sửa đổi.
- **Bầu hai lần:** Khó kiểm soát trong hệ thống giấy tờ hoặc Web2 không an toàn.

### Giải pháp Blockchain
Hệ thống này mã hóa **mỗi lá phiếu thành một giao dịch (Transaction)** được ghi vĩnh viễn lên mạng lưới Ethereum. Điều đó đảm bảo:
- ✅ **Bất biến (Immutable):** Không ai — kể cả Admin — có thể sửa hay xóa phiếu đã bầu.
- ✅ **Minh bạch (Transparent):** Bất kỳ ai cũng có thể dán TxHash lên Etherscan để tự xác minh phiếu của mình.
- ✅ **Công bằng (Fair):** Smart Contract tự động chặn mỗi ví chỉ được bỏ đúng 1 phiếu trong 1 cuộc bầu cử.
- ✅ **Ẩn danh giả định (Pseudonymous):** Lá phiếu công khai nhưng danh tính thực đằng sau địa chỉ ví được bảo vệ.

---

## 1.2. Kiến Trúc Hệ Thống (5 Tầng Hybrid)

```
┌─────────────────────────────────────────────────────────┐
│  TẦNG 1: FRONTEND (HTML + JS + Ethers.js v6)            │
│  Giao diện người dùng — Hiển thị bầu cử, biểu đồ       │
└──────────────────────┬─────────────────────────────────┘
                       │ REST API (JSON) + WebSocket (Real-time)
┌──────────────────────▼─────────────────────────────────┐
│  TẦNG 2: BACKEND (Django 5 + Channels)                  │
│  API JSON + SIWE Auth + Đẩy WebSocket Real-time        │
└──────────────────────┬─────────────────────────────────┘
       │ ORM                       │ requests lib
┌──────▼────┐        ┌───────▼─────────────────────────┐
│  TẦNG 3a:   │        │  TẦNG 3b: IPFS (Pinata)             │
│  PostgreSQL │        │  Lưu ảnh ứng viên phi tập trung       │
│  (Off-chain)│        └───────────────────────────────┘
└────────────┘
        ▲
        │ Django ORM (ghi số phiếu)
┌───────┴─────────────────────────────────────────────────┐
│  TẦNG 4: INDEXER (Python + Web3.py)                     │
│  Script chạy ngầm 24/7 — Lắng nghe Event VoteCast      │
└───────────────────────┬─────────────────────────────────┘
                        │ Đọc Event logs
┌───────────────────────▼─────────────────────────────────┐
│  TẦNG 5: BLOCKCHAIN (Ethereum Sepolia)                  │
│  Smart Contract Election.sol — Hòm phiếu bất biến      │
│  MetaMask ◄──── Cử tri ký phiếu và gửi giao dịch       │
└─────────────────────────────────────────────────────────┘
```

### B. Đọc Dữ Liệu (Read - Thường xuyên)
- Indexer (Tầng 4) lắng nghe các sự kiện (`VoteCast`) từ Blockchain 24/7.
- Indexer gọi thêm `w3.eth.get_transaction(tx_hash)` để lấy ví người gửi (`tx.from`), sau đó lưu vào PostgreSQL để có lịch sử "Ai vừa vote".
- **Bảo mật dữ liệu:** Indexer sử dụng `transaction.atomic()` của cơ sở dữ liệu để đảm bảo việc "Cộng phiếu" và "Ghi lịch sử" xảy ra nguyên tử đồng thời. Ngăn chặn tuyệt đối việc cộng phiếu 2 lần nếu Indexer sập giữa chừng.
- Người dùng truy cập Frontend, Frontend gọi API từ Backend Django.
- Backend trả về JSON dữ liệu lấy ngay từ PostgreSQL (cực nhanh, không tốn phí Gas).

### C. Quản lý Whitelist (Off-chain & On-chain)
Vì Smart Contract không cho phép duyệt qua danh sách `mapping` (không thể lấy tất cả ví đã whitelist), Admin sẽ quản lý Whitelist như sau:
1. Admin tải lên file CSV hoặc nhập danh sách ví trên Django Dashboard.
2. Backend lưu danh sách này vào Database (`WhitelistVoter`).
3. Dashboard gọi MetaMask của Admin để gửi mảng `address[]` xuống hàm `addToWhitelist()` trên Blockchain.
4. Mọi thứ được đồng bộ: Dashboard có danh sách để hiển thị (từ DB), còn Blockchain có danh sách để xác thực (từ mapping).

---

## 1.3. Luồng Dữ Liệu Chi Tiết

### Luồng 1: Tải Trang (Read Path — Không tốn Gas)
```
Cử tri mở trình duyệt
   → Frontend kết nối WebSocket tới Django Channels
   → Frontend gọi GET /api/elections/
   → Django trả danh sách bầu cử (kèm địa chỉ hợp đồng đã tạo từ Factory)
   → Frontend render biểu đồ ban đầu
```

### Luồng 2: Admin Đăng nhập (Web3 Auth - Không mật khẩu)
```
Admin bấm "Đăng nhập"
   → Frontend gọi GET /api/auth/nonce/ lấy mã ngẫu nhiên
   → Admin dùng MetaMask ký (Sign) mã đó
   → Gửi chữ ký (Signature) lên POST /api/auth/verify/
   → Django dùng eth_account kiểm tra, nếu đúng -> Cấp Session/JWT
```

### Luồng 3: Bỏ Phiếu (Write Path — Tốn phí Gas nhỏ)
```
Cử tri bấm chọn Ứng viên A trên Web
   → Ethers.js kết nối MetaMask yêu cầu xác nhận
   → Cử tri ký giao dịch, đẩy lên mạng Sepolia
   → Smart Contract `Election.sol` (tạo bởi Factory) lưu dữ liệu & phát ra Event `VoteCast`
```

### Luồng 4: Đồng Bộ & Real-time Cập Nhật (Đỉnh cao UX)
```
Smart Contract phát ra Event `VoteCast`
   → Script Indexer đang chạy ngầm lập tức chộp được Event
   → Indexer lấy `tx.from`, bọc vào `transaction.atomic()` lưu PostgreSQL & cộng phiếu
   → Ngay lập tức, Indexer/Django đẩy WebSocket tới TẤT CẢ trình duyệt
   → Chart.js nhảy phần trăm ngay lập tức (KHÔNG cần F5 tải lại trang!)
```

---

## 1.4. Trang Chi Tiết Cuộc Bầu Cử (`/elections/<id>/`)

Khi nhấn vào một vấn đề cần bỏ phiếu, cử tri sẽ thấy một trang chi tiết đầy đủ gồm:

| Khối | Nội dung |
|:---|:---|
| **Thông tin cơ bản** | Tên vấn đề, mô tả, trạng thái, thời gian, chế độ Public/Private |
| **Bảng ứng viên** | Tên, ảnh (từ IPFS), số phiếu, tỉ lệ %, thanh tiến trình |
| **Biểu đồ cột** | So sánh trực quan số phiếu giữa các ứng viên (Chart.js) |
| **Biểu đồ tròn** | Phân bổ tỉ lệ % phiếu bầu (Chart.js) |
| **Thống kê tổng** | Tổng phiếu đã bầu, tỉ lệ tham gia, ứng viên đang dẫn đầu |
| **Nút hành động** | Bầu chọn (nếu chưa vote) / TxHash xác nhận (nếu đã vote) |
| **Lịch sử phiếu** | Bảng Real-time các giao dịch gần nhất (ví ẩn danh + thời gian) |

> [!NOTE]
> **2 chế độ bầu cử:**
> - 🔓 **Public Poll:** Bất kỳ ví MetaMask nào cũng có thể vote tự do.
> - 🔒 **Private Poll:** Smart Contract chỉ chấp nhận các ví nằm trong Whitelist do Admin cấu hình trước.

---

## 1.5. Các Tài Liệu Liên Quan

| File | Nội dung |
|:---|:---|
| [2_Smart_Contract.md](./2_Smart_Contract.md) | Thiết kế `ElectionFactory.sol` và `Election.sol` |
| [3_Backend_API.md](./3_Backend_API.md) | Django API Thuần: Models, Endpoints đầy đủ, Web3 Auth |
| [4_Frontend_Web3.md](./4_Frontend_Web3.md) | Ethers.js, MetaMask flow, Chart.js, WebSockets |
| [5_Cong_Cu_Va_Thu_Vien.md](./5_Cong_Cu_Va_Thu_Vien.md) | Tech Stack, cấu trúc thư mục, biến môi trường |
| [6_Roadmap_10_Ngay.md](./6_Roadmap_10_Ngay.md) | Lộ trình thực hành 10 ngày (3 người) |
| [7_Huong_Phat_Trien.md](./7_Huong_Phat_Trien.md) | Hướng nâng cấp tương lai (L2, ZKP, DAO) |
| [8_Phan_Cong_Cong_Viec_3_Nguoi.md](./8_Phan_Cong_Cong_Viec_3_Nguoi.md) | Phân công vai trò cho 3 thành viên |
