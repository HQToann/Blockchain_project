// --- CONFIGURATION ---
const RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/L_p_5WfT_l6U2640L140Hn3f0qV9xM4p"; // Cấu hình RPC (Tùy chọn cho frontend)
const EXPECTED_CHAIN_ID = 11155111; // Sepolia Testnet
const ELECTION_ID = parseInt(window.location.pathname.split('/').filter(Boolean)[1]) || 1;

let signer = null;
let contract = null;

// ABI đầy đủ cho Frontend
const ELECTION_ABI = [
    "function vote(uint256 _candidateId) public",
    "function hasVoted(address) public view returns (bool)",
    "function whitelist(address) public view returns (bool)",
    "function isPrivate() public view returns (bool)"
];

let CONTRACT_ADDRESS = "";
let electionData = null;
let userHasVoted = false;
let userIsWhitelisted = false;

// Khởi tạo Chart.js
let myChart = null;

// --- UTILS: TOAST NOTIFICATION ---
function showToast(message, type="info") {
    let bgColor = "#58a6ff";
    if (type === "success") bgColor = "#3fb950";
    if (type === "error") bgColor = "#f85149";
    if (type === "warning") bgColor = "#e3b341";

    Toastify({
        text: message,
        duration: 4000,
        gravity: "bottom", // bottom
        position: "right", // right
        style: {
            background: bgColor,
            borderRadius: "8px",
            fontFamily: "'Inter', sans-serif",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
        }
    }).showToast();
}

// 1. KẾT NỐI VÍ & KIỂM TRA TRẠNG THÁI
async function connectWallet() {
    if (window.ethereum == null) {
        showToast("Vui lòng cài đặt MetaMask!", "error");
        return;
    }
    const provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    signer = await provider.getSigner();
    
    document.getElementById("walletAddress").innerText = "Đã kết nối ví: " + signer.address;
    
    contract = new ethers.Contract(CONTRACT_ADDRESS, ELECTION_ABI, signer);
    
    // Kiểm tra trạng thái đã vote
    userHasVoted = await contract.hasVoted(signer.address);
    
    // Kiểm tra whitelist nếu là hòm phiếu kín
    if (electionData && electionData.election.is_private) {
        userIsWhitelisted = await contract.whitelist(signer.address);
    } else {
        userIsWhitelisted = true; // Hòm phiếu công khai thì ai cũng hợp lệ
    }

    renderCandidateButtons(); // Cập nhật lại nút vote
}

// 2. XỬ LÝ BỎ PHIẾU
async function castVote(candidateId) {
    if (!contract) {
        showToast("Vui lòng kết nối MetaMask trước!", "warning");
        return;
    }
    
    // Đổi trạng thái Loading
    const btn = document.getElementById(`btnVote_${candidateId}`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner"></span> Đang xử lý...`;
        btn.style.opacity = "0.7";
        btn.style.cursor = "not-allowed";
    }

    try {
        const tx = await contract.vote(candidateId);
        showToast("Giao dịch đang được gửi lên Blockchain... Đợi khoảng 10-15s", "info");
        
        await tx.wait(); // Chờ xác nhận
        
        showToast("Bầu chọn thành công! Cảm ơn bạn.", "success");
        userHasVoted = true; 
        renderCandidateButtons(); // Khóa tất cả nút
    } catch (error) {
        console.error(error);
        
        // Bắt lỗi Hết Tiền (Out of Gas)
        let errorMsg = error.reason || error.message;
        if (error.code === "INSUFFICIENT_FUNDS") {
            errorMsg = "Ví của bạn không đủ ETH (Sepolia) để trả phí Gas! Vui lòng nạp thêm ETH.";
        } else if (error.info && error.info.error && error.info.error.message.includes("insufficient funds")) {
             errorMsg = "Ví của bạn không đủ ETH (Sepolia) để trả phí Gas! Vui lòng nạp thêm ETH.";
        } else if (error.message.includes("User denied")) {
            errorMsg = "Bạn vừa từ chối giao dịch!";
        }

        showToast("Lỗi: " + errorMsg, "error");
        renderCandidateButtons(); // Phục hồi nút nếu lỗi
    }
}

// 3. TẢI DỮ LIỆU BAN ĐẦU
async function fetchInitialData() {
    const res = await fetch(`/api/elections/${ELECTION_ID}/`);
    electionData = await res.json();
    
    CONTRACT_ADDRESS = electionData.election.contract_addr;
    document.getElementById("electionName").innerText = electionData.election.name;
    
    let statusBadge = electionData.election.status;
    let statusText = statusBadge;
    if (statusBadge === 'pending') statusText = 'Sắp diễn ra';
    if (statusBadge === 'active') statusText = 'Đang diễn ra';
    if (statusBadge === 'closed') statusText = 'Đã kết thúc';

    document.getElementById("electionStatusBadge").innerHTML = `
        <span class="badge ${statusBadge}">${statusText}</span>
        <span class="badge ${electionData.election.is_private ? 'private' : 'public'}">${electionData.election.is_private ? '🔒 Bầu kín' : '🌍 Công khai'}</span>
    `;
    
    renderChart();
    renderCandidateDOM(); // Vẽ khung HTML cho ứng viên
    renderCandidateButtons(); // Cập nhật trạng thái nút ban đầu
}

// 4. RENDER BIỂU ĐỒ
function renderChart() {
    const ctx = document.getElementById('voteChart').getContext('2d');
    const labels = electionData.candidates.map(c => c.name);
    const votes = electionData.candidates.map(c => c.vote_count);
    
    if (myChart) myChart.destroy();
    myChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: votes,
                backgroundColor: ['#ff6384', '#36a2eb', '#cc65fe', '#4bc0c0', '#ffce56']
            }]
        }
    });
}

// 5. RENDER KHUNG DANH SÁCH ỨNG VIÊN (Chỉ chạy 1 lần)
function renderCandidateDOM() {
    const listDiv = document.getElementById("candidateList");
    listDiv.innerHTML = "";
    electionData.candidates.forEach(c => {
        listDiv.innerHTML += `
            <div class="candidate-card">
                <img src="${c.image_url}" alt="${c.name}"/>
                <h3>${c.name}</h3>
                <div class="vote-stats" id="voteCount_${c.id}">${c.vote_count} phiếu</div>
                <div class="percentage-bar">
                    <div class="percentage-fill" id="voteFill_${c.id}" style="width: ${c.percentage}%"></div>
                </div>
                <p style="margin-top:0" id="votePercent_${c.id}">${c.percentage}%</p>
                <div id="btnContainer_${c.id}" style="width: 100%;"></div>
            </div>
        `;
    });
}

// 6. RENDER NÚT BẦU CHỌN (Chạy mỗi khi có cập nhật trạng thái ví hoặc hòm phiếu)
function renderCandidateButtons() {
    if (!electionData) return;

    const status = electionData.election.status;
    
    electionData.candidates.forEach(c => {
        const container = document.getElementById(`btnContainer_${c.id}`);
        if (!container) return;

        let btnHtml = "";
        let btnDisabled = false;
        let btnText = `🗳️ Bầu Cho ${c.name}`;

        // Các lớp kiểm tra điều kiện để Khóa nút
        if (status !== 'active') {
            btnDisabled = true;
            btnText = "Chưa mở bầu cử";
        } else if (userHasVoted) {
            btnDisabled = true;
            btnText = "✅ Đã bỏ phiếu";
        } else if (signer && !userIsWhitelisted) {
            btnDisabled = true;
            btnText = "⛔ Không có quyền bầu";
        }

        const style = btnDisabled ? 'background:var(--text-secondary); cursor:not-allowed;' : '';
        btnHtml = `<button id="btnVote_${c.id}" onclick="castVote(${c.id})" class="btn" style="width:100%; transition: all 0.2s; ${style}" ${btnDisabled ? 'disabled' : ''}>${btnText}</button>`;
        container.innerHTML = btnHtml;
    });
}

// 7. WEBSOCKET REAL-TIME (Cập nhật không giật lag)
function setupWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsProtocol}${window.location.host}/ws/election/${ELECTION_ID}/`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = async function(e) {
        const payload = JSON.parse(e.data);
        if (payload.type === 'NEW_VOTE') {
            // Thay vì tải lại toàn bộ DOM, chỉ tải lại dữ liệu từ API và cập nhật số liệu
            const res = await fetch(`/api/elections/${ELECTION_ID}/`);
            const newData = await res.json();
            
            electionData.candidates = newData.candidates;
            electionData.election.total_votes = newData.election.total_votes;

            // Cập nhật biểu đồ
            myChart.data.datasets[0].data = electionData.candidates.map(c => c.vote_count);
            myChart.update();

            // Cập nhật DOM số liệu mượt mà
            electionData.candidates.forEach(c => {
                document.getElementById(`voteCount_${c.id}`).innerText = `${c.vote_count} phiếu`;
                document.getElementById(`voteFill_${c.id}`).style.width = `${c.percentage}%`;
                document.getElementById(`votePercent_${c.id}`).innerText = `${c.percentage}%`;
            });
        }
    };
    
    socket.onclose = function(e) {
        console.error('WebSocket bị ngắt kết nối');
    };
}

// CHẠY KHI TẢI TRANG
window.onload = async () => {
    await fetchInitialData();
    setupWebSocket();
};
