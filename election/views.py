import os
import secrets
import json
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from eth_account.messages import encode_defunct
from web3 import Web3

from .models import Election, Candidate, VoteRecord
from .services import upload_image_to_ipfs

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

# 3. API Upload ảnh lên Pinata
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

# Read API
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