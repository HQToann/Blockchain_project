# 4. FRONTEND & WEB3 INTEGRATION

---

## 4.1. Tổng Quan

Frontend được xây dựng bằng **HTML/CSS/JS thuần** để giữ sự đơn giản và tập trung vào phần tích hợp Web3. Hai thư viện JavaScript chính được nhúng qua CDN:
- **Ethers.js v6:** Kết nối MetaMask, gửi giao dịch lên Smart Contract.
- **Chart.js:** Vẽ biểu đồ cột và biểu đồ tròn kết quả bầu cử.

---

## 4.2. Cấu Trúc Các Trang

### Trang 1: Danh Sách Bầu Cử (`index.html`)
- Hiển thị danh sách card các cuộc bầu cử.
- Mỗi card: Tên, trạng thái (`🟢 Đang diễn ra` / `🔴 Đã kết thúc`), tổng số phiếu hiện tại, chế độ (Public/Private).
- Click vào card → chuyển đến trang chi tiết.

### Trang 2: Chi Tiết & Bỏ Phiếu (`detail.html`)
Đây là trang trung tâm của dự án, gồm các khối sau:

**Header**: Tên bầu cử, mô tả, trạng thái, thời gian.

**Bảng ứng viên:** Mỗi ứng viên hiển thị dưới dạng card bao gồm ảnh (từ IPFS), tên, số phiếu, tỉ lệ % và thanh tiến trình (progress bar).

**Biểu đồ:**
```html
<canvas id="barChart"></canvas>    <!-- Biểu đồ cột -->
<canvas id="pieChart"></canvas>    <!-- Biểu đồ tròn -->
```

**Thống kê:**
```
📊 Tổng phiếu: 245  |  🏆 Dẫn đầu: Phương án A (58%)
```

**Khu vực hành động (Action Zone):**
- Chưa kết nối ví → Hiện nút `🦊 Kết nối MetaMask`
- Đã kết nối, chưa vote, hòm đang mở → Hiện các nút bầu chọn
- Đã vote rồi → Hiện thông báo xanh + TxHash (link Etherscan)
- Hòm đã đóng → Hiện thông báo kết quả chính thức

**Bảng lịch sử phiếu (Real-time):**

| Thời gian | Địa chỉ ví | Khối | TxHash |
|:---|:---|:---|:---|
| 14:32:10 | `0x123...abc` | 5123000 | [🔗](https://sepolia.etherscan.io) |

### Trang 3: Admin Dashboard (`admin_dashboard.html`)
- Tổng quan: Số cuộc bầu cử, tổng phiếu toàn hệ thống.
- Danh sách cuộc bầu cử với nút điều khiển: **Mở hòm phiếu** / **Đóng hòm phiếu** (gọi Smart Contract).
- Form tạo cuộc bầu cử mới.
- Form upload ảnh ứng viên lên IPFS.

---

## 4.3. Luồng Tích Hợp Ethers.js & WebSockets

### Bước 1: Đăng nhập Web3 (SIWE) cho Admin
Khi Admin bấm "Đăng nhập":
1. Gọi `fetch('/api/auth/nonce/')` lấy mã ngẫu nhiên.
2. Dùng Ethers.js gọi `signer.signMessage(nonce)`.
3. Gửi chữ ký lên `POST /api/auth/verify/`.
4. Nhận token/session.

### Bước 2: Kết nối WebSocket (Real-time)
Khi cử tri mở trang Chi tiết, JavaScript tự động kết nối:
```javascript
// election_id được lấy động từ URL, không hardcode
const electionId = window.location.pathname.split('/').filter(Boolean)[1];
const ws = new WebSocket(`ws://${window.location.host}/ws/election/${electionId}/`);
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'NEW_VOTE') {
        // Cập nhật Chart.js ngay lập tức!
        updateChart(data.data.candidate_id);
    }
};
```

### Bước 3: Kết nối MetaMask (Cử tri chuẩn bị bầu chọn)
```javascript
const provider = new ethers.BrowserProvider(window.ethereum);
await provider.send("eth_requestAccounts", []);
const signer = await provider.getSigner();
const voterAddress = await signer.getAddress();
```

### Bước 4: Khởi tạo Contract Instance
```javascript
// CONTRACT_ADDRESS và ABI lấy từ file Election_ABI.json sau khi deploy
const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, signer);
```

### Bước 5: Gọi hàm Vote
```javascript
async function castVote(candidateId) {
    try {
        const tx = await contract.vote(candidateId);
        showLoading("Đang gửi phiếu lên Blockchain...");
        const receipt = await tx.wait();  // Chờ giao dịch được xác nhận
        showSuccess(`Bỏ phiếu thành công! TxHash: ${receipt.hash}`);
    } catch (error) {
        if (error.message.includes("Already voted")) {
            showError("Đã bỏ phiếu rồi!");
        } else {
            showError("Giao dịch thất bại. Vui lòng thử lại.");
        }
    }
}
```

### Bước 6: Đọc Trạng Thái từ Contract (Không tốn Gas)
```javascript
// Kiểm tra hòm phiếu đã mở chưa và ví hiện tại đã vote chưa
const isOpen = await contract.isOpen();
const alreadyVoted = await contract.hasVoted(voterAddress);
// Lưu ý: Tên ứng viên và ảnh lấy từ API Backend, không gọi trực tiếp từ Contract
```

---

## 4.4. Biểu Đồ Real-time với Chart.js

```javascript
// Khởi tạo biểu đồ cột
const barChart = new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
        labels: candidates.map(c => c.name),
        datasets: [{
            label: 'Số phiếu',
            data: candidates.map(c => Number(c.voteCount)),
            backgroundColor: ['#4F46E5', '#10B981', '#F59E0B', '#EF4444'],
        }]
    }
});

// Cập nhật biểu đồ Real-time mỗi 10 giây
setInterval(async () => {
    const results = await fetch(`/api/elections/${electionId}/results/`);
    const data = await results.json();
    barChart.data.datasets[0].data = data.candidates.map(c => c.vote_count);
    barChart.update('active');
}, 10000);
```

---

## 4.5. Xử Lý Các Trạng Thái UI

```javascript
async function updateActionZone() {
    const isOpen = await contract.isOpen();
    const hasVoted = await contract.hasVoted(voterAddress);

    if (!isOpen) {
        showBanner("🔴 Cuộc bầu cử đã kết thúc", "red");
    } else if (hasVoted) {
        showBanner("✅ Bạn đã hoàn thành bỏ phiếu!", "green");
    } else {
        showVoteButtons();  // Hiện các nút bầu chọn
    }
}
```
