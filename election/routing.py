from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Đường dẫn mà Frontend sẽ kết nối tới (ws://localhost:8000/ws/election/<id>/)
    re_path(r'ws/election/(?P<election_id>\w+)/$', consumers.ElectionConsumer.as_asgi()),
]
