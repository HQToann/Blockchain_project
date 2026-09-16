from django.db import models

class Election(models.Model):
    contract_addr = models.CharField(max_length=42, unique=True, null=True, blank=True) # Địa chỉ sinh ra từ Factory
    name = models.CharField(max_length=255)
    is_private = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='pending') # pending, active, closed
    
    # Background Task Tracking
    tx_hash = models.CharField(max_length=66, blank=True, null=True)
    tx_status = models.CharField(max_length=20, default='pending', choices=[('pending','Đang xếp hàng'),('broadcasted','Đang chờ xác nhận'),('confirmed','Thành công'),('failed','Thất bại')])
    tx_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Candidate(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    candidate_id = models.PositiveIntegerField(null=True, blank=True) # ID tương ứng trên Smart Contract
    name = models.CharField(max_length=255)
    image_cid = models.CharField(max_length=100) # Mã IPFS Pinata
    vote_count = models.PositiveIntegerField(default=0)
    
    # Background Task Tracking
    tx_hash = models.CharField(max_length=66, blank=True, null=True)
    tx_status = models.CharField(max_length=20, default='pending', choices=[('pending','Đang xếp hàng'),('broadcasted','Đang chờ xác nhận'),('confirmed','Thành công'),('failed','Thất bại')])
    tx_error = models.TextField(blank=True, null=True)

class VoteRecord(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    voter_address  = models.CharField(max_length=42)
    # KHÔNG LƯU candidate_id để bảo vệ quyền riêng tư
    tx_hash = models.CharField(max_length=66, unique=True)
    block_number = models.PositiveBigIntegerField()
    voted_at = models.DateTimeField(auto_now_add=True)

class WhitelistVoter(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='whitelist')
    voter_address = models.CharField(max_length=42)
    
    # Background Task Tracking
    tx_hash = models.CharField(max_length=66, blank=True, null=True)
    tx_status = models.CharField(max_length=20, default='pending', choices=[('pending','Đang xếp hàng'),('broadcasted','Đang chờ xác nhận'),('confirmed','Thành công'),('failed','Thất bại')])
    tx_error = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('election', 'voter_address')

class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Thông tin'),
        ('SUCCESS', 'Thành công'),
        ('WARNING', 'Cảnh báo'),
        ('ERROR', 'Lỗi'),
    ]
    MODULE_CHOICES = [
        ('SYSTEM', 'Hệ thống'),
        ('BLOCKCHAIN', 'Blockchain'),
        ('IPFS', 'IPFS Pinata'),
        ('ADMIN', 'Quản trị viên'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, default='SYSTEM')
    message = models.TextField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.get_level_display()}] {self.module}: {self.message[:50]}"

class IndexerState(models.Model):
    key = models.CharField(max_length=50, unique=True, default='main')
    last_block = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"State: {self.key} - Block: {self.last_block}"