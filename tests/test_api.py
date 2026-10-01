"""
Operation 'ABHEDYA-CHAKRA'
Automated Test Suite for Base v0.1 FastAPI Endpoints
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "abhedya-chakra-api"


def test_dataset_summary():
    res = client.get("/api/dataset/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] == 2000000
    assert data["unique_accounts"] > 0
    assert data["unique_transactions"] > 0
    assert data["total_amount"] > 0
    assert data["timestamp_available"] is True
    assert data["device_type_available"] is True
    assert data["source_type"] == "PRODUCTION_DATASET"
    assert set(data["payment_modes"].keys()) == {"UPI", "IMPS", "NEFT", "RTGS"}


def test_account_search():
    # Search for known prefix
    res = client.get("/api/accounts/search?q=KKBK&limit=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    first = data[0]
    assert "account" in first
    assert "inbound_transaction_count" in first
    assert "outbound_transaction_count" in first
    assert "observed_inflow" in first
    assert "observed_outflow" in first
    assert "dataset_observed_net_movement" in first


def test_account_detail_real():
    # Use real account from dataset
    res = client.get("/api/accounts/KKBK10000000")
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == "KKBK10000000"
    assert data["inbound_transaction_count"] >= 0
    assert data["outbound_transaction_count"] > 0
    assert isinstance(data["associated_ifscs"], list)
    assert isinstance(data["associated_ips"], list)


def test_account_detail_404():
    res = client.get("/api/accounts/NONEXISTENT999999")
    assert res.status_code == 404


def test_account_transactions_pagination():
    res = client.get("/api/accounts/KKBK10000000/transactions?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == "KKBK10000000"
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["items"]) <= 10
    if len(data["items"]) > 0:
        item = data["items"][0]
        assert item["Timestamp"] is not None
        assert item["Device_Type"] is not None
        assert item["Amount"] > 0


def test_account_graph():
    res = client.get("/api/accounts/KKBK10000000/graph?max_hops=1&max_nodes=50")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    root_node = next((n for n in data["nodes"] if n["id"] == "KKBK10000000"), None)
    assert root_node is not None
    assert root_node["is_root"] is True


def test_account_trace_4_hops():
    res = client.get("/api/accounts/KKBK10000000/trace?max_nodes=100")
    assert res.status_code == 200
    data = res.json()
    assert data["root_account"] == "KKBK10000000"
    assert data["max_hops"] == 4
    assert "nodes" in data
    assert "edges" in data
    assert "paths" in data
    assert isinstance(data["paths"], list)
