# 🟢 NGÀY 8: ĐẨY DỮ LIỆU REAL-TIME BẰNG WEBSOCKETS (DJANGO CHANNELS)

Hôm nay là ngày tạo ra phép màu cho ứng dụng! Thay vì bắt người dùng tải lại trang, Backend sẽ chủ động "Báo tin" cho trình duyệt.

> [!IMPORTANT]
> **Redis Server Bắt Buộc:** Tiến trình Django (Daphne) và tiến trình Indexer chạy tách biệt hoàn toàn. Để chúng giao tiếp được với nhau, bắt buộc phải dùng **Redis**. Nếu dùng `InMemoryChannelLayer`, WebSocket sẽ "câm lặng vĩnh viễn" do khác process.
> 
> **Cách chạy Redis Server (Chọn 1 trong 2):**
> 1. Dùng Docker (Khuyên dùng): Mở Terminal gõ `docker run -p 6379:6379 -d redis`
> 2. Dùng Windows (WSL): Cài đặt `sudo apt install redis-server` và chạy `sudo service redis-server start`
> 
> Đảm bảo Redis đang chạy ở port 6379 trước khi đi tiếp!

---

## BƯỚC 1: Cấu hình ASGI thay cho WSGI

Mở `core/settings.py` và sửa/thêm các dòng sau:

```python
# 1. Bổ sung 'channels' vào INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',   # ← THÊM DÒNG NÀY
    'election',
]

# 2. Bỏ WSGI cũ
# WSGI_APPLICATION = 'core.wsgi.application'

# 3. Chuyển sang ASGI
ASGI_APPLICATION = 'core.asgi.application'

# 4. Cấu hình Channel Layer: Tự động dùng Redis nếu có REDIS_URL (Trên Render)
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }
```

Mở `core/asgi.py`, sửa toàn bộ thành:

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import election.routing # Lát nữa ta sẽ tạo file này

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            election.routing.websocket_urlpatterns
        )
    ),
})
```

---

## BƯỚC 2: Viết Consumer (Nơi xử lý WebSockets)

Tạo file mới `election/consumers.py`:

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ElectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Lấy ID cuộc bầu cử từ URL
        self.election_id = self.scope['url_route']['kwargs']['election_id']
        self.room_group_name = f'election_{self.election_id}'

        # Đăng ký vào group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Rời group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Hàm này được gọi khi Indexer đẩy dữ liệu vào group
    async def send_vote_update(self, event):
        message = event['message']

        # Gửi dữ liệu xuống Frontend (Trình duyệt)
        await self.send(text_data=json.dumps({
            'type': 'NEW_VOTE',
            'data': message
        }))
```

---

## BƯỚC 3: Cấu hình Routing cho WebSockets

Tạo file mới `election/routing.py`:

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Đường dẫn mà Frontend sẽ kết nối tới (ws://localhost:8000/ws/election/<id>/)
    re_path(r'ws/election/(?P<election_id>\w+)/$', consumers.ElectionConsumer.as_asgi()),
]
```

---

Mở file `election/views.py` và bổ sung API Webhook nội bộ để nhận tin từ Indexer, sau đó phát xuống Frontend:

```python
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@csrf_exempt
def internal_notify_vote(request):
    """
    Webhook nội bộ để Indexer gọi vào mỗi khi có vote mới.
    Giải quyết triệt để lỗi "Timeout reading from Redis" và lỗi khác process trên Render.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            election_id = data.get("election_id")
            if not election_id:
                return JsonResponse({"status": "error", "message": "Missing election_id"}, status=400)
            
            # Khởi tạo lại Redis pool an toàn trong luồng HTTP của ASGI
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"election_{election_id}",
                {
                    "type": "send_vote_update",
                    "message": "Update"
                }
            )
            
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)
```

*(Lưu ý: Indexer ở Ngày 7 sẽ gọi HTTP POST vào endpoint này thay vì tự gọi `channel_layer.group_send`)*

---
🎉 **XONG NGÀY 8!**
Hạ tầng truyền tin tốc độ cao thông qua Redis đã dựng xong. 2 tiến trình độc lập (Django & Indexer) giờ đây đã có thể nói chuyện mượt mà. Ở Ngày 9, Frontend chỉ việc kết nối WebSocket và biểu đồ sẽ tự nhảy múa.
