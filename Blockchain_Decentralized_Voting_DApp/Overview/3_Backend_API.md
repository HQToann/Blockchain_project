# 3. BACKEND API: DJANGO THUẦN (JsonResponse)

---

## 3.1. Tổng Quan

Backend Django đóng vai trò là **bảng thông báo nhanh (Bulletin Board)** của hệ thống. Toàn bộ API được viết bằng **Django thuần**, sử dụng `JsonResponse` và `View` cơ bản — không phụ thuộc thêm bất kỳ thư viện ngoài nào.

Django **không tham gia** vào luồng bỏ phiếu (phiếu được gửi thẳng lên Blockchain), nhưng phụ trách:
- Cung cấp dữ liệu Off-chain (tên bầu cử, thông tin ứng viên) cho Frontend.
- Lưu trữ số phiếu đã được Indexer đồng bộ về từ Blockchain.
- Cung cấp trang quản trị Admin để tạo cuộc bầu cử.

---

## 3.2. Thiết Kế Cơ Sở Dữ Liệu (Models)

### Model `Election` (Cuộc bầu cử)
```python
class Election(models.Model):
    contract_addr  = models.CharField(max_length=42, unique=True)
    name           = models.CharField(max_length=255)
    is_private     = models.BooleanField(default=False)
    status         = models.CharField(max_length=20, default='pending') # pending, active, closed
    created_at     = models.DateTimeField(auto_now_add=True)
```

### Model `Candidate` (Ứng viên)
```python
class Candidate(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    candidate_id   = models.PositiveIntegerField()
    name           = models.CharField(max_length=255)
    image_cid      = models.CharField(max_length=100)
    vote_count     = models.PositiveIntegerField(default=0)
```

### Model `VoteRecord` (Lịch sử phiếu — Indexer ghi)
```python
class VoteRecord(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE)
    voter_address  = models.CharField(max_length=42)
    # LƯU Ý: Không lưu candidate_id ở đây để bảo vệ quyền riêng tư tuyệt đối!
    tx_hash        = models.CharField(max_length=66, unique=True)
    block_number   = models.PositiveBigIntegerField()
    voted_at       = models.DateTimeField(auto_now_add=True)  # auto_now_add để khỏi cần truyền thủ công
```

### Model `WhitelistVoter` (Private Poll)
```python
class WhitelistVoter(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='whitelist')
    voter_address  = models.CharField(max_length=42)
    added_at       = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('election', 'voter_address')
```

> [!CAUTION]
> **Rủi ro đếm phiếu trùng & Database Race Condition (Indexer):**
> 1. Indexer phải gọi `w3.eth.get_transaction(tx_hash)` để lấy `tx.from` (do Event không phát ra ví). Điều này tốn thêm 1 request RPC, cần kiểm soát rate-limit của Alchemy bằng `time.sleep()`.
> 2. Việc ghi `VoteRecord` và cập nhật `vote_count` của `Candidate` bắt buộc phải được bọc trong **`transaction.atomic()`** của Django. Nếu không, khi Indexer crash giữa chừng và restart, `VoteRecord` bị lỗi duplicate key, nhưng `vote_count` vẫn bị cộng dồn 2 lần (double-count).

---

## 3.3. Bảng API Endpoints Đầy Đủ

### Public APIs (Không cần xác thực)

| Method | Endpoint | Mô tả |
|:---|:---|:---|
| `GET` | `/api/elections/` | Lấy danh sách toàn bộ cuộc bầu cử (kèm địa chỉ contract) |
| `GET` | `/api/elections/<id>/` | Chi tiết 1 cuộc bầu cử |
| `GET` | `/api/elections/<id>/candidates/` | Danh sách ứng viên kèm số phiếu |
| `GET` | `/api/elections/<id>/results/` | Kết quả: số phiếu, tỉ lệ %, người dẫn đầu |
| `GET` | `/api/elections/<id>/votes/` | Lịch sử phiếu bầu |

### Web3 Auth APIs (Đăng nhập Admin không mật khẩu)

| Method | Endpoint | Mô tả |
|:---|:---|:---|
| `GET` | `/api/auth/nonce/` | Lấy mã `nonce` ngẫu nhiên để ví MetaMask ký |
| `POST` | `/api/auth/verify/` | Gửi chữ ký (signature) lên để Django xác thực, trả về Token/Session |

### Admin APIs (Yêu cầu Session/Token hợp lệ)

| Method | Endpoint | Mô tả |
|:---|:---|:---|
| *(Tự động qua Indexer)* | N/A | **Lưu ý:** Election trong Database được Indexer tự động tạo khi bắt được event `ElectionCreated` từ Blockchain. Backend không có endpoint POST ghi trực tiếp. |
| `PATCH` | `/api/elections/<id>/` | Cập nhật thông tin |
| `POST` | `/api/elections/<id>/candidates/` | ⭐ **Tạo ứng viên trong Django DB** (phải thực hiện TRƯỚC khi gọi `addCandidate()` trên Smart Contract!) |
| `POST` | `/api/upload/` | Tải ảnh lên IPFS, nhận về CID |

### Internal Webhook APIs (Giao tiếp Đa Luồng)

| Method | Endpoint | Mô tả |
|:---|:---|:---|
| `POST` | `/api/internal/notify_vote/` | API bảo mật chỉ dành cho `indexer.py` gọi sang Django Server để kích hoạt đẩy luồng WebSocket xuống Frontend mỗi khi có giao dịch mới (khắc phục lỗi Cross-Process trên Render). |

---

## 3.4. Mô Hình Kiến Trúc "Service Layer"

Để tránh tình trạng "Fat Views" (nhồi nhét quá nhiều code vào `views.py`), dự án áp dụng chuẩn **Service Layer Pattern**:
- `views.py`: **Chỉ** làm nhiệm vụ nhận Request, phân tích tham số, gọi Selector/Service và trả về `JsonResponse`.
- `selectors.py`: Chứa các hàm đọc dữ liệu từ Database (GET).
- `services.py`: Chứa các hàm ghi/sửa dữ liệu hoặc xử lý nghiệp vụ bên ngoài (POST/IPFS).

### 1. `selectors.py` (Chuyên Đọc Dữ Liệu)
```python
from .models import Election, Candidate

def get_election_results_selector(election_id: int) -> dict:
    election = Election.objects.get(pk=election_id)
    candidates = Candidate.objects.filter(election=election)
    total_votes = sum(c.vote_count for c in candidates)

    results = []
    winner = None
    max_votes = -1

    for c in candidates:
        pct = round((c.vote_count / total_votes * 100), 2) if total_votes > 0 else 0
        results.append({
            'id': c.candidate_id,
            'name': c.name,
            'image_url': f"https://gateway.pinata.cloud/ipfs/{c.image_cid}",
            'vote_count': c.vote_count,
            'percentage': pct,
        })
        if c.vote_count > max_votes:
            max_votes = c.vote_count
            winner = {'id': c.candidate_id, 'name': c.name}

    return {
        'election_id': election.id,
        'election_name': election.name,
        'status': election.status,
        'total_votes': total_votes,
        'candidates': results,
        'winner': winner,
    }
```

### 2. `services.py` (Chuyên Xử Lý Nghiệp Vụ)
```python
import requests as http_requests
import os

def upload_image_to_ipfs_service(image_file) -> dict:
    if not image_file:
        raise ValueError("Không có file được tải lên")

    # Dùng JWT Token (cách xác thực mới của Pinata - không dùng api_key cũ)
    headers = {
        "Authorization": os.getenv("PINATA_JWT"),
    }
    response = http_requests.post(
        "https://api.pinata.cloud/pinning/pinFileToIPFS",
        files={"file": image_file},
        headers=headers
    )
    
    if response.status_code != 200:
        raise Exception("Lỗi khi tải ảnh lên Pinata")
        
    cid = response.json()["IpfsHash"]
    return {
        "cid": cid,
        "url": f"https://gateway.pinata.cloud/ipfs/{cid}"
    }
```

### 3. `views.py` (Mỏng Nhẹ & Gọn Gàng)
```python
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Election
from . import selectors
from . import services

def election_results_view(request, pk):
    """GET /api/elections/<id>/results/"""
    try:
        data = selectors.get_election_results_selector(election_id=pk)
        return JsonResponse(data)
    except Election.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy'}, status=404)

@staff_member_required
def ipfs_upload_view(request):
    """POST /api/ipfs/upload/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        file = request.FILES.get('image')
        result = services.upload_image_to_ipfs_service(file)
        return JsonResponse(result)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

---

## 3.5. Định Tuyến URL (`core/urls.py`)

> [!NOTE]
> Toàn bộ route được đăng ký **thẳng trong `core/urls.py`** — không dùng `election/urls.py` riêng + `include()`. Đây là cách đơn giản hơn, đủ dùng cho quy mô đồ án.

```python
# core/urls.py
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from election import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Trang HTML
    path('', TemplateView.as_view(template_name='index.html')),
    path('election/<int:election_id>/', TemplateView.as_view(template_name='detail.html')),
    path('dashboard/', TemplateView.as_view(template_name='admin_dashboard.html')),

    # Auth
    path('api/auth/nonce/', views.get_nonce),
    path('api/auth/verify/', views.verify_signature),

    # API dữ liệu (thêm vào sau khi viết xong views tương ứng ở Ngày 5-6)
    path('api/upload/', views.upload_candidate_image),          # endpoint thực tế là /api/upload/
    path('api/elections/', views.get_elections),
    path('api/elections/<int:election_id>/', views.get_election_detail),
    path('api/elections/<int:election_id>/candidates/', views.create_candidate),

    # Webhook nội bộ
    path('api/internal/notify_vote/', views.internal_notify_vote),
]
```

---

## 3.6. Cấu Trúc Thư Mục Backend

```text
decentralized_voting/
├── core/               # Project Configuration
│   ├── settings.py     # Cấu hình DB, ASGI, WebSockets
│   ├── urls.py         # Router chính (tất cả route viết ở đây)
│   └── asgi.py         # Chạy Django Channels (WebSockets)
│
├── election/
│   ├── models.py       # Election, Candidate, VoteRecord, WhitelistVoter
│   ├── services.py     # Logic ghi DB (upload IPFS)
│   ├── views.py        # Tất cả API endpoints
│   └── consumers.py    # Nhận/Phát WebSocket Event tới Frontend
│
└── indexer/
    ├── indexer.py      # Lắng nghe Factory (ElectionCreated) & VoteCast
    └── last_block.txt  # Checkpoint số block đã xử lý
```

> [!IMPORTANT]
> **Không cài `djangorestframework`**. Toàn bộ API trả về `JsonResponse` từ `django.http`. Bảo vệ Admin API bằng kiểm tra `request.session.get('is_admin')` (SIWE session — không dùng `@staff_member_required` hay `request.user.is_staff`).
