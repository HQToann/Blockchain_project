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
