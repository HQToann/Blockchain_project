# 2. TÀI LIỆU 2: THIẾT KẾ SMART CONTRACT (FACTORY PATTERN)

Với kiến trúc dành cho 3 người, Smart Contract được nâng cấp với **Factory Pattern**. Điều này biến hệ thống thành một Nền tảng (Platform) thực thụ, cho phép sinh ra hàng ngàn cuộc bầu cử độc lập mà không cần tự tay Deploy lại.

---

## 2.1. Kiến Trúc Factory

Thay vì 1 hợp đồng, chúng ta sẽ viết 2 hợp đồng trong cùng file `VotingSystem.sol`:

1. **`ElectionFactory`**: Hợp đồng "Mẹ", quản lý quyền sinh sát và sinh ra các hợp đồng con.
2. **`Election`**: Hợp đồng "Con", đại diện cho 1 hòm phiếu duy nhất (VD: "Bầu Bí Thư", "Bầu Lớp Trưởng").

---

## 2.2. Chi Tiết `ElectionFactory.sol`

Hợp đồng này được Deploy duy nhất **MỘT LẦN** lên Sepolia.

**Nhiệm vụ:**
- Chứa mảng `address[] public deployedElections` lưu trữ địa chỉ các hợp đồng con.
- Có hàm `createElection(string memory _name, bool _isPrivate)`.
- Khi Admin từ Django gọi hàm này, Factory sẽ chạy lệnh `new Election(...)`.
- Tự động gán người tạo (Admin) làm Chủ sở hữu (`admin` của hợp đồng con).

**Event phát ra:**
- `event ElectionCreated(address indexed electionAddress, string name, address admin, bool isPrivate);` (Backend sẽ dùng Indexer lắng nghe event này để tự động cập nhật địa chỉ Contract mới vào Database, bao gồm cả trường `is_private`).

---

## 2.3. Chi Tiết `Election.sol` (Hợp đồng con)

Hợp đồng này **KHÔNG** tự deploy. Nó chỉ được sinh ra từ Factory.

### A. Biến Trạng Thái (State Variables)
- `string public electionName`: Tên cuộc bầu cử.
- `address public admin`: Người tạo ra hòm phiếu này.
- `bool public isPrivate`: Cờ xác định hòm phiếu kín.
- `bool public isOpen`: Trạng thái hòm phiếu (Đóng/Mở).
- `mapping(address => bool) public hasVoted`: Đánh dấu ví đã vote.
- `mapping(address => bool) public whitelist`: Whitelist cho Private Poll.

### B. Modifier (Bộ lọc kiểm tra)
- `onlyAdmin`: Chỉ `admin` mới được gọi hàm. Bắt buộc: `require(msg.sender == admin, "Not admin");`.
- `onlyWhileOpen`: Bắt buộc `isOpen == true`.

### C. Các Hàm (Functions) Chính

| Hàm | Phân quyền | Giải thích |
|:---|:---|:---|
| `constructor(address _admin, ...)` | Factory gọi | Factory sẽ truyền `msg.sender` (ví Admin) vào `_admin`. |
| `addCandidate(string name)` | `onlyAdmin` | Thêm phương án bầu. Chỉ thêm được khi hòm chưa mở. |
| `addToWhitelist(address[] voters)` | `onlyAdmin` | Đẩy danh sách ví hợp lệ lên mạng (Private Poll). |
| `startElection()` | `onlyAdmin` | Bật `isOpen = true`. |
| `stopElection()` | `onlyAdmin` | Tắt `isOpen = false`. |
| `vote(uint256 candidateId)` | Công khai | Kiểm tra chưa vote, kiểm tra whitelist (nếu private). Không lưu `candidateId` để bảo vệ quyền riêng tư! Phát Event `VoteCast`. |

### D. Events
```solidity
event VoteCast(uint256 indexed candidateId);
event CandidateAdded(uint256 indexed candidateId, string name);
```

---

## 2.4. Phân Tích Bảo Mật (Security & Privacy)

> [!CAUTION]
> **Giới hạn kỹ thuật về Quyền Riêng Tư trên Blockchain Công Khai:**
> Dù Event `VoteCast` không chứa địa chỉ ví, và Database không lưu `candidateId` với `voter_address`, **toàn bộ dữ liệu truyền vào hàm `vote(uint256 candidateId)` đều là public trong payload của giao dịch**. Bất kỳ ai kiểm tra `TxHash` trên Etherscan đều xem được `Input Data`. 
> *(Để ẩn danh tuyệt đối, cần ZKP trong tương lai).*

---

## 2.5. Quy Trình Deploy Thực Tế
1. Cài đặt và code bằng **Hardhat** trực tiếp trong VS Code.
2. Cấu hình `hardhat.config.js` để kết nối mạng **Sepolia** (qua Alchemy RPC) và nạp Private Key (từ `.env`).
3. Chạy lệnh `npx hardhat compile` để biên dịch file `VotingSystem.sol`.
4. Viết script `ignition/modules/Factory.js` chỉ định deploy `ElectionFactory`.
5. Chạy lệnh deploy: `npx hardhat ignition deploy... --network sepolia`.
6. ✅ **LƯU LẠI ngay:** `Contract Address` của Factory và `ABI` (cả 2 ABI). Lắp vào Backend.
