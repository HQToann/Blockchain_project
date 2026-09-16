import os
import secrets
import json
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib.auth.models import User
from eth_account.messages import encode_defunct
from web3 import Web3

from django.shortcuts import render
from .models import Election, Candidate, VoteRecord, SystemLog
from .services import upload_image_to_ipfs

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# -- LOGGING SYSTEM --
def system_logs(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    return render(request, 'logs.html')

def get_latest_logs(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    logs = SystemLog.objects.all()[:50] # Lấy 50 log mới nhất
    logs_data = []
    for log in logs:
        logs_data.append({
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': log.level,
            'module': log.module,
            'message': log.message
        })
    return JsonResponse({'logs': logs_data})

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
                admin_wallet = os.getenv("ADMIN_WALLET_ADDRESS", "").strip().lower()
                if recovered_address.lower() != admin_wallet:
                    return JsonResponse({'error': 'Ví này không phải là Admin hệ thống!'}, status=403)

                # Tích hợp vào hệ thống Authentication của Django Admin
                user, created = User.objects.get_or_create(username=admin_wallet)
                if created:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                
                # Hàm login của Django (tạo Cookie session cho Admin)
                login(request, user)
                
                request.session['is_admin'] = True
                request.session['wallet'] = recovered_address
                
                return JsonResponse({'success': True, 'wallet': recovered_address, 'redirect': '/admin/'})
            else:
                return JsonResponse({'error': 'Invalid signature'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Only POST allowed'}, status=405)

from django.db.models import Sum

from web3 import Web3
import os
from .models import IndexerState

def get_elections(request):
    # Lấy danh sách các cuộc bầu cử kèm tổng số phiếu
    elections = []
    for e in Election.objects.all().order_by('-id'):
        total = Candidate.objects.filter(election=e).aggregate(t=Sum('vote_count'))['t'] or 0
        elections.append({
            'id': e.id,
            'name': e.name,
            'contract_addr': e.contract_addr,
            'is_private': e.is_private,
            'status': e.status,
            'total_votes': total
        })
        
    is_lagging = False
    try:
        w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
        current_block = w3.eth.block_number
        state = IndexerState.objects.filter(key='main').first()
        if state and (current_block - state.last_block > 5):
            is_lagging = True
    except Exception:
        is_lagging = True
        
    return JsonResponse({'elections': elections, 'is_lagging': is_lagging})

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

from web3.exceptions import TransactionNotFound

def verify_vote_api(request):
    tx_hash = request.GET.get('tx')
    if not tx_hash:
        return JsonResponse({'error': 'Vui lòng cung cấp mã giao dịch (tx_hash)'}, status=400)
    
    # 1. Kiểm tra trong DB (Indexer đã quét)
    from .models import VoteRecord
    record = VoteRecord.objects.filter(tx_hash=tx_hash).first()
    if record:
        return JsonResponse({
            'status': 'confirmed',
            'message': 'Giao dịch đã được xác nhận và ghi nhận thành công!',
            'data': {
                'election': record.election.name,
                'voter_address': record.voter_address,
                'block_number': record.block_number,
                'time': record.voted_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    # 2. Nếu chưa có trong DB, query trực tiếp lên Web3 xem nó đang pending hay reverted
    try:
        w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt.status == 1:
            return JsonResponse({'status': 'indexing', 'message': 'Giao dịch đã thành công trên chuỗi, hệ thống đang đồng bộ (vui lòng đợi vài giây).'})
        else:
            return JsonResponse({'status': 'failed', 'message': 'Giao dịch đã thất bại (Reverted) trên chuỗi.'})
    except TransactionNotFound:
        # Có thể tx đang Pending trong Mempool
        try:
            tx = w3.eth.get_transaction(tx_hash)
            return JsonResponse({'status': 'pending', 'message': 'Giao dịch đang chờ thợ mỏ xác nhận (Pending).'})
        except TransactionNotFound:
            return JsonResponse({'status': 'not_found', 'message': 'Không tìm thấy giao dịch này trên mạng lưới.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from .models import WhitelistVoter
import django_rq
from election.tasks import add_whitelist_task

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def add_whitelist_api(request, election_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            voter_address = data.get('voter_address')
            if not voter_address:
                return JsonResponse({'error': 'Missing voter_address'}, status=400)
                
            election = Election.objects.get(id=election_id)
            
            # Check if exists
            if WhitelistVoter.objects.filter(election=election, voter_address=voter_address).exists():
                return JsonResponse({'error': 'Địa chỉ này đã có trong whitelist!'}, status=400)
                
            wl = WhitelistVoter.objects.create(
                election=election,
                voter_address=voter_address,
                tx_status='pending'
            )
            
            django_rq.enqueue(add_whitelist_task, wl.id)
            return JsonResponse({'success': True, 'message': 'Đã gửi lệnh thêm whitelist vào hàng đợi ngầm.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST only'}, status=405)

@csrf_exempt
def internal_notify_vote(request):
    if request.headers.get('X-Internal-Secret') != os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default'):
        return JsonResponse({'error': 'Unauthorized access'}, status=403)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            election_id = data.get('election_id')
            candidate_id = data.get('candidate_id')
            tx_hash = data.get('tx_hash')
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'election_{election_id}',
                {
                    'type': 'send_vote_update',
                    'message': {
                        'candidate_id': candidate_id,
                        'tx_hash': tx_hash
                    }
                }
            )
            
            # Broadcast to the general group (for index.html)
            async_to_sync(channel_layer.group_send)(
                'election_all',
                {
                    'type': 'send_vote_update',
                    'message': {
                        'election_id': election_id,
                        'candidate_id': candidate_id,
                        'tx_hash': tx_hash
                    }
                }
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'POST only'}, status=405)