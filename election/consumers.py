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