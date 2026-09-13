# 🟢 NGÀY 1 & 2: CODE VÀ DEPLOY SMART CONTRACT VỚI FACTORY PATTERN

Chào mừng bạn đến với ngày code đầu tiên! Trọng tâm của 2 ngày này là **Kỹ sư Blockchain** trong nhóm. Chúng ta sẽ code hợp đồng thông minh (Smart Contract) và đưa nó lên mạng thử nghiệm Sepolia.

> **💡 Lời khuyên:** Hãy làm thật chậm, đọc kỹ giải thích từng dòng code để lúc đi bảo vệ đồ án, giảng viên hỏi chỗ nào bạn cũng trả lời được.
> 
> [!WARNING]
> **Quy ước Tối quan trọng cho toàn dự án:** Cả nhóm PHẢI thống nhất dùng chung 1 ví MetaMask duy nhất cho vai trò Admin xuyên suốt dự án.
> - Kỹ sư Blockchain dùng ví này để deploy Factory (nhằm chiếm quyền `factoryOwner` trên Blockchain).
> - Kỹ sư Backend sẽ dùng chính địa chỉ ví này làm giá trị `ADMIN_WALLET_ADDRESS` trong `.env` ở Ngày 3-4 (để cấp quyền Admin trên Web).
> 
> Nếu 2 người dùng 2 ví khác nhau, Backend sẽ không có quyền tạo hòm phiếu trên Blockchain!

---

## BƯỚC 1: Chuẩn bị Ví và Tiền ảo (Sepolia ETH)

Để đưa code lên Blockchain, chúng ta cần ví và tiền để trả "phí Gas" (hoàn toàn miễn phí vì dùng mạng Testnet).

1. **Cài ví MetaMask:** 
   - Lên Chrome Extension, tìm và cài đặt **MetaMask**.
   - Tạo ví mới, **LƯU KỸ 12 TỪ KHÓA** ra giấy (Không lưu trên máy tính).
2. **Bật mạng Sepolia:**
   - Trong MetaMask, bấm vào nút chọn mạng (góc trên cùng bên trái) -> Bật "Show test networks" -> Chọn **Sepolia**.
3. **Xin Sepolia ETH (Tiền giả):**
   - Truy cập: [https://sepoliafaucet.com/](https://sepoliafaucet.com/) hoặc [https://cloud.google.com/application/web3/faucet/ethereum/sepolia](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)
   - Đăng nhập (nếu cần), dán địa chỉ ví MetaMask của bạn vào và nhận 0.5 ETH. Đợi vài phút để tiền về ví.

---

## BƯỚC 2: Code Smart Contract với Hardhat (VS Code)

Chúng ta sẽ dùng **Hardhat** – một công cụ chuyên nghiệp để code và deploy Smart Contract trực tiếp trong VS Code. Bạn không cần dùng Remix IDE nữa.

### 2.1. Giải ngố về các "File lạ" vừa xuất hiện
Lúc nãy, hệ thống đã tự động cài đặt môi trường Hardhat cho bạn. Bạn sẽ thấy thư mục dự án xuất hiện rất nhiều file mới. Đây là ý nghĩa của chúng:
- `package.json` & `node_modules/`: Nền tảng Node.js. Chứa danh sách và mã nguồn của các công cụ, thư viện phụ trợ (như chính bản thân Hardhat).
- `hardhat.config.js`: "Trái tim" của Hardhat. File này quy định chúng ta xài phiên bản Solidity nào (0.8.20), và kết nối với mạng Blockchain nào (Sepolia).
- `contracts/VotingSystem.sol`: Nơi chứa mã nguồn chính của hợp đồng.
- `ignition/modules/Factory.js`: Kịch bản triển khai (Deploy Script). Thay vì bấm nút trên web, đoạn code JavaScript này sẽ tự động ra lệnh cho Hardhat mang contract đẩy lên Blockchain.

### 2.2. Đọc hiểu Smart Contract
1. Đảm bảo bạn đang mở Terminal tại thư mục gốc `Blockchain_Project`.
2. Mở file `contracts/VotingSystem.sol` (mình đã đưa code sẵn vào cho bạn).
3. Đọc kỹ comment tiếng Việt trong file để hiểu logic. File này chứa 2 hợp đồng: `Election` (Hòm phiếu) và `ElectionFactory` (Xưởng đúc hòm phiếu).

---

## BƯỚC 3: Cấu hình Môi trường (Cực kỳ quan trọng)

Để Hardhat có thể thay mặt bạn đẩy code lên mạng Sepolia, bạn cần khai báo URL mạng và Private Key của ví.

1. Mở file `.env` (ngay thư mục gốc dự án).
2. Tìm dòng `ALCHEMY_RPC_URL` và điền URL của Alchemy (Bạn vào Alchemy.com -> tạo App mạng Sepolia -> copy HTTPS URL).
3. Tìm dòng `PRIVATE_KEY` và điền khóa riêng tư của ví MetaMask.
   - *Cách lấy:* Mở MetaMask -> Bấm dấu 3 chấm góc phải -> Account Details -> Show Private Key.
   - **CẢNH BÁO:** TUYỆT ĐỐI KHÔNG dùng ví có chứa tiền thật (Mainnet ETH) cho việc này!

---

## BƯỚC 4: Compile (Biên dịch bằng lệnh)

Thay vì bấm nút trên Remix, chúng ta dùng lệnh để Hardhat dịch file `.sol` (Solidity) sang mã máy EVM.
Mở Terminal và gõ lệnh:
```bash
npx hardhat compile
```
- **`npx`**: Câu lệnh để gọi công cụ Hardhat đang cài ẩn trong thư mục `node_modules`.
Nếu màn hình hiện `Compiled 2 Solidity files successfully`, tức là code không có lỗi. Hardhat sẽ tự động sinh ra thư mục `artifacts/` chứa ABI của hợp đồng.

---

## BƯỚC 5: Deploy (Triển khai lên Sepolia)

Chúng ta sẽ dùng **Hardhat Ignition** (công cụ deploy mới nhất của Hardhat). Đoạn code trong `ignition/modules/Factory.js` sẽ gọi hợp đồng `ElectionFactory` và nói cho Hardhat biết cần phải deploy nó.

Chạy lệnh sau trên Terminal:
```bash
npx hardhat ignition deploy ignition/modules/Factory.js --network sepolia
```

Chờ khoảng 15-30 giây để giao dịch được gửi lên Blockchain. Khi xong, Terminal sẽ in ra thông báo tương tự thế này:
```
Deployed addresses
FactoryModule#ElectionFactory - 0x123abc...
```

---

## BƯỚC 6: Lấy thông tin quan trọng lưu lại

Đây là những thông tin tối quan trọng mà Kỹ sư Blockchain phải chuyển cho Kỹ sư Backend (hoặc để tự dùng ở các ngày sau):

1. **Contract Address (Địa chỉ Factory):**
   - Chính là dòng địa chỉ `0x...` vừa in ra ở màn hình Terminal sau khi deploy xong. Hãy copy lưu ra một file nháp (Note).
2. **ABI của ElectionFactory:**
   - Mở file `artifacts/contracts/VotingSystem.sol/ElectionFactory.json`.
   - Tìm thuộc tính `"abi": [...]`, copy toàn bộ mảng `[...]` đó và dán vào file `Factory_ABI.json` ở thư mục gốc.
3. **ABI của Election (Hợp đồng con):**
   - Mở file `artifacts/contracts/VotingSystem.sol/Election.json`.
   - Copy mảng `"abi": [...]` và dán vào file `Election_ABI.json`.

---
🎉 **CHÚC MỪNG BẠN ĐÃ HOÀN THÀNH NGÀY 1 & 2 VỚI HARDHAT!** 🎉
Bây giờ, Kỹ sư Blockchain đã có đủ "Đồ chơi" (Contract Address + ABI) để gửi cho đội Backend bắt đầu code Django ở Ngày 3.

**Bạn hãy tự chạy lệnh deploy đi nhé, nếu báo lỗi thiếu số dư (insufficient funds) thì nhớ vòi thêm Sepolia ETH. Xong xuôi thì báo mình!**
