import os
import glob
import json
from django.conf import settings

def get_factory_address():
    # 1. Ưu tiên biến môi trường (Ví dụ cấu hình trên Render)
    env_addr = os.getenv("FACTORY_ADDRESS")
    if env_addr: 
        return env_addr

    # 2. Đọc từ file của Hardhat Ignition (khi chạy local/dev)
    try:
        # settings.BASE_DIR trỏ tới gốc dự án (Blockchain_Project)
        search_path = os.path.join(settings.BASE_DIR, "ignition", "deployments", "chain-*", "deployed_addresses.json")
        files = glob.glob(search_path)
        if files:
            # Sắp xếp file theo thời gian sửa đổi (lấy file mới nhất)
            latest_file = max(files, key=os.path.getmtime)
            with open(latest_file, "r") as f:
                data = json.load(f)
                if data:
                    # Lấy địa chỉ đầu tiên (thường là {"VotingModule#ElectionFactory": "0x..."})
                    return list(data.values())[0]
    except Exception as e:
        print(f"Warning: Không thể đọc file deployed_addresses.json: {e}")
        
    # 3. Giá trị hardcode dự phòng cuối cùng
    return "0x44F8Db431EA5049D60547777Af54a0D7E46D12DE"
