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
