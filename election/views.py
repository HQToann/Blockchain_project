import os
import secrets
import json
import time
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.contrib.auth.models import User
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.exceptions import TransactionNotFound
from datetime import timezone, timedelta
from django.core.cache import cache

from django.shortcuts import render
from django.db.models import Sum
from .models import Election, Candidate, VoteRecord, SystemLog, IndexerState, WhitelistVoter, AdminWallet

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import django_rq
from election.tasks import add_whitelist_task

# --- RATE LIMITER đơn giản dùng Django cache ---
def rate_limit(key_prefix, limit=10, window=60):
    """
    Giới hạn số request theo IP.
    limit: số request tối đa trong khoảng window giây.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '')
                .split(',')[0].strip()
                or request.META.get('REMOTE_ADDR', 'unknown')
            )
            cache_key = f"rl:{key_prefix}:{ip}"
            count = cache.get(cache_key, 0)
            if count >= limit:
                return JsonResponse(
                    {'error': f'Quá nhiều yêu cầu. Thử lại sau {window} giây.'},
                    status=429
                )
            cache.set(cache_key, count + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

# -- Web3 singleton (khởi tạo 1 lần, tái dùng toàn bộ process) --
_w3_instance = None
def get_w3():
    global _w3_instance
    if _w3_instance is None:
        _w3_instance = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_RPC_URL')))
    return _w3_instance

# -- Timezone Việt Nam (UTC+7) --
VN_TZ = timezone(timedelta(hours=7))

def fmt_time(dt):
    """Format datetime sang giờ Việt Nam."""
    return dt.astimezone(VN_TZ).strftime('%H:%M %d/%m/%Y')

# -- LOGGING SYSTEM --
def system_logs(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    return render(request, 'logs.html')

def get_latest_logs(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    logs = SystemLog.objects.all()[:50]
    logs_data = [
        {
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': log.level,
            'module': log.module,
            'message': log.message
        }
        for log in logs
    ]
    return JsonResponse({'logs': logs_data})

# 1. API Cấp mã ngẫu nhiên (Nonce)
@csrf_exempt
@rate_limit('nonce', limit=10, window=60)  # Tối đa 10 lần/phút/IP
def get_nonce(request):
    nonce = secrets.token_hex(16)
    # Lưu nonce và thời gian tạo vào session (chỉ cho phép ký trong 5 phút)
    request.session['auth_nonce'] = nonce
    request.session['nonce_time'] = time.time()
    return JsonResponse({'nonce': nonce})

# 2. API Kiểm tra chữ ký (Verify)
@csrf_exempt
@rate_limit('login', limit=5, window=60)   # Tối đa 5 lần đăng nhập/phút/IP (chống brute-force)
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
            # Dùng Web3() không cần provider để verify sig (offline)
            w3_offline = Web3()
            
            # Khôi phục địa chỉ ví từ chữ ký
            recovered_address = w3_offline.eth.account.recover_message(message, signature=signature)
            
            if recovered_address.lower() == public_address.lower():
                # CHỮ KÝ ĐÚNG -> Xóa nonce để tránh dùng lại
                del request.session['auth_nonce']
                
                # KIỂM TRA QUYỀN ADMIN
                # Ưu tiên đọc từ DB (AdminWallet model) — quản lý trực tiếp từ Django Admin UI
                # Fallback về biến môi trường nếu DB chưa có bản ghi nào (bootstrap lần đầu)
                db_wallets = set(
                    AdminWallet.objects
                    .filter(is_active=True)
                    .values_list('wallet_address', flat=True)
                )
                
                if db_wallets:
                    # Sử dụng danh sách từ DB
                    admin_wallets = {w.lower() for w in db_wallets}
                else:
                    # Fallback: đọc từ .env khi DB chưa được cài đặt
                    raw_env = (
                        os.getenv("ADMIN_WALLET_ADDRESSES") or
                        os.getenv("ADMIN_WALLET_ADDRESS") or ""
                    )
                    admin_wallets = {w.strip().lower() for w in raw_env.split(',') if w.strip()}
                
                if not admin_wallets:
                    return JsonResponse({'error': 'Chưa có admin wallet nào được cài đặt!'}, status=500)
                
                if recovered_address.lower() not in admin_wallets:
                    return JsonResponse({'error': 'Ví này không phải là Admin hệ thống!'}, status=403)
                
                wallet_lower = recovered_address.lower()
                
                # Nếu đang dùng fallback (DB rỗng), tự động seed wallet này vào DB
                if not db_wallets:
                    AdminWallet.objects.get_or_create(
                        wallet_address=wallet_lower,
                        defaults={'label': 'Admin (auto-seeded từ .env)', 'is_active': True}
                    )

                # Tích hợp vào hệ thống Authentication của Django Admin
                user, created = User.objects.get_or_create(username=wallet_lower)
                if created:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                elif not user.is_staff:
                    # Đảm bảo user cũ vẫn có quyền nếu admin thêm họ sau này
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

# Read APIs
def get_elections(request):
    """
    Lấy danh sách cuộc bầu cử kèm tổng phiếu và trạng thái indexer.
    Hỗ trợ phân trang qua query params: ?page=1&limit=10
    Dùng annotate() để tránh N+1 queries.
    """
    # --- Phân trang ---
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    try:
        limit = min(50, max(1, int(request.GET.get('limit', 10))))  # Tối đa 50 mỗi trang
    except (ValueError, TypeError):
        limit = 10

    offset = (page - 1) * limit

    # Filter theo status nếu có
    status_filter = request.GET.get('status')  # VD: ?status=active

    elections_qs = (
        Election.objects
        .annotate(total_votes=Sum('candidates__vote_count'))
        .order_by('-id')
    )
    if status_filter:
        elections_qs = elections_qs.filter(status=status_filter)

    total_count = elections_qs.count()
    page_qs = elections_qs[offset: offset + limit]

    elections = [
        {
            'id': e.id,
            'name': e.name,
            'contract_addr': e.contract_addr,
            'is_private': e.is_private,
            'status': e.status,
            'total_votes': e.total_votes or 0,
        }
        for e in page_qs
    ]

    # Kiểm tra Indexer có đang trễ nhịp không (dùng web3 singleton)
    is_lagging = False
    try:
        current_block = get_w3().eth.block_number
        state = IndexerState.objects.filter(key='main').first()
        if state and (current_block - state.last_block > 5):
            is_lagging = True
    except Exception:
        is_lagging = True

    return JsonResponse({
        'elections': elections,
        'is_lagging': is_lagging,
        # Metadata phân trang
        'pagination': {
            'total': total_count,
            'page': page,
            'limit': limit,
            'has_next': (offset + limit) < total_count,
            'has_prev': page > 1,
        }
    })



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
                'image_url': f"https://gateway.pinata.cloud/ipfs/{c.image_cid}",  # Pinata gateway: ảnh đã pin sẵn ở đây, CORS mở với nội dung public
                'vote_count': c.vote_count,
                'percentage': pct
            })
            
        return JsonResponse({
            'election': {
                'id': election.id,
                'name': election.name,
                'contract_addr': election.contract_addr,
                'status': election.status,
                'is_private': election.is_private,
                'total_votes': total_votes
            },
            'candidates': candidates_data,
            'voters': [
                {
                    'voter_address': v.voter_address,
                    'tx_hash': v.tx_hash,
                    'block_number': v.block_number,
                    'voted_at': fmt_time(v.voted_at)  # Giờ Việt Nam UTC+7
                }
                for v in VoteRecord.objects.filter(election=election).order_by('-voted_at')[:100]
            ]
        })
    except Election.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


def verify_vote_api(request):
    tx_hash = request.GET.get('tx')
    if not tx_hash:
        return JsonResponse({'error': 'Vui lòng cung cấp mã giao dịch (tx_hash)'}, status=400)
    
    # 1. Kiểm tra trong DB (Indexer đã quét) — nhanh nhất
    record = VoteRecord.objects.filter(tx_hash=tx_hash).first()
    if record:
        return JsonResponse({
            'status': 'confirmed',
            'message': 'Giao dịch đã được xác nhận và ghi nhận thành công!',
            'data': {
                'election': record.election.name,
                'voter_address': record.voter_address,
                'block_number': record.block_number,
                'time': fmt_time(record.voted_at)  # Giờ Việt Nam UTC+7
            }
        })
        
    # 2. Nếu chưa có trong DB, query trực tiếp lên Web3
    # FIX: khởi tạo w3 trước try block để tránh NameError ở except bên trong
    w3 = get_w3()
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt.status == 1:
            return JsonResponse({'status': 'indexing', 'message': 'Giao dịch đã thành công trên chuỗi, hệ thống đang đồng bộ (vui lòng đợi vài giây).'})
        else:
            return JsonResponse({'status': 'failed', 'message': 'Giao dịch đã thất bại (Reverted) trên chuỗi.'})
    except TransactionNotFound:
        # Có thể tx đang Pending trong Mempool
        try:
            w3.eth.get_transaction(tx_hash)  # Chỉ cần check tồn tại, không cần lưu
            return JsonResponse({'status': 'pending', 'message': 'Giao dịch đang chờ thợ mỏ xác nhận (Pending).'})
        except TransactionNotFound:
            return JsonResponse({'status': 'not_found', 'message': 'Không tìm thấy giao dịch này trên mạng lưới.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Fix #1: Bỏ @csrf_exempt — endpoint này dùng session cookie nên phải bảo vệ CSRF.
# JS gửi kèm header X-CSRFToken từ cookie.
def add_whitelist_api(request, election_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # GET: trả về danh sách whitelist của hòm phiếu này
    if request.method == 'GET':
        wl_list = WhitelistVoter.objects.filter(election_id=election_id).order_by('-id')
        data = [{
            'voter_address': w.voter_address,
            'tx_status': w.tx_status,
            'tx_hash': w.tx_hash,
        } for w in wl_list]
        return JsonResponse({'whitelist': data})
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            voter_address = data.get('voter_address', '').strip()
            if not voter_address:
                return JsonResponse({'error': 'Missing voter_address'}, status=400)
            
            import re
            if not re.match(r'^0x[a-fA-F0-9]{40}$', voter_address):
                return JsonResponse({'error': 'Địạ chỉ ví không hợp lệ (phải là 0x + 40 ký tự hex).'}, status=400)
                
            election = Election.objects.get(id=election_id)
            
            # Fix #10: Cho phép retry nếu TX trước đó bị FAIL
            existing = WhitelistVoter.objects.filter(
                election=election, voter_address__iexact=voter_address
            ).first()
            
            if existing:
                if existing.tx_status == 'failed':
                    # Reset để thử lại
                    existing.tx_status = 'pending'
                    existing.tx_hash = None
                    existing.tx_error = None
                    existing.save()
                    django_rq.enqueue(add_whitelist_task, existing.id)
                    return JsonResponse({'success': True, 'message': 'Đã thử lại lệnh thêm whitelist (TX cũ bị thất bại).'})
                else:
                    status_map = {'pending': 'đang xếp hàng', 'broadcasted': 'đang chờ xác nhận', 'confirmed': 'đã xác nhận'}
                    st = status_map.get(existing.tx_status, existing.tx_status)
                    return JsonResponse({'error': f'Địa chỉ này đã có trong whitelist (trạng thái: {st})!'}, status=400)
            
            wl = WhitelistVoter.objects.create(
                election=election,
                voter_address=voter_address,
                tx_status='pending'
            )
            django_rq.enqueue(add_whitelist_task, wl.id)
            return JsonResponse({'success': True, 'message': 'Đã gửi lệnh thêm whitelist vào hàng đợi ngầm.'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def internal_notify_vote(request):
    # FIX: dùng biến env riêng INTERNAL_API_SECRET thay vì DJANGO_SECRET_KEY
    expected = os.environ.get('INTERNAL_API_SECRET') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default')
    if request.headers.get('X-Internal-Secret') != expected:
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