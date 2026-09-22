// --- CONFIGURATION ---

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

// Hàm chống XSS (Cross-Site Scripting)
function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Lấy CSRF token từ cookie (Django gửi qua cookie 'csrftoken')
function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}

// --- UTILS: TOAST NOTIFICATION ---
function showToast(message, type="info") {
    let bgColor = "#58a6ff";
    if (type === "success") bgColor = "#3fb950";
    if (type === "error") bgColor = "#f85149";
    if (type === "warning") bgColor = "#e3b341";

    Toastify({
        text: message,
        duration: 5000,
        gravity: "bottom",
        position: "right",
        style: {
            background: bgColor,
            borderRadius: "8px",
            fontFamily: "'Inter', sans-serif",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
        }
    }).showToast();
}

// --- UTILS: TX STATUS BADGE ---
function txStatusBadge(status) {
    const map = {
        'pending':     ['⏳ Đang xếp hàng', 'tx-pending'],
        'broadcasted': ['📡 Đang chờ xác nhận', 'tx-broadcasted'],
        'confirmed':   ['✅ Đã xác nhận', 'tx-confirmed'],
        'failed':      ['❌ Thất bại', 'tx-failed'],
    };
    const [text, cls] = map[status] || ['—', ''];
    return `<span class="badge ${cls}">${text}</span>`;
}

// 1. KẾT NỐI VÍ & KIỂM TRA TRẠNG THÁI
async function connectWallet() {
    if (window.ethereum == null) {
        showToast("Vui lòng cài đặt MetaMask!", "error");
        return;
    }
    const provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send("eth_requestAccounts", []);

    // Kiểm tra đúng mạng lưới Sepolia
    const network = await provider.getNetwork();
    if (Number(network.chainId) !== EXPECTED_CHAIN_ID) {
        showToast(`Sai mạng lưới! Vui lòng chuyển sang Sepolia Testnet (Chain ID: ${EXPECTED_CHAIN_ID}).`, "error");
        return;
    }

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

// --- ADMIN WHITELIST ---
async function addWhitelist() {
    const addressInput = document.getElementById("whitelistAddress").value.trim();
    const btn = document.getElementById("btnWhitelist");
    const status = document.getElementById("whitelistStatus");

    if (!addressInput) {
        showToast("Vui lòng nhập địa chỉ ví!", "warning");
        return;
    }

    // Kiểm tra định dạng ví Ethereum
    if (!/^0x[a-fA-F0-9]{40}$/.test(addressInput)) {
        showToast("Địa chỉ ví không hợp lệ!", "error");
        return;
    }

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Đang xử lý...`;
    status.innerText = "Đang gửi yêu cầu...";
    status.style.color = "var(--text-secondary)";

    try {
        const response = await fetch(`/api/elections/${ELECTION_ID}/whitelist/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()  // Fix #1: Gửi CSRF token theo yêu cầu của Django
            },
            credentials: 'same-origin',        // Đảm bảo gửi cookie session
            body: JSON.stringify({ voter_address: addressInput })
        });

        const data = await response.json();

        if (response.ok) {
            showToast("Thêm cử tri thành công! Giao dịch đang chạy ngầm.", "success");
            status.innerText = "✅ " + data.message;
            status.style.color = "var(--success-color)";
            document.getElementById("whitelistAddress").value = "";
            // Tải lại danh sách whitelist sau khi thêm
            loadWhitelistTable();
        } else {
            showToast(data.error || "Có lỗi xảy ra", "error");
            status.innerText = "❌ Lỗi: " + (data.error || "Không xác định");
            status.style.color = "var(--danger-color)";
        }
    } catch (err) {
        showToast("Lỗi kết nối máy chủ", "error");
        status.innerText = "❌ Lỗi mạng!";
        status.style.color = "var(--danger-color)";
    } finally {
        btn.disabled = false;
        btn.innerHTML = `➕ Thêm Cử Tri`;
    }
}

// Tải bảng danh sách whitelist của hòm phiếu này
async function loadWhitelistTable() {
    const tableContainer = document.getElementById("whitelistTableContainer");
    if (!tableContainer) return;

    try {
        const res = await fetch(`/api/elections/${ELECTION_ID}/whitelist/`);
        const data = await res.json();
        const list = data.whitelist || [];

        if (list.length === 0) {
            tableContainer.innerHTML = '<p style="color: var(--text-secondary); font-size: 0.9em; margin-top: 10px;">Chưa có cử tri nào được thêm.</p>';
            return;
        }

        const txStatusMap = {
            'pending':     ['⏳ Xếp hàng', 'tx-pending'],
            'broadcasted': ['📡 Chờ xác nhận', 'tx-broadcasted'],
            'confirmed':   ['✅ Xác nhận', 'tx-confirmed'],
            'failed':      ['❌ Thất bại', 'tx-failed'],
        };

        const rows = list.map(item => {
            const [txt, cls] = txStatusMap[item.tx_status] || ['—', ''];
            const shortAddr = item.voter_address.slice(0, 8) + '...' + item.voter_address.slice(-6);
            const txLink = item.tx_hash
                ? `<a href="https://sepolia.etherscan.io/tx/${item.tx_hash}" target="_blank" title="${item.tx_hash}">🔗 Xem</a>`
                : '—';
            return `<tr>
                <td title="${item.voter_address}">${shortAddr}</td>
                <td><span class="badge ${cls}">${txt}</span></td>
                <td>${txLink}</td>
            </tr>`;
        }).join('');

        tableContainer.innerHTML = `
            <table class="whitelist-table">
                <thead><tr><th>Địa chỉ ví</th><th>Trạng thái TX</th><th>Etherscan</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    } catch (e) {
        tableContainer.innerHTML = '<p style="color:var(--danger-color); font-size:0.9em;">Không tải được danh sách.</p>';
    }
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

        const receipt = await tx.wait(); // Chờ xác nhận
        const txHash = receipt.hash;

        showToast("🎉 Bầu chọn thành công! Cảm ơn bạn.", "success");
        userHasVoted = true;
        renderCandidateButtons(); // Khóa tất cả nút

        // Hiện TxHash + nút xác minh
        showVoteConfirmation(txHash);
    } catch (error) {
        console.error(error);

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

// Hiện hộp xác nhận sau khi vote thành công
function showVoteConfirmation(txHash) {
    const shortHash = txHash.slice(0, 12) + '...' + txHash.slice(-8);
    const confirmBox = document.getElementById("voteConfirmationBox");
    if (!confirmBox) return;

    confirmBox.innerHTML = `
        <div class="tx-hash-box">
            <span>🧾</span>
            <div style="flex:1;">
                <div style="font-size:0.75rem; color: var(--text-secondary); margin-bottom: 4px;">Mã giao dịch (TxHash) của bạn:</div>
                <span title="${txHash}">${shortHash}</span>
            </div>
            <a href="https://sepolia.etherscan.io/tx/${txHash}" target="_blank" class="btn" style="padding: 6px 12px; font-size: 0.8rem; background: #4f46e5;">🔗 Etherscan</a>
            <a href="/verify/?tx=${txHash}" target="_blank" class="btn" style="padding: 6px 12px; font-size: 0.8rem; background: #16a34a;">✅ Xác minh</a>
        </div>`;
    confirmBox.style.display = "block";
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

    // Hiện khung Whitelist Admin nếu là hòm phiếu Private
    const adminSection = document.getElementById("adminWhitelistSection");
    if (adminSection && electionData.election.is_private) {
        adminSection.style.display = "block";
        loadWhitelistTable(); // Tải danh sách whitelist ngay khi vào trang
    }

    renderChart();
    renderCandidateDOM(); // Vẽ khung HTML cho ứng viên
    renderCandidateButtons(); // Cập nhật trạng thái nút ban đầu
    renderVoterList(electionData.voters); // Hiện danh sách cử tri
}

// RENDER DANH SÁCH CỬ TRI
function renderVoterList(voters) {
    const container = document.getElementById('voterList');
    const countEl = document.getElementById('voterCount');
    if (!container) return;

    if (!voters || voters.length === 0) {
        container.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 20px 0;">Chưa có phiếu bầu nào.</p>';
        if (countEl) countEl.innerText = '0 cử tri';
        return;
    }

    if (countEl) countEl.innerText = `${voters.length} cử tri`;

    const rows = voters.map((v, i) => {
        const shortAddr = v.voter_address.slice(0, 8) + '...' + v.voter_address.slice(-6);
        const shortTx  = v.tx_hash.slice(0, 10) + '...';
        return `<tr style="animation: fadeIn 0.3s ease ${i * 0.04}s both;">
            <td style="font-weight:600; color: var(--text-secondary); padding: 10px 12px;">#${voters.length - i}</td>
            <td style="padding: 10px 12px;">
                <span title="${v.voter_address}" style="font-family:monospace; font-size:0.88rem;">${shortAddr}</span>
                <button onclick="navigator.clipboard.writeText('${v.voter_address}'); showToast('Copied!','success')" 
                    style="background:none; border:none; cursor:pointer; color:var(--text-secondary); padding:2px 6px; font-size:0.75rem;">⎘</button>
            </td>
            <td style="padding: 10px 12px; color: var(--text-secondary); font-size:0.85rem;">${v.voted_at}</td>
            <td style="padding: 10px 12px; font-size:0.82rem;">
                <a href="https://sepolia.etherscan.io/tx/${v.tx_hash}" target="_blank" 
                   title="${v.tx_hash}"
                   style="display:inline-flex; align-items:center; gap:4px; color: var(--accent-color);">
                    ${shortTx} 🔗
                </a>
            </td>
        </tr>`;
    }).join('');

    container.innerHTML = `
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr style="border-bottom: 2px solid var(--border-color);">
                    <th style="text-align:left; padding:8px 12px; color:var(--text-secondary); font-size:0.85rem; font-weight:600;">#</th>
                    <th style="text-align:left; padding:8px 12px; color:var(--text-secondary); font-size:0.85rem; font-weight:600;">Wallet</th>
                    <th style="text-align:left; padding:8px 12px; color:var(--text-secondary); font-size:0.85rem; font-weight:600;">Thời gian</th>
                    <th style="text-align:left; padding:8px 12px; color:var(--text-secondary); font-size:0.85rem; font-weight:600;">Giao dịch</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>`;
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
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
            }]
        },
        options: {
            plugins: {
                legend: { position: 'bottom', labels: { font: { family: 'Inter' } } }
            }
        }
    });
}

// 5. RENDER KHUNG DANH SÁCH ỨNG VIÊN (Chỉ chạy 1 lần)
function renderCandidateDOM() {
    const listDiv = document.getElementById("candidateList");
    listDiv.innerHTML = "";
    electionData.candidates.forEach(c => {
        const safeName = escapeHTML(c.name);
        const safeImg = escapeHTML(c.image_url);
        listDiv.innerHTML += `
            <div class="candidate-card">
                <img src="${safeImg}" alt="${safeName}"
                     onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22140%22 height=%22140%22 viewBox=%220 0 140 140%22%3E%3Crect width=%22140%22 height=%22140%22 fill=%22%23e2e8f0%22 rx=%2270%22/%3E%3Ccircle cx=%2270%22 cy=%2252%22 r=%2224%22 fill=%22%2394a3b8%22/%3E%3Cellipse cx=%2270%22 cy=%22105%22 rx=%2236%22 ry=%2222%22 fill=%22%2394a3b8%22/%3E%3C/svg%3E'"/>
                <h3>${safeName}</h3>
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

        let btnDisabled = false;
        const safeName = escapeHTML(c.name);
        let btnText = `🗳️ Bầu Cho ${safeName}`;

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
        container.innerHTML = `<button id="btnVote_${c.id}" onclick="castVote(${c.id})" class="btn" style="width:100%; transition: all 0.2s; ${style}" ${btnDisabled ? 'disabled' : ''}>${btnText}</button>`;
    });
}

// 7. WEBSOCKET REAL-TIME
function setupWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsProtocol}${window.location.host}/ws/election/${ELECTION_ID}/`;
    const socket = new WebSocket(wsUrl);

    socket.onmessage = async function(e) {
        const payload = JSON.parse(e.data);
        if (payload.type === 'NEW_VOTE') {
            const res = await fetch(`/api/elections/${ELECTION_ID}/`);
            const newData = await res.json();

            electionData.candidates = newData.candidates;
            electionData.election.total_votes = newData.election.total_votes;
            electionData.voters = newData.voters;

            // Cập nhật biểu đồ
            myChart.data.datasets[0].data = electionData.candidates.map(c => c.vote_count);
            myChart.update();

            // Cập nhật DOM số liệu mượt mà
            electionData.candidates.forEach(c => {
                const vc = document.getElementById(`voteCount_${c.id}`);
                const vf = document.getElementById(`voteFill_${c.id}`);
                const vp = document.getElementById(`votePercent_${c.id}`);
                if (vc) vc.innerText = `${c.vote_count} phiếu`;
                if (vf) vf.style.width = `${c.percentage}%`;
                if (vp) vp.innerText = `${c.percentage}%`;
            });

            // Cập nhật danh sách cử tri
            renderVoterList(electionData.voters);
        }
    };

    socket.onclose = function() {
        setTimeout(setupWebSocket, 3000); // Tự kết nối lại sau 3s
    };
}

// CHẠY KHI TẢI TRANG
window.onload = async () => {
    await fetchInitialData();
    setupWebSocket();

    // --- Lắng nghe khi user đổi ví hoặc đổi mạng trong MetaMask ---
    if (window.ethereum) {
        // Đổi ví: reset trạng thái, yêu cầu kết nối lại
        window.ethereum.on('accountsChanged', (accounts) => {
            signer = null;
            contract = null;
            userHasVoted = false;
            userIsWhitelisted = false;
            const walletEl = document.getElementById('walletAddress');
            if (walletEl) walletEl.innerText = '';
            renderCandidateButtons();
            if (accounts.length === 0) {
                showToast('Ví đã bị ngắt kết nối.', 'warning');
            } else {
                showToast('Bạn đã đổi ví. Vui lòng kết nối lại để cập nhật trạng thái.', 'warning');
            }
        });

        // Đổi mạng: cảnh báo nếu không phải Sepolia
        window.ethereum.on('chainChanged', (chainIdHex) => {
            const newChainId = parseInt(chainIdHex, 16);
            if (newChainId !== EXPECTED_CHAIN_ID) {
                showToast(`Sai mạng lưới! Vui lòng chuyển về Sepolia (Chain ID: ${EXPECTED_CHAIN_ID}).`, 'error');
                signer = null;
                contract = null;
                renderCandidateButtons();
            } else {
                showToast('Đã chuyển về Sepolia Testnet ✅', 'success');
            }
        });
    }
};

