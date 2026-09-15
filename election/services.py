import os
import requests
from django.conf import settings
from .models import SystemLog

def upload_image_to_ipfs(file_obj):
    SystemLog.objects.create(level='INFO', module='IPFS', message=f'Đang tải file {file_obj.name} lên Pinata IPFS...')
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    
    # Dùng JWT Token (cách xác thực mới của Pinata)
    headers = {
        'Authorization': f"Bearer {os.getenv('PINATA_JWT')}"
    }
    
    files = {
        'file': file_obj
    }
    
    response = requests.post(url, files=files, headers=headers)
    
    if response.status_code == 200:
        # Trả về mã Hash CID của ảnh
        cid = response.json()['IpfsHash']
        SystemLog.objects.create(level='SUCCESS', module='IPFS', message=f'Tải file thành công! CID: {cid}')
        return cid
    else:
        SystemLog.objects.create(level='ERROR', module='IPFS', message=f'Lỗi tải file lên Pinata: {response.text}')
        raise Exception("IPFS Upload Failed: " + response.text)
