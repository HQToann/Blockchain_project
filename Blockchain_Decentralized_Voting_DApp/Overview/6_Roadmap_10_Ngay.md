# 6. ROADMAP: KẾ HOẠCH TRIỂN KHAI 10 NGÀY (Nhóm 3 Người)

Với 3 tính năng nâng cấp (Factory, SIWE, WebSockets), lộ trình triển khai được chia thành 10 ngày để cân đối khối lượng công việc cho cả 3 thành viên.

---

## 🟢 NGÀY 1-2: BLOCKCHAIN & FACTORY (Blockchain Engineer)
*Mục tiêu: Viết và Deploy bộ Hợp đồng thông minh lên Sepolia.*

- [ ] Cài đặt MetaMask, nhận Sepolia ETH.
- [ ] Khởi tạo môi trường Hardhat, viết `ElectionFactory.sol` và `Election.sol` trong VS Code.
- [ ] Biên dịch (Compile) bằng Hardhat CLI (`npx hardhat compile`).
- [ ] Deploy ElectionFactory lên mạng lưới Sepolia.
- [ ] Lưu lại Contract Address và ABI (của cả 2 contract).

## 🟢 NGÀY 3-4: BACKEND & WEB3 AUTH (Backend Engineer)
*Mục tiêu: Setup Django và tính năng Đăng nhập không mật khẩu.*

- [ ] Tạo dự án Django, setup PostgreSQL.
- [ ] Cài đặt thư viện: pipenv install django daphne eth-account ...
- [ ] Khởi tạo Models (Election, Candidate, VoteRecord, WhitelistVoter).
- [ ] Xây dựng 2 API cho Web3 Auth: /api/auth/nonce/ và /api/auth/verify/.
- [ ] Test bằng Postman hoặc Frontend giả lập.

## 🟢 NGÀY 5-6: NGHIỆP VỤ & IPFS (Backend Engineer)
*Mục tiêu: Các API phục vụ hiển thị.*

- [ ] Tạo tài khoản Pinata Cloud lấy API Key.
- [ ] Viết API upload ảnh ứng viên lên IPFS.
- [ ] Viết các API: Lấy danh sách bầu cử, kết quả, chi tiết.
- [ ] Xây dựng giao diện Admin Dashboard cơ bản (bằng Django Templates hoặc HTML tĩnh gọi API).

## 🟢 NGÀY 7: INDEXER (Blockchain Engineer + Backend Engineer)
*Mục tiêu: Đồng bộ dữ liệu Blockchain về Database.*

- [ ] Tạo script indexer.py độc lập.
- [ ] Lắng nghe 2 sự kiện: ElectionCreated (từ Factory) và VoteCast (từ Election).
- [ ] Bọc code lưu Database vào `transaction.atomic()`.
- [ ] Test: Bầu qua Admin Dashboard hoặc Etherscan -> Indexer nhận diện -> Database tăng phiếu.

## 🟢 NGÀY 8: WEBSOCKETS (Backend Engineer + Frontend Engineer)
*Mục tiêu: Cấu hình ASGI để đẩy dữ liệu Real-time.*

- [ ] Thay WSGI bằng ASGI (daphne).
- [ ] Viết consumers.py trong Django để gửi tín hiệu tới client.
- [ ] Cập nhật Indexer: Khi có phiếu mới, Indexer gọi lệnh đẩy WebSocket.

## 🟢 NGÀY 9: FRONTEND TÍCH HỢP (Frontend Engineer)
*Mục tiêu: Kết nối Ethers.js, WebSockets và Chart.js.*

- [ ] Viết HTML/CSS (khuyến nghị dùng Bootstrap/Tailwind).
- [ ] Dùng Ethers.js kết nối MetaMask để gọi hàm vote().
- [ ] Tích hợp WebSocket (`new WebSocket(...)`) để lắng nghe tín hiệu.
- [ ] Khi có tín hiệu, gọi Chart.js update lại biểu đồ mượt mà.

## 🟢 NGÀY 10: TỔNG KIỂM TRA & DEMO (Cả nhóm)
*Mục tiêu: Đảm bảo không có lỗi (Edge cases).*

- [ ] Chạy luồng Full: Đăng nhập SIWE -> Tạo bầu cử (Factory) -> Ứng viên (IPFS) -> Vote (MetaMask) -> Chart nhảy số (WebSockets).
- [ ] Test lỗi: Người dùng từ chối giao dịch, lỗi rớt mạng.
- [ ] Chuẩn bị kịch bản báo cáo và Slide.
