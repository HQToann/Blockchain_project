import os
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from .models import Election, Candidate, WhitelistVoter

class ElectionViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.election = Election.objects.create(
            name="Test Django Election",
            contract_addr="0x123",
            is_private=True,
            status="active"
        )
        self.candidate = Candidate.objects.create(
            election=self.election,
            candidate_id=0,
            name="Alice",
            image_cid="QmTest",
            vote_count=5
        )

    def test_get_election_detail(self):
        response = self.client.get(f'/api/elections/{self.election.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Kiểm tra các field cơ bản
        self.assertEqual(data['election']['name'], "Test Django Election")
        self.assertEqual(data['election']['total_votes'], 5)
        self.assertEqual(data['election']['is_private'], True)   # FIX: kiểm tra field is_private
        self.assertEqual(len(data['candidates']), 1)
        self.assertEqual(data['candidates'][0]['percentage'], 100.0)
        # Kiểm tra field voters mới thêm
        self.assertIn('voters', data)
        self.assertIsInstance(data['voters'], list)
        self.assertEqual(len(data['voters']), 0)  # Chưa có VoteRecord nào trong setUp

    @patch('election.views.async_to_sync')
    def test_internal_notify_vote(self, mock_async_to_sync):
        mock_sync_func = MagicMock()
        mock_async_to_sync.return_value = mock_sync_func
        
        # Test unauthorized (no secret token)
        resp1 = self.client.post('/api/internal/notify_vote/', json.dumps({
            'election_id': self.election.id,
            'candidate_id': 0,
            'tx_hash': '0xabc'
        }), content_type='application/json')
        self.assertEqual(resp1.status_code, 403)
        
        # Test authorized - dùng đúng secret hiện tại (INTERNAL_API_SECRET nếu có, else DJANGO_SECRET_KEY)
        secret = os.environ.get('INTERNAL_API_SECRET') or os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default')
        resp2 = self.client.post('/api/internal/notify_vote/', json.dumps({
            'election_id': self.election.id,
            'candidate_id': 0,
            'tx_hash': '0xabc'
        }), content_type='application/json', HTTP_X_INTERNAL_SECRET=secret)
        self.assertEqual(resp2.status_code, 200, f"Lỗi: {resp2.content}")
        self.assertTrue(mock_sync_func.called)

class IndexerTest(TestCase):
    def setUp(self):
        self.election = Election.objects.create(
            name="Test Indexer Election",
            status="pending",
            tx_status="broadcasted",
            tx_hash="0xabc123"
        )

    @patch('indexer.indexer.w3')
    @patch('indexer.indexer.factory_contract')
    def test_check_broadcasted_transactions_confirmed(self, mock_factory, mock_w3):
        # Cần import trễ để tránh lỗi Apps aren't loaded yet nếu script kia tự gọi django.setup()
        from indexer.indexer import check_broadcasted_transactions
        
        # Setup mock Web3 to return a confirmed receipt
        mock_receipt = MagicMock()
        mock_receipt.status = 1
        mock_w3.eth.get_transaction_receipt.return_value = mock_receipt
        
        mock_logs = [{'args': {'electionAddress': '0x999'}}]
        mock_factory.events.ElectionCreated.return_value.process_receipt.return_value = mock_logs
        
        check_broadcasted_transactions()
        
        self.election.refresh_from_db()
        self.assertEqual(self.election.tx_status, 'confirmed')
        self.assertEqual(self.election.contract_addr, '0x999')

    @patch('indexer.indexer.w3')
    @patch('indexer.indexer.factory_contract')
    def test_check_broadcasted_status_change_via_event(self, mock_factory, mock_w3):
        """
        Test TH2: Indexer đọc ElectionStatusChanged event để đổi status
        Thay thế hack cũ (pending_status trong tx_error).
        """
        from indexer.indexer import check_broadcasted_transactions

        # Tạo election đã có contract_addr (TH2: đổi trạng thái)
        election_with_contract = Election.objects.create(
            name="Election With Contract",
            status="pending",
            contract_addr="0xABC",
            tx_status="broadcasted",
            tx_hash="0xdef456",
            tx_error=""  # Không có hack pending_status
        )

        mock_receipt = MagicMock()
        mock_receipt.status = 1
        mock_w3.eth.get_transaction_receipt.return_value = mock_receipt

        # Mock ElectionStatusChanged event trả về isOpen=True
        mock_status_logs = [{'args': {'isOpen': True}}]
        mock_election_contract = MagicMock()
        mock_election_contract.events.ElectionStatusChanged.return_value.process_receipt.return_value = mock_status_logs
        mock_w3.eth.contract.return_value = mock_election_contract

        # factory_contract.events.ElectionCreated không được gọi ở TH2
        mock_factory.events.ElectionCreated.return_value.process_receipt.return_value = []

        check_broadcasted_transactions()

        election_with_contract.refresh_from_db()
        self.assertEqual(election_with_contract.tx_status, 'confirmed')
        self.assertEqual(election_with_contract.status, 'active')  # isOpen=True → active
        self.assertEqual(election_with_contract.tx_error, '')

