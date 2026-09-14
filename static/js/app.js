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

// Hứng Websocket và vẽ biểu đồ
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
