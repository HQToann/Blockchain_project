# 7. HƯỚNG PHÁT TRIỂN & CÁC ĐIỂM NÂNG CẤP

Tài liệu này chuẩn bị cho bạn "vũ khí phản biện" khi hội đồng hỏi về điểm yếu và hướng phát triển của dự án.

---

## 7.1. Lỗ Hổng Hiện Tại & Cách Khắc Phục

### Vấn đề 1: Tấn công Sybil (Sybil Attack)
*   **Bản chất:** Tạo ví MetaMask hoàn toàn miễn phí. Một người có thể tạo 1,000 ví, rồi bầu cùng một phương án 1,000 lần. Smart Contract chặn được "1 ví = 1 phiếu" nhưng không biết 1,000 ví kia đều thuộc về 1 người thực sự.
*   **Giải pháp hiện tại:** Dùng chế độ **Private Poll + Whitelist**. Admin chỉ cấp quyền vote cho các ví đã được xác minh danh tính trước, loại bỏ hoàn toàn khả năng tấn công Sybil.
*   **Giải pháp nâng cao (Tương lai):** Tích hợp **eKYC** — Người dùng chụp CCCD trên trang Django (Web2). Sau khi hệ thống xác nhận danh tính thật, tự động thêm địa chỉ ví đó vào Whitelist trên Smart Contract. Mỗi người thật chỉ có thể đăng ký 1 ví.

### Vấn đề 2: Tập Trung Quyền Hạn của Admin (Centralization Risk)
*   **Bản chất:** Hiện tại, 1 Admin có toàn quyền: Tạo cuộc bầu cử, thêm ứng viên, mở/đóng hòm phiếu, quản lý Whitelist. Nếu Admin hành động không trung thực (ví dụ: đột ngột đóng hòm phiếu sớm khi ứng viên mình ủng hộ đang dẫn đầu), hệ thống không có cơ chế ngăn chặn.
*   **Giải pháp (Trình bày ở slide):** Áp dụng **Multi-sig Governance** — Yêu cầu ít nhất 3/5 người quản trị cùng ký xác nhận mới được thực hiện các thao tác nhạy cảm như đóng hòm phiếu hay thay đổi whitelist.

### Vấn đề 3: Ẩn Danh Tuyệt Đối (Absolute Privacy)
*   **Bản chất:** Hệ thống hiện tại sử dụng "Ẩn danh giả định" (Pseudonymity) — Người dùng không bị lộ tên thật, nhưng địa chỉ ví của họ được ghi công khai lên Blockchain kèm theo lựa chọn bầu cử. Nếu ai đó biết bạn sở hữu ví `0x123`, họ biết bạn đã bầu cho ai.
*   **Giải pháp (Công nghệ tiên tiến nhất):** **Zero-Knowledge Proofs (ZKP)** — Cho phép cử tri gửi lên Blockchain một "bằng chứng toán học" chứng minh họ có quyền vote và đã vote hợp lệ, nhưng **không tiết lộ địa chỉ ví** cũng như **không tiết lộ họ bầu cho ai**. Kết quả cuộc bầu cử vẫn được tính toán chính xác.

---

## 7.2. Hướng Nâng Cấp Kỹ Thuật (Cho Đồ Án Tốt Nghiệp Xuất Sắc)

- **Tích hợp L2 (Arbitrum / Base):** Mạng Sepolia chỉ là Testnet. Khi đưa lên Mainnet, phí Gas của Ethereum rất đắt. Triển khai Smart Contract (Factory) lên các Layer 2 (như Base của Coinbase hoặc Arbitrum) sẽ giúp phí Gas bầu chọn gần như bằng 0, phù hợp với người dùng cuối.
- **Tích hợp ZKP (Zero-Knowledge Proofs):** Hoàn thiện hoàn toàn vấn đề Privacy bằng cách sử dụng Zk-SNARKs. Cử tri chứng minh mình có quyền vote mà không cần tiết lộ ví của mình là gì (Anonymous Voting chuẩn mực).
- **Cơ chế quản trị DAO cho Factory:** Thay vì Admin tập trung (`admin` của Factory), việc tạo hòm phiếu mới sẽ được kiểm soát bởi một DAO (Tổ chức Tự trị Phi tập trung). Các thành viên nắm giữ Governance Token sẽ vote để quyết định xem có cho phép tạo hòm phiếu mới hay không. 

| Nâng cấp | Công nghệ | Lợi ích |
|:---|:---|:---|
| **Gasless Voting (Bỏ phiếu miễn phí Gas)** | Meta-Transactions, EIP-712 | Cử tri không cần trả tiền Gas, Admin chi trả hộ. Thân thiện người dùng hơn. |
| **Kết quả Real-time cực nhanh** | WebSocket (Django Channels) | Thay vì polling 10s, biểu đồ cập nhật ngay lập tức khi có phiếu mới. |
| **Triển khai lên Layer 2** | Polygon, Arbitrum | Phí Gas rẻ hơn 100x, tốc độ nhanh hơn nhiều so với Ethereum Mainnet. |
| **Ẩn danh tuyệt đối** | ZK-SNARKs (Circom + SnarkJS) | Bảo vệ hoàn toàn danh tính người bỏ phiếu. |
| **Quản trị phi tập trung** | Multi-sig (Gnosis Safe) hoặc DAO | Loại bỏ điểm tập trung quyền lực của Admin. |

---

## 7.3. Câu Hỏi Hội Đồng Thường Gặp & Cách Trả Lời

**Q: "Tại sao phải dùng Blockchain cho bỏ phiếu? Database thường không làm được à?"**
> *"Thưa thầy/cô, Database truyền thống có điểm yếu chết người: Người quản trị hệ thống có thể tự ý sửa đổi hay xóa bản ghi phiếu bầu mà không để lại dấu vết. Blockchain giải quyết điều này bằng tính bất biến — mỗi phiếu bầu một khi đã được ghi nhận không thể bị thay đổi bởi bất kỳ ai."*

**Q: "Tại sao phải dùng ví MetaMask phức tạp vậy?"**
> *"Ví MetaMask đóng vai trò là Căn cước Công dân điện tử và Bút ký số trong thế giới Web3. Không có ví, chúng ta không thể xác thực danh tính người bỏ phiếu và không thể tạo chữ ký số để ghi phiếu lên Blockchain một cách an toàn."*

**Q: "Hệ thống có điểm yếu gì không?"**
> *"Có, và em đã chuẩn bị sẵn. Điểm yếu lớn nhất là Tấn công Sybil và vấn đề tập trung quyền lực vào Admin. Chúng em đã phân tích và đề xuất hướng giải quyết bằng eKYC và Multi-sig tương ứng (trình bày ở slide cuối)."*
