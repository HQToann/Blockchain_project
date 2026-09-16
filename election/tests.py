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
        self.assertEqual(data['election']['name'], "Test Django Election")
        self.assertEqual(data['election']['total_votes'], 5)
        self.assertEqual(len(data['candidates']), 1)
        self.assertEqual(data['candidates'][0]['percentage'], 100.0)

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
        
        # Test authorized
        resp2 = self.client.post('/api/internal/notify_vote/', json.dumps({
            'election_id': self.election.id,
            'candidate_id': 0,
            'tx_hash': '0xabc'
        }), content_type='application/json', HTTP_X_INTERNAL_SECRET=os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default'))
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
