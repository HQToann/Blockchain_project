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

# 4. Cấu hình Channel Layer: Sử dụng Redis (BẮT BUỘC ĐỂ HOẠT ĐỘNG XUYÊN PROCESS)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
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

## BƯỚC 4: Kết nối Indexer với Channels

Mở lại file `indexer/indexer.py` (của Ngày 7), ở chỗ **cộng phiếu thành công**, ta sẽ "Hét" lên cho Channels biết để nó phát xuống Frontend:

```python
import os
import sys
import django
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# ... [Các code setup Django như cũ] ...

# Ở chỗ sau khi update vote_count thành công:
channel_layer = get_channel_layer()
async_to_sync(channel_layer.group_send)(
    f'election_{election.id}',
    {
        'type': 'send_vote_update',
        'message': {
            'candidate_id': candidate_id,
            'tx_hash': tx_hash
        }
    }
)
```

---
🎉 **XONG NGÀY 8!**
Hạ tầng truyền tin tốc độ cao thông qua Redis đã dựng xong. 2 tiến trình độc lập (Django & Indexer) giờ đây đã có thể nói chuyện mượt mà. Ở Ngày 9, Frontend chỉ việc kết nối WebSocket và biểu đồ sẽ tự nhảy múa.
