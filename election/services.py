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
