# 🟢 NGÀY 3 & 4: SETUP DJANGO, MODELS VÀ WEB3 AUTHENTICATION

Chào mừng **Kỹ sư Backend** bước vào nhiệm vụ của mình. Bạn sẽ gánh vác toàn bộ hạ tầng dữ liệu và bảo mật của dự án.

> 🛠️ **Yêu cầu:** Đã cài sẵn Python (>= 3.11) và PostgreSQL trên máy tính.

---

## BƯỚC 1: Khởi tạo dự án và Môi trường ảo

Mở Terminal (Command Prompt hoặc PowerShell) tại thư mục gốc của dự án (`Blockchain_Project`), chạy các lệnh sau:

```bash
# 1. Cài Pipenv (công cụ quản lý môi trường ảo)
pip install pipenv

# 2. Cài đặt TẤT CẢ thư viện cần thiết cho cả 10 ngày (cài 1 lần duy nhất)
pipenv install django psycopg2-binary django-cors-headers web3 eth-account python-dotenv channels channels-redis daphne

# 3. Kích hoạt môi trường ảo (Sau này mỗi lần code đều phải gõ lệnh này trước)
pipenv shell

# 4. Khởi tạo Project Django tại thư mục gốc (dấu chấm ở cuối rất quan trọng!)
django-admin startproject core .

# 5. Tạo App nghiệp vụ
python manage.py startapp election
```

# 6. Tạo file .env
Tạo file `.env` ngang hàng với file `manage.py` và điền biến bảo mật (chú ý địa chỉ ví viết thường, không khoảng trắng):
```env
# === WEB3 AUTH ===
# CHÚ Ý: Địa chỉ ví này PHẢI GIỐNG 100% với ví Kỹ sư Blockchain đã dùng để deploy Factory ở Ngày 1-2!
ADMIN_WALLET_ADDRESS=0xDiaChiViMetaMask_CuaAdmin_VietThuongKhongDauKhongCoKhoangTrang
```

---

## BƯỚC 2: Cấu hình `settings.py`

Mở file `core/settings.py` và chỉnh sửa các mục sau:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() # Đọc file .env

BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'election',    # Thêm app của mình
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware', # Tạm Tắt CSRF để làm API cho dễ
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Cấu hình Database PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'voting_db',
        'USER': 'postgres',
        'PASSWORD': '123', # Đổi thành pass của bạn
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Cấu hình Session
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_AGE = 86400  # Session đăng nhập sống 1 ngày (tránh bị out giữa chừng khi Demo)

> [!WARNING]
> **Lưu ý Bảo mật (Dành cho Q&A):** Việc dùng Cookie Session cho API và tắt CSRF (`@csrf_exempt`) là để làm Demo/Đồ án nhanh. Trong thực tế, hệ thống nên chuyển sang dùng **JWT (gửi qua Header Authorization)** để miễn nhiễm hoàn toàn với CSRF!

# Cấu hình đường dẫn Templates và Static files
import os
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Chỉ đường tới thư mục templates/
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # Chỉ đường tới thư mục static/
STATIC_URL = '/static/'
```
*Lưu ý: Bạn nhớ mở pgAdmin lên và tạo một Database trống tên là `voting_db` trước nhé.*

---

## BƯỚC 3: Xây dựng Models (Cơ sở dữ liệu)

Mở `election/models.py`, viết cấu trúc các bảng:

```python
from django.db import models

class Election(models.Model):
    contract_addr  = models.CharField(max_length=42, unique=True) # Địa chỉ sinh ra từ Factory
    name           = models.CharField(max_length=255)
    is_private     = models.BooleanField(default=False)
    status         = models.CharField(max_length=20, default='pending') # pending, active, closed
    created_at     = models.DateTimeField(auto_now_add=True)

class Candidate(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    candidate_id   = models.PositiveIntegerField() # ID tương ứng trên Smart Contract
    name           = models.CharField(max_length=255)
    image_cid      = models.CharField(max_length=100) # Mã IPFS Pinata
    vote_count     = models.PositiveIntegerField(default=0)

class VoteRecord(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE)
    voter_address  = models.CharField(max_length=42)
    # KHÔNG LƯU candidate_id để bảo vệ quyền riêng tư
    tx_hash        = models.CharField(max_length=66, unique=True)
    block_number   = models.PositiveBigIntegerField()
    voted_at       = models.DateTimeField(auto_now_add=True)

class WhitelistVoter(models.Model):
    election       = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='whitelist')
    voter_address  = models.CharField(max_length=42)
    
    class Meta:
        unique_together = ('election', 'voter_address')
```

Sau khi lưu file, chạy lệnh để tạo bảng trong DB:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## BƯỚC 4: Code Web3 Authentication (SIWE)

Chúng ta sẽ làm tính năng đăng nhập mà KHÔNG CẦN mật khẩu. Người dùng ký bằng MetaMask, Backend sẽ kiểm tra chữ ký.

Mở (hoặc tạo) file `election/views.py`:

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from eth_account.messages import encode_defunct
from web3 import Web3
import os
import secrets
import json
import time

# 1. API Cấp mã ngẫu nhiên (Nonce)
@csrf_exempt
def get_nonce(request):
    nonce = secrets.token_hex(16)
    # Lưu nonce và thời gian tạo vào session (chỉ cho phép ký trong 5 phút)
    request.session['auth_nonce'] = nonce
    request.session['nonce_time'] = time.time()
    return JsonResponse({'nonce': nonce})

# 2. API Kiểm tra chữ ký (Verify)
@csrf_exempt
def verify_signature(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            signature = data.get('signature')
            public_address = data.get('address')
            
            saved_nonce = request.session.get('auth_nonce')
            saved_time = request.session.get('nonce_time', 0)
            
            if not saved_nonce:
                return JsonResponse({'error': 'Nonce expired'}, status=400)
            
            if time.time() - saved_time > 300: # 5 phút
                return JsonResponse({'error': 'Nonce timeout (5 minutes)'}, status=400)
            
            # Chuẩn hóa tin nhắn cần kiểm tra
            message = encode_defunct(text=saved_nonce)
            w3 = Web3()
            
            # Khôi phục địa chỉ ví từ chữ ký
            recovered_address = w3.eth.account.recover_message(message, signature=signature)
            
            if recovered_address.lower() == public_address.lower():
                # CHỮ KÝ ĐÚNG -> Dù là Admin hay không thì cũng xóa nonce để tránh dùng lại
                del request.session['auth_nonce']
                
                # KIỂM TRA QUYỀN ADMIN (Chống ai cũng login được)
                admin_wallet = os.getenv("ADMIN_WALLET_ADDRESS", "").lower()
                if recovered_address.lower() != admin_wallet:
                    return JsonResponse({'error': 'Ví này không phải là Admin hệ thống!'}, status=403)

                # Chữ ký hợp lệ & đúng Admin! Đánh dấu đăng nhập thành công
                request.session['is_admin'] = True
                request.session['wallet'] = recovered_address
                
                return JsonResponse({'success': True, 'wallet': recovered_address})
            else:
                return JsonResponse({'error': 'Invalid signature'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Only POST allowed'}, status=405)
```

Mở `core/urls.py` để gắn URL cho API:

> [!CAUTION]
> **Dán đúng từ́ng phần, không dán thừa!** Tại thời điểm này `views.py` chỉ có `get_nonce` và `verify_signature`. Nếu dán thêm các route của Ngày 5-6 (`get_elections`, `get_election_detail`, `upload_candidate_image`) vào đây, Django sẽ báo `AttributeError` và **không khởi động được** — không test được gì cả!

```python
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

    # API Auth (Web3 SIWE) — Đã viết xong ở Ngày 3-4
    path('api/auth/nonce/', views.get_nonce),
    path('api/auth/verify/', views.verify_signature),

    # --- Các route sau sẽ bổ sung ở Ngày 5-6 khi có hàm tương ứng ---
    # path('api/upload/', views.upload_candidate_image),
    # path('api/elections/', views.get_elections),
    # path('api/elections/<int:election_id>/', views.get_election_detail),
    # path('api/elections/<int:election_id>/candidates/', views.create_candidate),
]
```

---
🎉 **HOÀN THÀNH NGÀY 3 & 4!** 
Để chạy thử Server, gõ lệnh: `python manage.py runserver`.
Mở trình duyệt truy cập `http://127.0.0.1:8000/api/auth/nonce/`, nếu bạn thấy một chuỗi ngẫu nhiên sinh ra tức là API đã sống!
