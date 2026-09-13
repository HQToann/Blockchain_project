# 🟢 NGÀY 9: LẮP RÁP FRONTEND (WEB3 & WEBSOCKETS)

Sân khấu thuộc về **Kỹ sư Giao diện (Frontend Developer)**. Hôm nay bạn sẽ nối Ethers.js vào nút bấm "Bầu chọn", và nối Chart.js vào WebSocket.

> 🛠️ **Yêu cầu:**
> - Tạo thư mục `templates/` và `static/js/` ở thư mục gốc dự án (cùng cấp với `manage.py`).
> - **Bất buộc:** Server phải chạy bằng `daphne` (không dùng `runserver` thông thường nữa!) thì WebSocket mới kết nối được:
> ```bash
> daphne -p 8000 core.asgi:application
> ```

---

## BƯỚC 1: Code HTML và Thư viện

Mở `templates/detail.html` (Trang chi tiết bầu cử):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Chi Tiết Bầu Cử</title>
    <!-- Thư viện Ethers.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ethers/6.7.0/ethers.umd.min.js"></script>
    <!-- Thư viện Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h1 id="electionName">Đang tải...</h1>
    
    <button id="btnConnect" onclick="connectWallet()">Kết Nối MetaMask</button>
    <p id="walletAddress"></p>

    <!-- Biểu đồ -->
    <div style="width: 400px; height: 400px;">
        <canvas id="voteChart"></canvas>
    </div>

    <!-- Danh sách ứng viên để Vote -->
    <div id="candidateList"></div>

    <script src="/static/js/app.js"></script>
</body>
</html>
```

---

## BƯỚC 2: Code JavaScript (Ethers.js + MetaMask)

Tạo thư mục `static/js/`, tạo file `app.js`:

```javascript
let signer = null;
let contract = null;

// Lấy ID cuộc bầu cử từ URL (VD: /election/3/ -> ELECTION_ID = 3)
// window.location.pathname.split('/') trả về ['', 'election', '3', '']
// .filter(Boolean) loại phần tử rỗng: ['election', '3']
// [1] lấy phần tử thứ 2 là '3', parseInt chuyển sang số
const ELECTION_ID = parseInt(window.location.pathname.split('/').filter(Boolean)[1]) || 1;

// ABI của hợp đồng con (Copy từ file Election_ABI.json ngày 2)
const ELECTION_ABI = [
    "function vote(uint256 _candidateId) public"
];
// Địa chỉ hợp đồng của cuộc bầu cử này (Phải lấy từ API Backend)
let CONTRACT_ADDRESS = "";

async function connectWallet() {
    if (window.ethereum == null) {
        alert("Vui lòng cài đặt MetaMask!");
        return;
    }
    const provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    signer = await provider.getSigner();
    
    document.getElementById("walletAddress").innerText = "Đã kết nối ví: " + signer.address;
    
    // Khởi tạo đối tượng hợp đồng
    contract = new ethers.Contract(CONTRACT_ADDRESS, ELECTION_ABI, signer);
}

async function castVote(candidateId) {
    if (!contract) {
        alert("Vui lòng kết nối MetaMask trước!");
        return;
    }
    
    try {
        // Gọi hàm vote trên Blockchain
        const tx = await contract.vote(candidateId);
        alert("Giao dịch đang xử lý... TxHash: " + tx.hash);
        
        // Đợi Blockchain xác nhận (đào block)
        await tx.wait();
        alert("Bầu chọn thành công!");
    } catch (error) {
        console.error(error);
        alert("Lỗi: " + (error.reason || error.message));
    }
}
```

---

## BƯỚC 3: Hứng WebSocket và Vẽ Biểu Đồ

Thêm đoạn mã sau vào cuối file `app.js` để kết nối WebSocket:

```javascript
let myChart = null;

// Hàm tải dữ liệu lần đầu bằng REST API
async function fetchInitialData() {
    const res = await fetch(`/api/elections/${ELECTION_ID}/`);
    const data = await res.json();
    
    CONTRACT_ADDRESS = data.election.contract_addr;
    document.getElementById("electionName").innerText = data.election.name;
    
    // Khởi tạo Chart.js
    const ctx = document.getElementById('voteChart').getContext('2d');
    
    const labels = data.candidates.map(c => c.name);
    const votes = data.candidates.map(c => c.vote_count);
    
    myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: votes,
                backgroundColor: ['#ff6384', '#36a2eb', '#cc65fe']
            }]
        }
    });

    // Tạo các nút Vote
    const listDiv = document.getElementById("candidateList");
    data.candidates.forEach(c => {
        listDiv.innerHTML += `
            <div style="margin:10px; border:1px solid #ccc; padding:10px;">
                <img src="${c.image_url}" width="100"/>
                <h3>${c.name}</h3>
                <button onclick="castVote(${c.id})">Bầu Cho ${c.name}</button>
            </div>
        `;
    });
}

// Hàm khởi tạo WebSocket
function setupWebSocket() {
    // ws://localhost:8000/ws/election/1/
    const wsUrl = `ws://${window.location.host}/ws/election/${ELECTION_ID}/`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = function(e) {
        const payload = JSON.parse(e.data);
        if (payload.type === 'NEW_VOTE') {
            console.log("CÓ NGƯỜI VỪA VOTE!", payload.data);
            // Khi có người vote, tải lại dữ liệu biểu đồ
            // (Trong thực tế, bạn chỉ cần +1 vào mảng data của Chart.js để tối ưu)
            // Tạm thời gọi API tải lại cho dễ:
            fetchInitialData(); 
        }
    };
    
    socket.onclose = function(e) {
        console.error('WebSocket bị ngắt kết nối');
    };
}

// Chạy 2 hàm khi vừa load trang
window.onload = async () => {
    await fetchInitialData();
    setupWebSocket();
};
```

---

## BƯỚC 4: Code JavaScript cho Admin Dashboard (admin.js)

File `app.js` ở trên là dành cho Cử tri. Riêng Admin cần thêm file `static/js/admin.js` để gọi các hàm quản trị trên Smart Contract (Factory & Election). Đây là bước sống còn để kịch bản Demo Ngày 10 hoạt động.

```javascript
let adminSigner = null;
let factoryContract = null;

// Lấy địa chỉ Factory từ cấu hình hoặc API Backend
const FACTORY_ADDRESS = "0xDiaChiFactoryCuaBan...";
const FACTORY_ABI = [
    "function createElection(string memory _name, bool _isPrivate) public",
    "function getDeployedElections() public view returns (address[])"
];
// ABI của Election con để Admin thêm ứng viên và mở hòm phiếu
const ELECTION_ABI = [
    "function addCandidate(string memory _name) public",
    "function startElection() public",
    "function stopElection() public"
];

// 1. Đăng nhập Admin bằng SIWE (Web3)
async function loginAdminSIWE() {
    if (!window.ethereum) return alert("Cài MetaMask!");
    const provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    adminSigner = await provider.getSigner();
    const address = await adminSigner.getAddress();
    
    try {
        // Bước A: Lấy Nonce từ Backend
        const nonceRes = await fetch('/api/auth/nonce/');
        const nonceData = await nonceRes.json();
        
        // Bước B: Ký tin nhắn bằng MetaMask
        const signature = await adminSigner.signMessage(nonceData.nonce);
        
        // Bước C: Gửi chữ ký lên xác thực
        const verifyRes = await fetch('/api/auth/verify/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ address: address, signature: signature })
        });
        const verifyData = await verifyRes.json();
        
        if (verifyData.success) {
            alert("Đăng nhập Admin thành công!");
            // Khởi tạo Factory Contract sau khi đã xác thực
            factoryContract = new ethers.Contract(FACTORY_ADDRESS, FACTORY_ABI, adminSigner);
        } else {
            alert("Lỗi đăng nhập: " + verifyData.error);
        }
    } catch (e) {
        alert("Lỗi SIWE: " + e.message);
    }
}

// 2. Tạo cuộc bầu cử mới (Gọi Factory)
async function createElectionOnChain(name, isPrivate) {
    try {
        const tx = await factoryContract.createElection(name, isPrivate);
        console.log("Đang chờ xác nhận...", tx.hash);
        await tx.wait(); // Chờ block được đào
        alert("Tạo hòm phiếu thành công! Indexer sẽ tự đồng bộ về Database.");
    } catch (e) {
        alert("Lỗi: " + e.message);
    }
}

// 3. Thêm ứng viên (ĐỒNG BỘ: Gọi API lưu DB TRƯỚC, gọi Blockchain SAU)
async function handleAddCandidate(dbElectionId, electionAddress, candidateIdOnChain, candidateName, imageFile) {
    try {
        // Bước A: Upload ảnh lên IPFS
        // CHÚ Ý: field phải là "image" (khớp với request.FILES['image'] trong views.py)
        // và endpoint đúng là /api/upload/ (không phải /api/ipfs/upload/)
        const formData = new FormData();
        formData.append("image", imageFile);
        const uploadRes = await fetch('/api/upload/', { method: 'POST', body: formData });
        const uploadData = await uploadRes.json();
        if (!uploadRes.ok) throw new Error(uploadData.error || "Lỗi upload IPFS");
        
        // Bước B: Lưu vào Django Database
        const dbRes = await fetch(`/api/elections/${dbElectionId}/candidates/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                candidate_id: candidateIdOnChain, 
                name: candidateName, 
                image_cid: uploadData.cid
            })
        });
        const dbData = await dbRes.json();
        if (!dbRes.ok) throw new Error(dbData.error || "Lỗi lưu DB");

        // Bước C: Ghi lên Blockchain (Chỉ thực hiện khi DB đã lưu thành công)
        const election = new ethers.Contract(electionAddress, ELECTION_ABI, adminSigner);
        const tx = await election.addCandidate(candidateName);
        console.log("Đang chờ xác nhận Blockchain...");
        await tx.wait();
        alert("Thêm ứng viên lên Blockchain & Database thành công!");
    } catch (e) {
        alert("Lỗi: " + e.message);
    }
}

// 4. Mở hòm phiếu (Bắt đầu cho phép vote)
async function startElection(electionAddress) {
    try {
        const election = new ethers.Contract(electionAddress, ELECTION_ABI, adminSigner);
        const tx = await election.startElection();
        await tx.wait();
        alert("Đã mở hòm phiếu! Cử tri có thể bắt đầu bầu chọn.");
    } catch (e) {
        alert("Lỗi: " + e.message);
    }
}
```

---

## BƯỚC 5: Giao diện HTML cho Admin Dashboard (admin_dashboard.html)

Tạo file `templates/admin_dashboard.html` để Admin có chỗ bấm nút gọi các hàm JavaScript ở Bước 4. Chú ý nút "Đăng nhập Web3" để kích hoạt chữ ký SIWE.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard</title>
    <!-- Tải ethers.js -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/ethers/6.7.0/ethers.umd.min.js"></script>
</head>
<body>
    <h1>Quản Trị Bầu Cử (Admin)</h1>
    
    <!-- Nút kết nối Admin -->
    <button onclick="loginAdminSIWE()">Đăng Nhập Web3 (Admin)</button>
    <hr>

    <!-- Form tạo Election -->
    <h2>1. Tạo Cuộc Bầu Cử Mới</h2>
    <input type="text" id="pollName" placeholder="Tên cuộc bầu cử (VD: Lớp 12A1)">
    <label><input type="checkbox" id="isPrivate"> Private Poll (Bầu kín)</label>
    <button onclick="handleCreateElection()">Tạo Hòm Phiếu (Gọi Factory)</button>

    <hr>
    
    <h2>2. Danh sách các hòm phiếu (Ví dụ tĩnh)</h2>
    <p><i>Trong thực tế, bạn sẽ dùng fetch('/api/elections/') để render danh sách này bằng JS. Dưới đây là 1 dòng ví dụ để có nút bấm:</i></p>
    
    <table border="1">
        <tr>
            <th>Tên Hòm Phiếu</th>
            <th>Contract Address</th>
            <th>Hành động</th>
        </tr>
        <tr>
            <td>Bầu Trưởng Thôn</td>
            <td>0x123...abc</td>
            <td>
                <!-- Form Thêm Ứng Viên Đồng Bộ -->
                <input type="text" id="candName" placeholder="Tên ứng viên">
                <input type="file" id="candFile" accept="image/*">
                <!-- dbElectionId = 1, ContractAddr = 0x123...abc, candidateIdOnChain = 0 -->
                <button onclick="submitCandidate(1, '0x123...abc', 0)">Thêm Ứng Viên A (ID=0)</button>
                <br><br>
                <!-- Gọi hàm startElection -->
                <button onclick="startElection('0x123...abc')">Mở Hòm Phiếu</button>
            </td>
        </tr>
    </table>

    <script src="/static/js/admin.js"></script>
    <script>
        // Hàm bọc để lấy dữ liệu từ Form truyền vào admin.js
        function handleCreateElection() {
            const name = document.getElementById("pollName").value;
            const isPrivate = document.getElementById("isPrivate").checked;
            createElectionOnChain(name, isPrivate);
        }
        
        // Hàm bọc để lấy Form thêm ứng viên
        function submitCandidate(dbElectionId, contractAddr, candidateIdOnChain) {
            const name = document.getElementById("candName").value;
            const file = document.getElementById("candFile").files[0];
            if (!file) return alert("Vui lòng chọn ảnh!");
            handleAddCandidate(dbElectionId, contractAddr, candidateIdOnChain, name, file);
        }
    </script>
</body>
</html>
```

---

## BƯỚC 6: Trang Chủ - index.html

Tạo file `templates/index.html`. Đây là trang mở đầu tiên khi Admin vào `http://127.0.0.1:8000/` — cần có nút link tới Dashboard và danh sách các cuộc bầu cử để Cử tri có thể click vào tham gia.

```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Hệ Thống Bầu Cử Phân Tán</title>
</head>
<body>
    <h1>Hệ Thống Bầu Cử Blockchain</h1>
    <a href="/dashboard/">🔑 Vào Trang Quản Trị (Admin)</a>
    <hr>

    <h2>Danh Sách Cuộc Bầu Cử</h2>
    <div id="electionList"><p>Đang tải...</p></div>

    <script>
    async function loadElections() {
        const res = await fetch('/api/elections/');
        const data = await res.json();
        const container = document.getElementById('electionList');
        
        if (!data.elections || data.elections.length === 0) {
            container.innerHTML = '<p>Chưa có cuộc bầu cử nào.</p>';
            return;
        }
        
        container.innerHTML = data.elections.map(e => `
            <div style="border:1px solid #ccc; margin:10px; padding:15px;">
                <h3>${e.name}</h3>
                <p>Trạng thái: <strong>${e.status}</strong> | ${e.is_private ? '🔒 Bầu kín' : '🌍 Công khai'}</p>
                <a href="/election/${e.id}/">🗳️ Tham gia bầu cử này</a>
            </div>
        `).join('');
    }
    
    window.onload = loadElections;
    </script>
</body>
</html>
```

---
🎉 **XONG NGÀY 9!**
Frontend đã hoàn tất vòng tuần hoàn: **Nhìn thấy dữ liệu -> Bấm Vote -> MetaMask Ký -> Đẩy lên Mạng -> Indexer Bắt Được -> Channels Gửi WebSocket -> Chart.js Nhảy Số.**
3 file HTML đã đủ: `index.html` (danh sách), `detail.html` (cử tri vote), `admin_dashboard.html` (Admin quản trị). Cố lên, chúng ta sắp về đích!
