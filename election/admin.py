import os
from django.contrib import admin
from django import forms
from django.contrib import messages
from web3 import Web3
from .models import Election, Candidate, VoteRecord, WhitelistVoter, SystemLog
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
            if obj.status == 'pending':
                obj.tx_status = 'pending'
                obj.save()
                django_rq.enqueue(change_election_status_task, obj.id, 'active')
                messages.info(request, f"Đang đẩy lệnh Mở hòm phiếu {obj.name} xuống Background Task...")
                    
    @admin.action(description="Đóng Hòm Phiếu (Ngừng vote)")
    def make_closed(self, request, queryset):
        for obj in queryset:
            if obj.status == 'active':
                obj.tx_status = 'pending'
                obj.save()
                django_rq.enqueue(change_election_status_task, obj.id, 'closed')
                messages.info(request, f"Đang đẩy lệnh Đóng hòm phiếu {obj.name} xuống Background Task...")

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
