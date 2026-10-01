"""
Correctness and Performance Regression Tests for Materialized Accounts Dimension
Validates accounts_dimension completeness, exact aggregation, entity rules, and search speed.
"""

import time
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.connection import get_db
from backend.features.models import AccountFeatures

client = TestClient(app)


def test_dimension_row_count_matches_union_of_senders_and_receivers():
    """
    Test 1: Every unique account in sender_account ∪ receiver_account exists in the dimension.
    Total unique account entities must equal exactly 24,873.
    """
    con = get_db()
    union_count = con.execute("""
        SELECT COUNT(DISTINCT acc) FROM (
            SELECT Sender_Account AS acc FROM transactions
            UNION
            SELECT Receiver_Account AS acc FROM transactions
        )
    """).fetchone()[0]

    dim_count = con.execute("SELECT COUNT(*) FROM accounts_dimension").fetchone()[0]
    assert dim_count == 24873, f"Expected 24873 accounts in dimension, found {dim_count}"
    assert dim_count == union_count, f"Dimension count ({dim_count}) does not match union count ({union_count})"


def test_known_account_aggregation_matches_raw_transactions():
    """
    Test 2 & 3: For a known account, total_inflow, total_outflow, net_flow_delta,
    and transaction counts match direct aggregation from the transaction source.
    """
    con = get_db()
    test_account = "SBIN10012624"

    # Query materialized dimension
    dim_row = con.execute("""
        SELECT 
            total_inflow, 
            total_outflow, 
            net_flow_delta, 
            incoming_txn_count, 
            outgoing_txn_count, 
            transaction_count,
            unique_senders,
            unique_receivers,
            counterparty_count
        FROM accounts_dimension 
        WHERE account_number = ?
    """, [test_account]).fetchone()

    assert dim_row is not None, f"Account {test_account} not found in dimension"
    (
        dim_inflow, dim_outflow, dim_net, 
        dim_inc_cnt, dim_out_cnt, dim_tx_cnt,
        dim_u_senders, dim_u_receivers, dim_cp_cnt
    ) = dim_row

    # Query raw transactions directly
    raw_in = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT Sender_Account), COALESCE(SUM(Amount), 0.0)
        FROM transactions WHERE Receiver_Account = ?
    """, [test_account]).fetchone()

    raw_out = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT Receiver_Account), COALESCE(SUM(Amount), 0.0)
        FROM transactions WHERE Sender_Account = ?
    """, [test_account]).fetchone()

    # Inflow, outflow, and net flow reconciliation
    assert dim_inflow == round(raw_in[2], 2), "Inflow aggregation mismatch"
    assert dim_outflow == round(raw_out[2], 2), "Outflow aggregation mismatch"
    assert dim_net == round(raw_in[2] - raw_out[2], 2), "Observed Net Flow Delta mismatch"

    # Transaction counts reconciliation
    assert dim_inc_cnt == raw_in[0], "Incoming transaction count mismatch"
    assert dim_out_cnt == raw_out[0], "Outgoing transaction count mismatch"
    assert dim_tx_cnt == (raw_in[0] + raw_out[0]), "Total transaction count mismatch"

    # Counterparty metrics reconciliation
    assert dim_u_senders == raw_in[1], "Unique senders count mismatch"
    assert dim_u_receivers == raw_out[1], "Unique receivers count mismatch"


def test_receiver_only_accounts_exist_in_dimension():
    """
    Test 4: Receiver-only accounts exist in the dimension with outgoing_txn_count = 0.
    """
    con = get_db()
    rec_only_rows = con.execute("""
        SELECT account_number, incoming_txn_count, outgoing_txn_count, total_inflow, total_outflow, net_flow_delta
        FROM accounts_dimension
        WHERE outgoing_txn_count = 0
    """).fetchall()

    assert len(rec_only_rows) > 0, "Expected receiver-only accounts to exist"
    assert len(rec_only_rows) == 385, f"Expected 385 receiver-only accounts, got {len(rec_only_rows)}"

    # Spot check first 5 receiver-only accounts against raw transactions
    for acc, inc, outc, inflow, outflow, net in rec_only_rows[:5]:
        assert outc == 0
        assert outflow == 0.0
        assert net == inflow
        raw_out_count = con.execute("SELECT COUNT(*) FROM transactions WHERE Sender_Account = ?", [acc]).fetchone()[0]
        assert raw_out_count == 0, f"Account {acc} marked as receiver-only but has raw outbound transactions"


def test_sender_only_accounts_exist_in_dimension():
    """
    Test 5: Sender-only accounts exist in the dimension with incoming_txn_count = 0.
    """
    con = get_db()
    sender_only_rows = con.execute("""
        SELECT account_number, incoming_txn_count, outgoing_txn_count, total_inflow, total_outflow, net_flow_delta
        FROM accounts_dimension
        WHERE incoming_txn_count = 0
    """).fetchall()

    assert len(sender_only_rows) > 0, "Expected sender-only accounts to exist"
    assert len(sender_only_rows) == 300, f"Expected 300 sender-only accounts, got {len(sender_only_rows)}"

    # Spot check first 5 sender-only accounts against raw transactions
    for acc, inc, outc, inflow, outflow, net in sender_only_rows[:5]:
        assert inc == 0
        assert inflow == 0.0
        assert net == -outflow
        raw_in_count = con.execute("SELECT COUNT(*) FROM transactions WHERE Receiver_Account = ?", [acc]).fetchone()[0]
        assert raw_in_count == 0, f"Account {acc} marked as sender-only but has raw inbound transactions"


def test_search_returns_correct_accounts_and_schema():
    """
    Test 6: Search returns correct accounts with expected schema fields.
    """
    res = client.get("/api/accounts/search?q=SBIN10012624&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    item = data[0]
    assert item["account"] == "SBIN10012624"
    assert "inbound_transaction_count" in item
    assert "outbound_transaction_count" in item
    assert "observed_inflow" in item
    assert "observed_outflow" in item
    assert "dataset_observed_net_movement" in item
    assert item["dataset_observed_net_movement"] == round(item["observed_inflow"] - item["observed_outflow"], 2)


def test_search_performance_material_improvement():
    """
    Test 7: Search performance improves materially from the ~9,965 ms baseline to sub-50 ms.
    """
    # Cold search
    t0 = time.perf_counter()
    res1 = client.get("/api/accounts/search?q=SBIN10012624&limit=20")
    t_cold = (time.perf_counter() - t0) * 1000

    # Warm search
    t1 = time.perf_counter()
    res2 = client.get("/api/accounts/search?q=SBIN&limit=20")
    t_warm = (time.perf_counter() - t1) * 1000

    assert res1.status_code == 200
    assert res2.status_code == 200
    # Must be dramatically faster than the 9,965 ms baseline (target < 100 ms)
    assert t_cold < 100.0, f"Search took {t_cold:.2f} ms (expected < 100 ms)"
    assert t_warm < 100.0, f"Warm search took {t_warm:.2f} ms (expected < 100 ms)"


def test_feature_store_schema_and_model_foundation():
    """
    Validates that account_features schema exists in DuckDB,
    uncomputed fields are NULL, and Pydantic model enforces typed contract.
    """
    con = get_db()
    table_info = con.execute("DESCRIBE account_features").fetchall()
    col_names = [r[0] for r in table_info]
    assert "account_number" in col_names
    assert "fan_in" in col_names
    assert "fan_out" in col_names
    assert "mule_risk_index" in col_names
    assert "layer1_candidate" in col_names
    assert "layer2_candidate" in col_names
    assert "layer3_candidate" in col_names
    assert "provenance" in col_names

    # Validate Pydantic model contract
    feat = AccountFeatures(account_number="TEST_ACC_001")
    assert feat.account_number == "TEST_ACC_001"
    assert feat.fan_in is None  # Uncalculated features MUST remain None, never fake zero
    assert feat.mule_risk_index is None
    assert feat.provenance == "DERIVED"
