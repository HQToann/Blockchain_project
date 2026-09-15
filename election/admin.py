import os
from django.contrib import admin
from django import forms
from django.contrib import messages
from web3 import Web3
from .models import Election, Candidate, VoteRecord, WhitelistVoter, SystemLog
from .services import upload_image_to_ipfs

import json

# --- WEB3 SETUP ---
w3 = Web3(Web3.HTTPProvider(os.environ.get('ALCHEMY_RPC_URL')))
admin_private_key = os.environ.get('PRIVATE_KEY')
admin_address = w3.eth.account.from_key(admin_private_key).address if admin_private_key else None

FACTORY_ADDRESS = "0x44F8Db431EA5049D60547777Af54a0D7E46D12DE"

# Tải ABI tự động từ file JSON giống như Indexer
with open("artifacts/contracts/VotingSystem.sol/ElectionFactory.json", "r", encoding="utf-8") as f:
    FACTORY_ABI = json.load(f)["abi"]

with open("artifacts/contracts/VotingSystem.sol/Election.json", "r", encoding="utf-8") as f:
    ELECTION_ABI = json.load(f)["abi"]

# --- ADMIN FORMS ---
class CandidateForm(forms.ModelForm):
    upload_image = forms.ImageField(required=True, label="Tải ảnh Ứng viên lên")

    class Meta:
        model = Candidate
        fields = ['election', 'name', 'upload_image'] # Chỉ hiển thị 3 trường này khi tạo

# --- ADMIN CLASSES ---
@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contract_addr', 'status', 'is_private', 'created_at')
    readonly_fields = ('contract_addr', 'status')
    actions = ['make_active', 'make_closed']

    def save_model(self, request, obj, form, change):
        if not change:
            # GỌI SMART CONTRACT KHI TẠO HÒM PHIẾU
            try:
                factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=FACTORY_ABI)
                tx = factory.functions.createElection(obj.name, obj.is_private).build_transaction({
                    'from': admin_address,
                    'nonce': w3.eth.get_transaction_count(admin_address, 'pending'),
                    'gas': 3000000,
                    'gasPrice': w3.eth.gas_price
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                messages.info(request, "Đang gửi giao dịch lên Blockchain. Vui lòng đợi (có thể mất 1-3 phút)...")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                
                if receipt.status == 0:
                    messages.error(request, "Giao dịch bị từ chối trên Blockchain (Reverted)!")
                    SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Giao dịch tạo hòm phiếu bị Reverted. Tx: {tx_hash.hex()}')
                    return
                
                # Parse event để lấy địa chỉ contract
                logs = factory.events.ElectionCreated().process_receipt(receipt)
                if logs:
                    obj.contract_addr = logs[0]['args']['electionAddress']
                    SystemLog.objects.create(level='SUCCESS', module='ADMIN', message=f'Tạo hòm phiếu {obj.name} thành công. Contract: {obj.contract_addr}')
                else:
                    messages.error(request, "Tạo Blockchain thất bại: Không tìm thấy sự kiện (Sai ABI hoặc lỗi mạng).")
                    SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Tạo hòm phiếu {obj.name} thất bại: Không tìm thấy sự kiện ElectionCreated.')
                    return
            except Exception as e:
                err_msg = str(e)
                if "underpriced" in err_msg:
                    messages.error(request, "Giao dịch trước đó của bạn vẫn đang chờ mạng lưới xác nhận! Vui lòng không bấm Lưu liên tục. Hãy đợi 1-2 phút rồi kiểm tra lại.")
                else:
                    messages.error(request, f"Lỗi Blockchain: {err_msg}")
                SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi tạo hòm phiếu {obj.name}: {err_msg}')
                return
                
        super().save_model(request, obj, form, change)

    @admin.action(description="Mở Hòm Phiếu (Bắt đầu cho vote)")
    def make_active(self, request, queryset):
        for obj in queryset:
            if obj.status == 'pending':
                try:
                    election_contract = w3.eth.contract(address=obj.contract_addr, abi=ELECTION_ABI)
                    tx = election_contract.functions.startElection().build_transaction({
                        'from': admin_address,
                        'nonce': w3.eth.get_transaction_count(admin_address, 'pending'),
                        'gas': 500000,
                        'gasPrice': w3.eth.gas_price
                    })
                    signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    
                    messages.info(request, f"Đang gửi lệnh Mở hòm phiếu {obj.name} lên Blockchain. Vui lòng đợi...")
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                    
                    if receipt.status == 0:
                        messages.error(request, f"Lỗi Blockchain: Không thể mở hòm phiếu {obj.name} (Reverted).")
                        return

                    obj.status = 'active'
                    obj.save()
                    messages.success(request, f"Đã mở hòm phiếu: {obj.name}")
                    SystemLog.objects.create(level='INFO', module='ADMIN', message=f'Mở hòm phiếu {obj.name}. Tx: {tx_hash.hex()}')
                except Exception as e:
                    err_msg = str(e)
                    if "underpriced" in err_msg:
                        messages.error(request, "Giao dịch Mở hòm phiếu đang chờ xác nhận, vui lòng không thao tác lại!")
                    else:
                        messages.error(request, f"Lỗi mở hòm phiếu {obj.name}: {err_msg}")
                    SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi mở hòm phiếu {obj.name}: {err_msg}')
                    
    @admin.action(description="Đóng Hòm Phiếu (Ngừng vote)")
    def make_closed(self, request, queryset):
        for obj in queryset:
            if obj.status == 'active':
                try:
                    election_contract = w3.eth.contract(address=obj.contract_addr, abi=ELECTION_ABI)
                    tx = election_contract.functions.stopElection().build_transaction({
                        'from': admin_address,
                        'nonce': w3.eth.get_transaction_count(admin_address, 'pending'),
                        'gas': 500000,
                        'gasPrice': w3.eth.gas_price
                    })
                    signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
                    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    
                    messages.info(request, f"Đang gửi lệnh Đóng hòm phiếu {obj.name} lên Blockchain. Vui lòng đợi...")
                    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                    
                    if receipt.status == 0:
                        messages.error(request, f"Lỗi Blockchain: Không thể đóng hòm phiếu {obj.name} (Reverted).")
                        return

                    obj.status = 'closed'
                    obj.save()
                    messages.success(request, f"Đã đóng hòm phiếu: {obj.name}")
                    SystemLog.objects.create(level='WARNING', module='ADMIN', message=f'Đóng hòm phiếu {obj.name}. Tx: {tx_hash.hex()}')
                except Exception as e:
                    err_msg = str(e)
                    if "underpriced" in err_msg:
                        messages.error(request, "Giao dịch Đóng hòm phiếu đang chờ xác nhận, vui lòng không thao tác lại!")
                    else:
                        messages.error(request, f"Lỗi đóng hòm phiếu {obj.name}: {err_msg}")
                    SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi đóng hòm phiếu {obj.name}: {err_msg}')

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    form = CandidateForm
    list_display = ('id', 'name', 'election', 'candidate_id', 'vote_count')

    def get_readonly_fields(self, request, obj=None):
        if obj: # Khi edit
            return ('candidate_id', 'image_cid', 'vote_count')
        return ()

    def save_model(self, request, obj, form, change):
        if not change:
            try:
                # 1. Tải ảnh lên IPFS
                image_file = form.cleaned_data['upload_image']
                cid = upload_image_to_ipfs(image_file)
                obj.image_cid = cid

                # 2. Gọi Smart Contract
                election_contract = w3.eth.contract(address=obj.election.contract_addr, abi=ELECTION_ABI)
                tx = election_contract.functions.addCandidate(obj.name).build_transaction({
                    'from': admin_address,
                    'nonce': w3.eth.get_transaction_count(admin_address, 'pending'),
                    'gas': 1000000,
                    'gasPrice': w3.eth.gas_price
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                messages.info(request, f"Đang gửi lệnh thêm ứng viên {obj.name}. Vui lòng chờ mạng lưới xác nhận (có thể tốn 1-3 phút)...")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

                if receipt.status == 0:
                    messages.error(request, "Lỗi Blockchain: Thêm ứng viên thất bại (Reverted)! Hòm phiếu có thể đã được Mở.")
                    SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi thêm ứng viên {obj.name} (Reverted).')
                    return

                # 3. Tự động tính ID
                current_count = Candidate.objects.filter(election=obj.election).count()
                obj.candidate_id = current_count
                
                messages.success(request, f"Thêm ứng viên {obj.name} thành công lên Blockchain!")
                SystemLog.objects.create(level='SUCCESS', module='ADMIN', message=f'Thêm ứng viên {obj.name} vào hòm phiếu {obj.election.name}. Tx: {tx_hash.hex()}')
            except Exception as e:
                err_msg = str(e)
                if "underpriced" in err_msg:
                    messages.error(request, "Giao dịch thêm ứng viên trước đó vẫn đang treo trên mạng lưới! Vui lòng không bấm Lưu liên tục. Hãy đợi thêm vài phút.")
                elif "is not in the chain after" in err_msg:
                    messages.error(request, "Mạng lưới Sepolia hiện tại quá nghẽn. Giao dịch vẫn đang được xử lý ngầm, vui lòng kiểm tra lại sau ít phút!")
                else:
                    messages.error(request, f"Lỗi hệ thống khi tạo Ứng viên: {err_msg}")
                SystemLog.objects.create(level='ERROR', module='ADMIN', message=f'Lỗi thêm ứng viên {obj.name}: {err_msg}')
                return
                
        super().save_model(request, obj, form, change)

@admin.register(WhitelistVoter)
class WhitelistVoterAdmin(admin.ModelAdmin):
    list_display = ('election', 'voter_address')

    def save_model(self, request, obj, form, change):
        if not change:
            try:
                election_contract = w3.eth.contract(address=obj.election.contract_addr, abi=ELECTION_ABI)
                tx = election_contract.functions.addVoterToWhitelist(obj.voter_address).build_transaction({
                    'from': admin_address,
                    'nonce': w3.eth.get_transaction_count(admin_address, 'pending'),
                    'gas': 200000,
                    'gasPrice': w3.eth.gas_price
                })
                signed_tx = w3.eth.account.sign_transaction(tx, private_key=admin_private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                
                if receipt.status == 0:
                    messages.error(request, "Lỗi Blockchain: Thêm whitelist thất bại (Reverted).")
                    return
            except Exception as e:
                err_msg = str(e)
                if "underpriced" in err_msg:
                    messages.error(request, "Giao dịch thêm whitelist đang chờ xác nhận, vui lòng không thao tác lại!")
                else:
                    messages.error(request, f"Lỗi thêm whitelist: {err_msg}")
                return
        super().save_model(request, obj, form, change)

@admin.register(VoteRecord)
class VoteRecordAdmin(admin.ModelAdmin):
    list_display = ('tx_hash', 'election', 'voter_address', 'voted_at')
    
    # Chỉ đọc, không cho tạo/xóa từ admin
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
