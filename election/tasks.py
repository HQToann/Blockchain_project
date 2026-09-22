import os
import json
import logging
import threading
from web3 import Web3
from django_rq import job
from django.conf import settings
from .models import Election, Candidate, WhitelistVoter, SystemLog
from .utils import get_factory_address
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger('election.tasks')

# --- WEB3 SETUP ---
w3 = Web3(Web3.HTTPProvider(os.environ.get('ALCHEMY_RPC_URL')))
admin_private_key = os.environ.get('PRIVATE_KEY')
admin_address = w3.eth.account.from_key(admin_private_key).address if admin_private_key else None
FACTORY_ADDRESS = get_factory_address()

# Tải ABI
with open(os.path.join(settings.BASE_DIR, "Factory_ABI.json"), "r", encoding="utf-8") as f:
    FACTORY_ABI = json.load(f)

with open(os.path.join(settings.BASE_DIR, "Election_ABI.json"), "r", encoding="utf-8") as f:
    ELECTION_ABI = json.load(f)

# --- NONCE MANAGER: Redis INCR (an toàn khi scale nhiều worker) ---
# Fallback về in-memory threading.Lock nếu Redis không có sẵn
REDIS_NONCE_KEY = "blockchain_voting:admin_nonce"
_nonce_lock = threading.Lock()
_nonce_memory = None

def _get_redis_client():
    """Lấy Redis client từ django-rq connection pool."""
    try:
        import django_rq
        return django_rq.get_connection('default')
    except Exception:
        return None

# Lua script: so sánh và cập nhật nonce trong 1 thao tác atomic duy nhất
# Trả về nonce mới nhất (safe to use)
NONCE_LUA = """
local cur = redis.call('GET', KEYS[1])
if cur == false or tonumber(cur) < tonumber(ARGV[1]) then
    redis.call('SET', KEYS[1], ARGV[1])
    return tonumber(ARGV[1])
else
    return redis.call('INCR', KEYS[1])
end
"""

def get_next_nonce():
    """
    Lấy nonce tiếp theo một cách an toàn:
    - Ưu tiên Redis Lua script (atomic, an toàn khi nhiều worker)
    - Fallback về threading.Lock in-memory (1 worker)
    """
    global _nonce_memory
    onchain = w3.eth.get_transaction_count(admin_address, 'pending')

    redis_client = _get_redis_client()
    if redis_client:
        # Lua script chạy atomic trên Redis server — không có race condition
        new_nonce = redis_client.eval(NONCE_LUA, 1, REDIS_NONCE_KEY, onchain)
        return int(new_nonce)
    else:
        # Fallback: in-memory với threading.Lock
        with _nonce_lock:
            if _nonce_memory is None or onchain > _nonce_memory:
                _nonce_memory = onchain
            else:
                _nonce_memory += 1
            return _nonce_memory

def broadcast_update(election_id):
    # Optional: trigger frontend to reload
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'election_{election_id}',
        {'type': 'send_vote_update', 'message': {'refresh': True}}
    )

@job('default', timeout=60)
def deploy_election_task(election_id):
    election = Election.objects.get(id=election_id)
    try:
        factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
        nonce = get_next_nonce()
        tx = factory.functions.createElection(election.name, election.is_private).build_transaction({
            'from': admin_address,
            'nonce': nonce,
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        election.tx_hash = tx_hash.hex()
        election.tx_status = 'broadcasted'
        SystemLog.objects.create(level='INFO', module='ADMIN', message=f'Đã broadcast lệnh tạo hòm phiếu {election.name}. Tx: {tx_hash.hex()}')
    except Exception as e:
        election.tx_status = 'failed'
        election.tx_error = str(e)
        SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi tạo hòm phiếu {election.name}: {str(e)}')
    election.save()

@job('default', timeout=60)
def change_election_status_task(election_id, new_status):
    election = Election.objects.get(id=election_id)
    try:
        election_contract = w3.eth.contract(address=election.contract_addr, abi=ELECTION_ABI)
        nonce = get_next_nonce()
        if new_status == 'active':
            tx = election_contract.functions.startElection().build_transaction({
                'from': admin_address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price
            })
        else:
            tx = election_contract.functions.stopElection().build_transaction({
                'from': admin_address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price
            })
            
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        election.tx_hash = tx_hash.hex()
        election.tx_status = 'broadcasted'
        # tx_error để trống — Indexer sẽ đọc ElectionStatusChanged event từ receipt để cập nhật status
        election.tx_error = ''
        SystemLog.objects.create(level='INFO', module='ADMIN', message=f'Đã broadcast lệnh đổi trạng thái hòm phiếu {election.name}. Tx: {tx_hash.hex()}')
    except Exception as e:
        election.tx_status = 'failed'
        election.tx_error = str(e)
        SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi đổi trạng thái hòm phiếu {election.name}: {str(e)}')
    election.save()

@job('default', timeout=60)
def add_candidate_task(candidate_db_id):
    candidate = Candidate.objects.get(id=candidate_db_id)
    try:
        election_contract = w3.eth.contract(address=candidate.election.contract_addr, abi=ELECTION_ABI)
        nonce = get_next_nonce()
        tx = election_contract.functions.addCandidate(candidate.name).build_transaction({
            'from': admin_address,
            'nonce': nonce,
            'gas': 1000000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        candidate.tx_hash = tx_hash.hex()
        candidate.tx_status = 'broadcasted'
        SystemLog.objects.create(level='INFO', module='ADMIN', message=f'Đã broadcast lệnh thêm ứng viên {candidate.name}. Tx: {tx_hash.hex()}')
    except Exception as e:
        candidate.tx_status = 'failed'
        candidate.tx_error = str(e)
        SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi thêm ứng viên {candidate.name}: {str(e)}')
    candidate.save()

@job('default', timeout=60)
def add_whitelist_task(whitelist_db_id):
    wl = WhitelistVoter.objects.get(id=whitelist_db_id)
    try:
        election_contract = w3.eth.contract(address=wl.election.contract_addr, abi=ELECTION_ABI)
        nonce = get_next_nonce()
        tx = election_contract.functions.addToWhitelist([wl.voter_address]).build_transaction({
            'from': admin_address,
            'nonce': nonce,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        wl.tx_hash = tx_hash.hex()
        wl.tx_status = 'broadcasted'
        SystemLog.objects.create(level='INFO', module='ADMIN', message=f'Đã broadcast lệnh thêm whitelist {wl.voter_address}. Tx: {tx_hash.hex()}')
    except Exception as e:
        wl.tx_status = 'failed'
        wl.tx_error = str(e)
        SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi thêm whitelist {wl.voter_address}: {str(e)}')
    wl.save()
