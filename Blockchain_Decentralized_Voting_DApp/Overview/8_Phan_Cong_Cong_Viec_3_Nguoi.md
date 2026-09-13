# 8. PHÂN CÔNG CÔNG VIỆC NHÓM (3 THÀNH VIÊN)

Dự án này sử dụng kiến trúc phân tán (Decentralized) kết hợp với Backend tập trung (Centralized). Để đảm bảo tiến độ trong 10 ngày, nhóm cần chia rõ 3 vai trò chuyên biệt. Không ai giẫm chân lên code của ai, và mọi giao tiếp giữa 3 người sẽ thông qua **API** và **Smart Contract ABI**.

---

## 👤 Thành Viên 1: Kỹ Sư Blockchain (Blockchain Data Engineer)

Người nắm giữ "Trái tim" của hệ thống — Đảm bảo tính bất biến, minh bạch và an toàn của phiếu bầu.

### Nhiệm Vụ Cốt Lõi:
1. **Viết Smart Contract:** Code `ElectionFactory.sol` và `Election.sol` trên Remix IDE.
2. **Kiểm định bảo mật:** Bắt lỗi Reentrancy, kiểm tra phân quyền `onlyAdmin`.
3. **Triển khai (Deploy):** Bơm tiền Sepolia ETH và đưa hợp đồng lên mạng lưới Ethereum Testnet. Cung cấp **Contract Address** và **ABI** cho 2 thành viên còn lại.
4. **Viết Indexer:** Code file `indexer.py` (Python) dùng thư viện `web3.py`. Lắng nghe Event 24/7 và bọc `transaction.atomic()` khi đẩy dữ liệu vào Database của Backend.

### KPI (Kết quả cần đạt):
- Hợp đồng không thể bị hack kết quả.
- Indexer chạy ngầm không bị crash khi mất mạng, không bao giờ cộng trùng phiếu.

### Ngày phụ trách chính (Xem Roadmap):
- Ngày 1, Ngày 2, Ngày 7.

---

## 👤 Thành Viên 2: Kỹ Sư Backend (Backend System Architect)

Người xây dựng "Khung xương" — Xử lý nghiệp vụ phức tạp, bảo mật đăng nhập và truyền tải dữ liệu siêu tốc.

### Nhiệm Vụ Cốt Lõi:
1. **Thiết kế Database:** Thiết lập PostgreSQL, tạo bảng (Models) cho Election, Candidate, VoteRecord, Whitelist.
2. **Bảo mật Web3 Auth (SIWE):** Viết logic giải mã chữ ký điện tử bằng `eth-account`, tạo hệ thống đăng nhập Admin không cần mật khẩu.
3. **Quản lý IPFS:** Tích hợp API của Pinata Cloud để upload và lưu trữ ảnh ứng viên phi tập trung.
4. **Hạ tầng WebSockets:** Thay thế WSGI bằng ASGI (`daphne`), cấu hình `consumers.py` (Django Channels) để đẩy tín hiệu nhảy số phiếu xuống Frontend.
5. **Cung cấp API:** Trả dữ liệu JSON (Danh sách bầu cử, kết quả) cho Frontend Engineer.

### KPI (Kết quả cần đạt):
- API phản hồi cực nhanh (dưới 200ms).
- Hệ thống WebSocket hoạt động ổn định, có người vote là biểu đồ nhảy số ngay.
- Đăng nhập bằng MetaMask trơn tru, chặn đứng mọi cố gắng giả mạo chữ ký.

### Ngày phụ trách chính (Xem Roadmap):
- Ngày 3, Ngày 4, Ngày 5, Ngày 8.

---

## 👤 Thành Viên 3: Kỹ Sư Giao Diện & Tích Hợp (Web3 Frontend Developer)

Người vẽ nên "Linh hồn" của ứng dụng — Chịu trách nhiệm toàn bộ về trải nghiệm người dùng (UX/UI).

### Nhiệm Vụ Cốt Lõi:
1. **Xây dựng UI:** Thiết kế các trang HTML/CSS (khuyên dùng TailwindCSS hoặc Bootstrap để có giao diện hiện đại). Bao gồm trang Danh sách, trang Chi tiết, và Admin Dashboard.
2. **Tích hợp Ethers.js:** Gọi ví MetaMask mở popup yêu cầu người dùng Ký (khi đăng nhập Admin) hoặc Xác nhận giao dịch (khi vote).
3. **Trực quan hóa Dữ liệu:** Sử dụng `Chart.js` để vẽ biểu đồ tròn/cột cực kỳ đẹp mắt và dễ hiểu.
4. **Bắt tín hiệu WebSockets:** Mở kết nối WebSocket tới Backend. Khi nhận được tín hiệu "Có phiếu mới", gọi hàm cập nhật Chart.js mà không cần tải lại trang.
5. **Xử lý Ngoại lệ (Edge Cases):** Báo lỗi màu đỏ khi người dùng không đủ tiền Gas, hoặc hủy giao dịch giữa chừng. Báo thành công màu xanh kèm link check Etherscan.

### KPI (Kết quả cần đạt):
- Giao diện đẹp, chuyên nghiệp, hiển thị tốt trên cả điện thoại (Responsive).
- Nút bấm trực quan, hướng dẫn người dùng mới biết cách dùng MetaMask.
- Hiệu ứng nhảy số phiếu mượt mà, gây ấn tượng mạnh lúc Demo.

### Ngày phụ trách chính (Xem Roadmap):
- Ngày 6, Ngày 9.

---

## 🤝 Giao Điểm Hợp Tác (Điểm nóng cần họp bàn)

1. **Ghép nối Frontend và Smart Contract:** Thành viên 1 và 3 phải ngồi cùng nhau để truyền đúng tên hàm, tham số và ABI vào Ethers.js.
2. **Ghép nối Indexer và Backend:** Thành viên 1 và 2 phải thống nhất cấu trúc Database để Indexer (Python) có thể gọi ORM của Django mà không bị lỗi.
3. **Ngày 10 (Chạy thử & Quay video Demo):** Cả 3 thành viên đóng 3 vai (Admin tạo poll, User 1 vote ứng viên A, User 2 vote ứng viên B) để test khả năng đồng bộ Real-time.
