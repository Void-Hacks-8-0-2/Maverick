"""
Unit & Integration Tests for Step 10B — Transaction Explorer
Tests search, filtering, server-side pagination, sorting, duplicate transaction IDs,
stable row identities, and forensic detail inspection.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db
from backend.transactions.service import query_transactions_explorer, get_transaction_by_stable_id

client = TestClient(app)

BENCHMARK_ACCOUNT = "KKBK10000402"


@pytest.fixture(scope="module")
def db_conn():
    return get_db()


class TestTransactionsService:
    def test_basic_query_and_pagination(self, db_conn):
        resp = query_transactions_explorer(db_conn, page=1, page_size=25)
        assert resp.page == 1
        assert resp.page_size == 25
        assert len(resp.items) == 25
        assert resp.total_count == 2000000
        assert resp.total_pages > 0
        assert resp.has_next is True
        assert resp.has_previous is False
        assert resp.provenance.dataset_sha256 == "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"

    def test_account_filter_in_and_out(self, db_conn):
        resp = query_transactions_explorer(db_conn, account_id=BENCHMARK_ACCOUNT, page_size=50)
        assert resp.total_count > 0
        for item in resp.items:
            assert item.Sender_Account == BENCHMARK_ACCOUNT or item.Receiver_Account == BENCHMARK_ACCOUNT

    def test_sender_and_receiver_filters(self, db_conn):
        # Sender filter
        sender_resp = query_transactions_explorer(db_conn, sender_account=BENCHMARK_ACCOUNT, page_size=20)
        for item in sender_resp.items:
            assert item.Sender_Account == BENCHMARK_ACCOUNT

        # Receiver filter
        receiver_resp = query_transactions_explorer(db_conn, receiver_account=BENCHMARK_ACCOUNT, page_size=20)
        for item in receiver_resp.items:
            assert item.Receiver_Account == BENCHMARK_ACCOUNT

    def test_exact_and_partial_transaction_id_search(self, db_conn):
        # Grab a sample transaction
        sample = db_conn.execute("SELECT Transaction_ID FROM transactions LIMIT 1").fetchone()[0]

        # Exact match
        exact_resp = query_transactions_explorer(db_conn, transaction_id=sample, page_size=10)
        assert exact_resp.total_count >= 1
        assert any(item.Transaction_ID == sample for item in exact_resp.items)

        # Partial match
        partial = sample[:6]
        part_resp = query_transactions_explorer(db_conn, transaction_id=partial, page_size=10)
        assert part_resp.total_count >= 1
        for item in part_resp.items:
            assert partial in item.Transaction_ID

    def test_amount_range_filter(self, db_conn):
        resp = query_transactions_explorer(db_conn, min_amount=50000.0, max_amount=100000.0, page_size=20)
        assert len(resp.items) > 0
        for item in resp.items:
            assert 50000.0 <= item.Amount <= 100000.0

    def test_temporal_bounds_filter(self, db_conn):
        start = "2026-09-18 00:00:00"
        end = "2026-09-18 23:59:59"
        resp = query_transactions_explorer(db_conn, start_time=start, end_time=end, page_size=20)
        for item in resp.items:
            assert start <= item.Timestamp <= end

    def test_payment_mode_and_device_filters(self, db_conn):
        resp = query_transactions_explorer(
            db_conn, payment_mode="IMPS", device_type="Android", page_size=20
        )
        for item in resp.items:
            assert item.Payment_Mode == "IMPS"
            assert item.Device_Type == "Android"

    def test_sorting_by_amount_and_timestamp(self, db_conn):
        # Sort by amount desc
        amt_resp = query_transactions_explorer(db_conn, sort_by="amount", sort_order="desc", page_size=25)
        amounts = [item.Amount for item in amt_resp.items]
        assert amounts == sorted(amounts, reverse=True)

        # Sort by timestamp asc
        ts_resp = query_transactions_explorer(db_conn, sort_by="timestamp", sort_order="asc", page_size=25)
        ts_list = [item.Timestamp for item in ts_resp.items]
        assert ts_list == sorted(ts_list)

    def test_stable_row_identity(self, db_conn):
        resp = query_transactions_explorer(db_conn, page=1, page_size=10)
        for item in resp.items:
            assert item.stable_id.startswith("row_")
            assert item.row_id >= 0
            assert str(item.row_id) in item.stable_id

    def test_get_transaction_by_stable_id(self, db_conn):
        # Retrieve row 0
        detail = get_transaction_by_stable_id(db_conn, "row_0")
        assert detail.transaction.row_id == 0
        assert detail.transaction.stable_id == "row_0"
        assert "sender_account" in detail.investigation_links
        assert "links" in detail.investigation_links
        assert "sender_timeline" in detail.investigation_links["links"]


class TestTransactionsAPI:
    def test_get_transactions_endpoint(self):
        res = client.get("/api/transactions?page=1&page_size=25")
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 25
        assert data["total_count"] == 2000000
        assert data["page"] == 1
        assert data["page_size"] == 25

    def test_get_transactions_filtered(self):
        res = client.get("/api/transactions?account_id=KKBK10000402&payment_mode=UPI&page_size=10")
        assert res.status_code == 200
        data = res.json()
        for item in data["items"]:
            assert item["Payment_Mode"] == "UPI"
            assert item["Sender_Account"] == "KKBK10000402" or item["Receiver_Account"] == "KKBK10000402"

    def test_get_transaction_detail_endpoint(self):
        res = client.get("/api/transactions/row_0")
        assert res.status_code == 200
        data = res.json()
        assert data["transaction"]["stable_id"] == "row_0"
        assert "investigation_links" in data
        assert "provenance" in data

    def test_get_transaction_detail_not_found(self):
        res = client.get("/api/transactions/row_999999999")
        assert res.status_code == 404
