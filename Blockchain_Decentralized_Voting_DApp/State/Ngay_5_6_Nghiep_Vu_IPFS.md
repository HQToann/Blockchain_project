# 🟢 NGÀY 5 & 6: IPFS PINATA VÀ CÁC API NGHIỆP VỤ

Tiếp tục hành trình của Kỹ sư Backend, hôm nay chúng ta sẽ xử lý việc upload ảnh phi tập trung và viết các API để cung cấp dữ liệu cho Frontend.

---

## BƯỚC 1: Cấu hình Pinata IPFS

Bản chất Blockchain không thể lưu trữ ảnh vì phí Gas sẽ cực kỳ đắt. Giải pháp là tải ảnh lên mạng lưới IPFS thông qua dịch vụ Pinata Cloud, sau đó chỉ lưu chuỗi mã hash (CID) vào Database.

1. Truy cập [Pinata.cloud](https://app.pinata.cloud/) tạo tài khoản miễn phí.
2. Vào mục **API Keys** → Bấm **New Key** → Đặt tên bất kỳ → Bấm **Generate API Key**.
3. Bạn sẽ thấy chuỗi **JWT** (bắt đầu bằng `ey...`). Hãy copy ngay vì nó chỉ hiện 1 lần!

> ⚠️ **Lưu ý:** Pinata đã **bỏ cách xác thực cũ** bằng `api_key` + `api_secret`. Hiện tại chỉ dùng **JWT Token**.

4. Tạo file `.env` ở thư mục gốc dự án và điền vào:

```env
PINATA_JWT=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## BƯỚC 2: Viết logic Upload Ảnh

Tạo file `election/services.py` để chứa các logic gọi ra bên ngoài (Service Layer).

```python
import os
import requests
from django.conf import settings

def upload_image_to_ipfs(file_obj):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    
    # Dùng JWT Token (cách xác thực mới của Pinata)
    headers = {
        'Authorization': os.getenv('PINATA_JWT')
    }
    
    files = {
        'file': file_obj
    }
    
    response = requests.post(url, files=files, headers=headers)
    
    if response.status_code == 200:
        # Trả về mã Hash CID của ảnh
        return response.json()['IpfsHash']
    else:
        raise Exception("IPFS Upload Failed: " + response.text)
```

Tiếp tục mở `election/views.py` thêm hàm nhận file từ Admin.

> 📌 **Lưu ý:** Đảm bảo phần đầu file `election/views.py` của bạn có đầy đủ các import sau (gộp tất cả import từ Ngày 3-4 và Ngày 5-6 lại):

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from eth_account.messages import encode_defunct
from web3 import Web3
from .models import Election, Candidate, VoteRecord
from .services import upload_image_to_ipfs
import secrets, json, os
```

Sau đó thêm hàm upload:

```python
from django.views.decorators.csrf import csrf_exempt
from .services import upload_image_to_ipfs

@csrf_exempt
def upload_candidate_image(request):
    # Nhớ kiểm tra bảo mật (chỉ Admin mới được upload)
    if not request.session.get('is_admin'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == 'POST' and request.FILES.get('image'):
        try:
            cid = upload_image_to_ipfs(request.FILES['image'])
            return JsonResponse({'success': True, 'cid': cid})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'No file'}, status=400)
```

---

## BƯỚC 3: Xây dựng các API Đọc Dữ Liệu (Read)

Đây là nơi Frontend gọi để lấy danh sách hiển thị ra biểu đồ.
Vào `election/views.py`, thêm các hàm sau:

```python
from .models import Election, Candidate, VoteRecord

def get_elections(request):
    # Lấy danh sách các cuộc bầu cử
    elections = Election.objects.all().values(
        'id', 'name', 'contract_addr', 'is_private', 'status'
    )
    return JsonResponse({'elections': list(elections)})

def get_election_detail(request, election_id):
    try:
        election = Election.objects.get(id=election_id)
        candidates = Candidate.objects.filter(election=election)
        
        # Đếm tổng số phiếu
        total_votes = sum(c.vote_count for c in candidates)
        
        candidates_data = []
        for c in candidates:
            # Tính % tự động
            pct = round((c.vote_count / total_votes * 100), 2) if total_votes > 0 else 0
            candidates_data.append({
                'id': c.candidate_id,
                'name': c.name,
                # Link xem ảnh trên gateway của pinata
                'image_url': f"https://gateway.pinata.cloud/ipfs/{c.image_cid}",
                'vote_count': c.vote_count,
                'percentage': pct
            })
            
        return JsonResponse({
            'election': {
                'id': election.id,
                'name': election.name,
                'contract_addr': election.contract_addr,
                'status': election.status,
                'total_votes': total_votes
            },
            'candidates': candidates_data
        })
    except Election.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
```

---

## BƯỚC 4: Kết nối URLs

Mở `core/urls.py` và **bỏ comment + bổ sung** các path sau (thêm vào `urlpatterns`, giữ nguyên 2 route `nonce`/`verify` cũ):

```python
    # --- Bổ sung 4 route mới này vào Ngày 5-6 (bỏ dấu # comment nếu đã có sẵn) ---
    path('api/upload/', views.upload_candidate_image),
    path('api/elections/', views.get_elections),
    path('api/elections/<int:election_id>/', views.get_election_detail),
    path('api/elections/<int:election_id>/candidates/', views.create_candidate),
```

> [!NOTE]
> Route `dashboard/` đã được thêm từ Ngày 3-4 rồi — **không cần thêm lại!**

---

## BƯỚC 5 (CRIỌC KỲ QUAN TRỌNG): API Tạo Ứng Viên Trong Database

> [!CAUTION]
> **Lỗi #2 và #3 cần sửa:** Hàm `addCandidate()` trên Smart Contract không phát Event nào, nên Indexer không thể tự tạo bản ghi Candidate trong DB. Nếu DB không có Candidate, Indexer sẽ bỏ qua phiếu bầu và API `/results/` luôn trả về `candidates: []`.
>
> **Quy trình bắt buộc:** Admin phải tạo Candidate **trong Django DB trước**, sau đó mới gọi `addCandidate()` trên Smart Contract.

Thêm API này vào `election/views.py`:

```python
@csrf_exempt
def create_candidate(request, election_id):
    """POST /api/elections/<id>/candidates/
    Body: { "name": "Nguyen Van A", "candidate_id": 0, "image_cid": "Qm..." }
    candidate_id phải trùng với index trong Smart Contract (bắt đầu từ 0).
    """
    if not request.session.get('is_admin'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        data = json.loads(request.body)
        election = Election.objects.get(id=election_id)

        candidate = Candidate.objects.create(
            election=election,
            candidate_id=data['candidate_id'],  # ID phải trùng với Smart Contract
            name=data['name'],
            image_cid=data.get('image_cid', ''),
        )
        return JsonResponse({'success': True, 'id': candidate.id, 'name': candidate.name})
    except Election.DoesNotExist:
        return JsonResponse({'error': 'Election not found'}, status=404)
    except KeyError as e:
        return JsonResponse({'error': f'Thiếu trường: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

> [!NOTE]
> Route `api/elections/<int:election_id>/candidates/` đã được thêm vào `core/urls.py` ở BƯỚC 4 rồi — **không cần dán thêm!**

**Quy trình Admin sử dụng:**
```
1. Upload ảnh lên IPFS -> nhận CID
2. Gọi POST /api/elections/<id>/candidates/ (với candidate_id=0, name=..., image_cid=...)
3. Gọi addCandidate() trên Smart Contract qua MetaMask (cùng thứ tự với bước trên)
4. Lặp lại cho từng ứng viên (candidate_id tăng dần: 0, 1, 2...)
```

---
🎉 **XONG NGÀY 5 & 6!**
Đến lúc này, Backend API đã hoàn thiện phần lớn chức năng lõi.
