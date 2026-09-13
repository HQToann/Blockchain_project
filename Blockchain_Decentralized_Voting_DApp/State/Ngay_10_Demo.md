# 🟢 NGÀY 10: TỔNG KIỂM TRA VÀ CHUẨN BỊ BÁO CÁO (DEMO)

Đây là ngày để cả 3 thành viên ngồi lại với nhau, kiểm tra toàn bộ luồng chạy của ứng dụng, bắt bug và phân vai trình diễn trước mặt Giảng viên.

---

## BƯỚC 1: Khởi động 100% Hệ thống

Để dự án chạy trơn tru, bạn cần mở **Ít nhất 2 cửa sổ Terminal (Command Prompt)**:

1. **Terminal 1 (Chạy Web Server bằng Daphne để có WebSocket):**
   ```bash
   pipenv shell
   daphne -p 8000 core.asgi:application
   ```
   *(Trang web của bạn sẽ chạy ở `http://127.0.0.1:8000/`)*

2. **Terminal 2 (Chạy Cỗ máy Bắt Sự kiện):**
   ```bash
   pipenv shell
   python indexer/indexer.py
   ```
   *(Đợi nó hiện chữ "🚀 Khởi động Indexer..." và nằm im canh me)*

---

## BƯỚC 1.5: Lưu Ý Sinh Tử Trược Giờ G

> [!WARNING]
> **Đồng bộ Candidate_ID:** 
> Backend và Smart Contract là 2 hệ thống độc lập. Admin phải đảm bảo thứ tự tạo ứng viên khớp nhau!
> 1. Gọi API tạo Candidate trong Django DB trước (nhập ID = 0, 1, 2...).
> 2. Lên Smart Contract gọi `addCandidate()` theo đúng thứ tự đó.
> 
> **Nếu ID bị lệch (VD: DB là 0, Contract là 1)**, phiếu bầu sẽ cộng nhầm người hoặc bị bỏ qua vĩnh viễn (do Indexer không tìm thấy ứng viên trong DB). Hãy kiểm tra kỹ trên [Sepolia Etherscan](https://sepolia.etherscan.io) bằng cách tìm kiếm Contract Address của Election và gọi thử hàm `candidates(0)` trong tab Read Contract để đảm bảo khớp thông tin với DB trước khi lên sân khấu!

---

## BƯỚC 2: Kịch Bản Demo Điểm A+

Hãy chia vai lúc báo cáo. Giảng viên rất thích xem Demo trực quan.

**Vai diễn 1 (Kỹ sư Backend đóng vai Admin):**
1. Mở trang chủ (`http://127.0.0.1:8000/`), bấm nút **"🔑 Vào Trang Quản Trị (Admin)"**.
2. Trang Dashboard mở ra, bấm nút **"Đăng Nhập Web3 (Admin)"**.
3. MetaMask nhảy lên yêu cầu ký (Khoe tính năng SIWE không mật khẩu). Đăng nhập thành công!
4. Vào trang Admin Dashboard, bấm **"Tạo cuộc bầu cử mới"**.
5. Giải thích: *"Khi em bấm nút này, Backend sẽ gọi Smart Contract `ElectionFactory` để tự động đẻ ra 1 Smart Contract con độc lập"*.
6. Ký giao dịch trên MetaMask để tạo poll.
7. Thêm ảnh ứng viên (Khoe tính năng tải lên **IPFS Pinata**).

**Vai diễn 2 (Kỹ sư Frontend đóng vai Cử tri 1):**
1. Dùng điện thoại hoặc máy tính thứ 2 (có cài MetaMask ví phụ).
2. Vào trang Chi tiết Bầu cử (`http://<IP_MAY_CHU>:8000/election/1/`).
3. Bấm **Bầu chọn** ứng viên A.
4. Ký giao dịch trên MetaMask.

**Vai diễn 3 (Kỹ sư Blockchain chỉ màn hình máy chiếu):**
1. Giải thích trong lúc giao dịch đang load: *"Lúc này giao dịch đang được mạng Sepolia xác nhận..."*
2. Khi Terminal 2 (Indexer) chớp dòng chữ *"🔥 Cập nhật phiếu thành công"*...
3. ...**BÙM!** Ngay lập tức trên máy tính của mọi người trong phòng, biểu đồ Chart.js tự động nảy số phần trăm ứng viên A lên mà không ai chạm vào chuột (Khoe sức mạnh của **WebSockets**).

**Chốt hạ (Kỹ sư Blockchain):**
- Mở trang web [sepolia.etherscan.io](https://sepolia.etherscan.io).
- Dán mã `TxHash` vào ô tìm kiếm.
- Khoe: *"Đây thưa thầy/cô, lá phiếu vừa rồi đã được ghi vĩnh viễn lên Blockchain, có đầy đủ Input Data, không ai có thể sửa đổi hay xóa bỏ nó được nữa!"*

---

## BƯỚC 3: Dự Phòng Sự Cố (Luôn Có Plan B)

- **Nếu nghẽn mạng Ethereum:** Chuyển ví MetaMask sang mức phí Gas cao hơn (Aggressive) để giao dịch chạy nhanh.
- **Nếu Alchemy hết hạn mức API:** Tạo trước 2-3 API Key dự phòng và đổi chuỗi `ALCHEMY_RPC_URL` trong file `.env`.
- **Lỗi kinh điển:** Cử tri bấm Vote xong nhưng không đủ tiền Gas. Hãy dặn mọi người lấy sẵn thật nhiều Sepolia ETH từ Faucet đêm trước ngày báo cáo!

---
🎉 **CHÚC MỪNG BẠN!** 🎉
Dự án **Decentralized Voting DApp** chính thức hoàn thiện. Với kiến trúc **Smart Contract Factory, SIWE Web3 Auth, IPFS, và Real-time WebSockets**, dự án này hoàn toàn dư sức đánh bại các nhóm khác và đem về cho bạn điểm Xuất Sắc!
