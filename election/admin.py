import os
from django.contrib import admin
from django import forms
from django.contrib import messages
from web3 import Web3
from .models import Election, Candidate, VoteRecord, WhitelistVoter, SystemLog, AdminWallet
from .services import upload_image_to_ipfs

import json

import django_rq
from .tasks import (
    deploy_election_task, change_election_status_task,
    add_candidate_task, add_whitelist_task
)

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
            # GỌI SMART CONTRACT KHI TẠO HÒM PHIẾU (BACKGROUND TASK)
            obj.tx_status = 'pending'
            super().save_model(request, obj, form, change)
            django_rq.enqueue(deploy_election_task, obj.id)
            messages.info(request, "Đang gửi lệnh tạo hòm phiếu xuống Background Task. Vui lòng F5 sau ít phút để kiểm tra trạng thái.")
            return
            
        super().save_model(request, obj, form, change)

    @admin.action(description="Mở Hòm Phiếu (Bắt đầu cho vote)")
    def make_active(self, request, queryset):
        for obj in queryset:
            if obj.status == 'pending' and obj.tx_status != 'broadcasted':
                obj.tx_status = 'pending'
                obj.save()
                django_rq.enqueue(change_election_status_task, obj.id, 'active')
                messages.info(request, f"Đang đẩy lệnh Mở hòm phiếu {obj.name} xuống Background Task...")
            elif obj.tx_status == 'broadcasted':
                messages.warning(request, f"Hòm phiếu {obj.name} đang có giao dịch chờ xác nhận, vui lòng đợi.")
                    
    @admin.action(description="Đóng Hòm Phiếu (Ngừng vote)")
    def make_closed(self, request, queryset):
        for obj in queryset:
            if obj.status == 'active' and obj.tx_status != 'broadcasted':
                obj.tx_status = 'pending'
                obj.save()
                django_rq.enqueue(change_election_status_task, obj.id, 'closed')
                messages.info(request, f"Đang đẩy lệnh Đóng hòm phiếu {obj.name} xuống Background Task...")
            elif obj.tx_status == 'broadcasted':
                messages.warning(request, f"Hòm phiếu {obj.name} đang có giao dịch chờ xác nhận, vui lòng đợi.")

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

                # 2. Đưa vào Background Task
                obj.tx_status = 'pending'
                super().save_model(request, obj, form, change)
                django_rq.enqueue(add_candidate_task, obj.id)
                
                messages.info(request, f"Đang tải dữ liệu ứng viên {obj.name} lên Blockchain ngầm. Vui lòng F5 sau ít phút...")
                return
            except Exception as e:
                messages.error(request, f"Lỗi IPFS/Hệ thống khi tạo Ứng viên: {str(e)}")
                return
                
        super().save_model(request, obj, form, change)

@admin.register(WhitelistVoter)
class WhitelistVoterAdmin(admin.ModelAdmin):
    list_display = ('election', 'voter_address')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.tx_status = 'pending'
            super().save_model(request, obj, form, change)
            django_rq.enqueue(add_whitelist_task, obj.id)
            messages.info(request, "Đang đẩy lệnh thêm Whitelist xuống Background Task...")
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


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display  = ('wallet_display', 'label', 'is_active', 'added_at')
    list_editable = ('label', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('wallet_address', 'label')
    readonly_fields = ('added_at',)
    actions = ['activate_wallets', 'deactivate_wallets']

    def wallet_display(self, obj):
        short = obj.wallet_address[:10] + '...' + obj.wallet_address[-6:]
        return short
    wallet_display.short_description = 'Wallet Address'

    def save_model(self, request, obj, form, change):
        # Tự chuẩn hóa chữ thường và kiểm tra định dạng địa chỉ
        obj.wallet_address = obj.wallet_address.strip().lower()  # LOWERCASE để nhất quán với logic so sánh
        import re
        if not re.match(r'^0x[a-fA-F0-9]{40}$', obj.wallet_address):
            from django.core.exceptions import ValidationError
            self.message_user(request, f'Địa chỉ ví không hợp lệ: {obj.wallet_address}', level='error')
            return
        super().save_model(request, obj, form, change)
        messages.success(request, f"Đã lưu admin wallet {obj.wallet_address[:12]}...")

    @admin.action(description="✅ Kích hoạt các ví đã chọn")
    def activate_wallets(self, request, queryset):
        count = queryset.update(is_active=True)
        messages.success(request, f"Đã kích hoạt {count} admin wallet.")

    @admin.action(description="🚧 Vô hiệu hoá các ví đã chọn")
    def deactivate_wallets(self, request, queryset):
        count = queryset.update(is_active=False)
        messages.warning(request, f"Đã vô hiệu hoá {count} admin wallet.")
