"""
Step 6: Blind Victim Investigation Engine & Workspace Tests
Operation 'ABHEDYA-CHAKRA'
Comprehensive verification of multi-hop blind victim fund-flow tracing,
provenance preservation, zero-fabrication invariants, role & risk integration,
terminal node identification, and deterministic execution.
"""

import pytest
from datetime import datetime, timedelta
import duckdb
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db
from backend.attribution.config import AttributionPolicyConfig
from backend.attribution.engine import trace_fifo_attribution_4hop
from backend.investigations.models import (
    VictimInvestigationResponse,
    DataProvenance,
    VictimAccountSummary,
    VictimRolesSummary,
    VictimVelocitySummary,
    TerminalAccountEvidence,
)
from backend.investigations.orchestrator import investigate_victim_account

client = TestClient(app)


def _make_mem_investigation_db(rows):
    """Creates a temporary in-memory DuckDB instance with transactions, accounts_dimension, and account_features."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE transactions (
            Transaction_ID VARCHAR,
            Sender_Account VARCHAR,
            Receiver_Account VARCHAR,
            Sender_IFSC VARCHAR,
            Receiver_IFSC VARCHAR,
            Amount DOUBLE,
            Timestamp TIMESTAMP,
            Payment_Mode VARCHAR,
            Narration VARCHAR,
            IP_Address VARCHAR,
            Device_Type VARCHAR
        );
    """)
    for r in rows:
        con.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", r)

    # Build accounts_dimension
    con.execute("""
        CREATE TABLE accounts_dimension AS
        WITH entity_tx AS (
            SELECT Sender_Account AS acc, Receiver_Account AS cp, Sender_IFSC AS ifsc, IP_Address AS ip, Device_Type AS dev, Payment_Mode AS pm, Timestamp AS ts, Amount AS amt, 1 AS is_out, 0 AS is_in FROM transactions
            UNION ALL
            SELECT Receiver_Account AS acc, Sender_Account AS cp, Receiver_IFSC AS ifsc, IP_Address AS ip, Device_Type AS dev, Payment_Mode AS pm, Timestamp AS ts, Amount AS amt, 0 AS is_out, 1 AS is_in FROM transactions
        )
        SELECT 
            acc AS account_number,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS total_inflow,
            ROUND(COALESCE(SUM(CASE WHEN is_out = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS total_outflow,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE -amt END), 0.0), 2) AS net_flow_delta,
            CAST(SUM(is_in) AS BIGINT) AS incoming_txn_count,
            CAST(SUM(is_out) AS BIGINT) AS outgoing_txn_count,
            CAST(COUNT(*) AS BIGINT) AS transaction_count,
            CAST(COUNT(DISTINCT CASE WHEN is_in = 1 THEN cp END) AS BIGINT) AS unique_senders,
            CAST(COUNT(DISTINCT CASE WHEN is_out = 1 THEN cp END) AS BIGINT) AS unique_receivers,
            CAST(COUNT(DISTINCT cp) AS BIGINT) AS counterparty_count,
            MIN(ts) AS first_seen_timestamp,
            MAX(ts) AS last_seen_timestamp,
            CAST(COUNT(DISTINCT CASE WHEN is_out = 1 THEN ifsc END) AS BIGINT) AS sender_ifsc_count,
            CAST(COUNT(DISTINCT CASE WHEN is_in = 1 THEN ifsc END) AS BIGINT) AS receiver_ifsc_count,
            CAST(COUNT(DISTINCT ip) AS BIGINT) AS unique_ip_count,
            CAST(COUNT(DISTINCT dev) AS BIGINT) AS unique_device_count,
            CAST(COUNT(DISTINCT pm) AS BIGINT) AS unique_payment_mode_count,
            'DERIVED' AS provenance
        FROM entity_tx
        GROUP BY acc;
    """)

    # Build account_features table
    con.execute("""
        CREATE TABLE account_features AS
        SELECT 
            account_number,
            incoming_txn_count,
            outgoing_txn_count,
            total_inflow AS incoming_volume,
            total_outflow AS outgoing_volume,
            net_flow_delta,
            unique_senders AS fan_in,
            unique_receivers AS fan_out,
            counterparty_count AS unique_counterparties,
            NULL::DOUBLE AS pass_through_ratio,
            NULL::BIGINT AS pass_through_event_count,
            NULL::DOUBLE AS median_incoming_to_outgoing_seconds,
            NULL::BIGINT AS rapid_outflow_count,
            FALSE AS pass_through_candidate,
            NULL::DOUBLE AS pass_through_incoming_volume,
            NULL::DOUBLE AS pass_through_attributed_volume,
            NULL::BIGINT AS pass_through_outgoing_transaction_count,
            FALSE AS layer1_candidate,
            FALSE AS layer2_candidate,
            FALSE AS layer3_candidate,
            '[]' AS layer1_reasons,
            '[]' AS layer2_reasons,
            '[]' AS layer3_reasons,
            0 AS layer1_signal_count,
            0 AS layer2_signal_count,
            0 AS layer3_signal_count,
            25.0 AS mule_risk_index,
            'MODERATE' AS risk_band,
            '[]' AS risk_reasons,
            '{}' AS risk_family_scores,
            'v1' AS risk_model_version,
            NULL::TIMESTAMP AS risk_computed_at,
            'DERIVED' AS risk_provenance,
            NULL::VARCHAR AS risk_factors,
            FALSE AS cycle_indicator
        FROM accounts_dimension;
    """)
    return con


# ==============================================================================
# TEST 1: Valid arbitrary account investigation structure
# ==============================================================================
def test_victim_investigation_arbitrary_valid_account():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_V_1", "VICTIM_ACC", "MULE_B", "IFSC_V", "IFSC_B", 50000.0, base, "UPI", "stolen funds", "1.1.1.1", "Mobile"),
        ("TX_B_C", "MULE_B", "MULE_C", "IFSC_B", "IFSC_C", 40000.0, base + timedelta(minutes=5), "IMPS", "layering", "2.2.2.2", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "VICTIM_ACC")

    assert isinstance(res, VictimInvestigationResponse)
    assert res.account_number == "VICTIM_ACC"
    assert res.status == "COMPLETED"
    assert res.investigation_id.startswith("INV-VICTIM_ACC-")
    assert res.account_summary.observed_outgoing_volume == 50000.0
    assert len(res.victim_transactions) == 1
    assert res.victim_transactions[0].transaction_id == "TX_V_1"
    assert res.trace.total_hops_found == 2
    assert len(res.terminals) >= 1
    assert res.terminals[0].account_number == "MULE_C"
    assert res.terminals[0].attributed_amount == 40000.0


# ==============================================================================
# TEST 2: Account not found error handling
# ==============================================================================
def test_victim_investigation_account_not_found():
    con = _make_mem_investigation_db([])
    with pytest.raises(ValueError, match="Account 'NON_EXISTENT_ACC_9999' not found"):
        investigate_victim_account(con, "NON_EXISTENT_ACC_9999")


# ==============================================================================
# TEST 3: Valid account with no downstream outgoing attribution
# ==============================================================================
def test_victim_investigation_no_downstream_attribution():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        # Only incoming funds to subject, no outgoing
        ("TX_IN_1", "SENDER_X", "VICTIM_NO_OUT", "IFSC_X", "IFSC_V", 10000.0, base, "UPI", "deposit", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "VICTIM_NO_OUT")

    assert res.status == "NO_QUALIFYING_OUTFLOW"
    assert res.trace.total_hops_found == 0
    assert len(res.trace.edges) == 0
    assert len(res.terminals) == 0
    assert any("No qualifying downstream temporal attribution" in w for w in res.warnings)


# ==============================================================================
# TEST 4: Victim transaction retrieval with genuine non-null fields
# ==============================================================================
def test_victim_transaction_retrieval():
    base = datetime(2025, 1, 1, 12, 0, 0)
    rows = [
        ("TX_TEST_1", "VICTIM_TX_ACC", "DEST_1", "IFSC_1", "IFSC_2", 1500.0, base, "NEFT", "fraud debit", "10.0.0.1", "Desktop"),
        ("TX_TEST_2", "SENDER_2", "VICTIM_TX_ACC", "IFSC_3", "IFSC_1", 2000.0, base - timedelta(hours=1), "UPI", "salary", "10.0.0.2", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "VICTIM_TX_ACC")

    assert len(res.victim_transactions) == 2
    tx_out = [t for t in res.victim_transactions if t.direction == "OUTGOING"][0]
    assert tx_out.transaction_id == "TX_TEST_1"
    assert tx_out.amount == 1500.0
    assert tx_out.sender_ifsc == "IFSC_1"
    assert tx_out.receiver_ifsc == "IFSC_2"
    assert tx_out.ip_address == "10.0.0.1"
    assert tx_out.device_type == "Desktop"
    assert tx_out.provenance == "RAW"


# ==============================================================================
# TEST 5: Mule risk integration (0-100 bounded)
# ==============================================================================
def test_victim_risk_integration():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX_1", "ACC_RISK", "DEST", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ACC_RISK")

    assert res.risk is not None
    assert 0.0 <= res.risk.risk_index <= 100.0
    assert res.risk.risk_band in ("LOW", "MODERATE", "HIGH", "VERY_HIGH")
    assert res.risk.risk_model_version == "v1"
    assert res.risk.risk_provenance == "DERIVED"


# ==============================================================================
# TEST 6: Mule role integration (Step 4 classes)
# ==============================================================================
def test_victim_role_integration():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX_1", "ACC_ROLE", "DEST", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ACC_ROLE")

    assert isinstance(res.roles, VictimRolesSummary)
    assert res.roles.primary_role_label in (
        "L1 Collector Candidate",
        "L2 Distributor Candidate",
        "L3 Terminal Candidate",
        "Originating Account / Standard Entity",
        "Standard Account / Unclassified",
    )
    assert res.roles.provenance == "DERIVED"


# ==============================================================================
# TEST 7: Velocity integration (Step 5A 3-15 min window)
# ==============================================================================
def test_victim_velocity_integration():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX_1", "ACC_VEL", "DEST", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ACC_VEL")

    assert isinstance(res.velocity, VictimVelocitySummary)
    assert res.velocity.window_description == "3_TO_15_MINUTES"
    assert res.velocity.classification_version == "v1"
    assert res.velocity.provenance == "DERIVED"


# ==============================================================================
# TEST 8: 4-Hop Provenance Trace integration
# ==============================================================================
def test_victim_trace_integration():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_A", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 900.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "D", "IFSC", "IFSC", 800.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
        ("T4", "D", "E", "IFSC", "IFSC", 700.0, base + timedelta(minutes=15), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_A", max_hops=4)

    assert res.trace.total_hops_found == 4
    assert len(res.trace.edges) == 4
    assert res.trace.edges[0].edge_type == "ROOT_SEED"
    assert all(e.edge_type == "FIFO_ATTRIBUTION" for e in res.trace.edges[1:])


# ==============================================================================
# TEST 9: Hop limit parameter enforcement (max_hops=2 vs 4)
# ==============================================================================
def test_victim_hop_limit_enforced():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_HOP", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 900.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "D", "IFSC", "IFSC", 800.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res_2hops = investigate_victim_account(con, "ROOT_HOP", max_hops=2)
    assert res_2hops.trace.total_hops_found == 2
    assert max(e.hop_number for e in res_2hops.trace.edges) == 2


# ==============================================================================
# TEST 10: Propagation amount correctness (Victim -> B 1000, B -> C 600 -> C gets 600)
# ==============================================================================
def test_victim_propagation_amount_correctness():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_PROP", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "D", "IFSC", "IFSC", 800.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_PROP", max_hops=3)

    # Hop 1: 1000
    # Hop 2: 600
    # Hop 3: C can only attribute up to 600 (not 800)
    h3_edge = [e for e in res.trace.edges if e.hop_number == 3][0]
    assert h3_edge.attributed_amount == 600.0


# ==============================================================================
# TEST 11: ROOT_SEED edge distinction
# ==============================================================================
def test_victim_root_seed_edge_distinction():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_SEED_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 500.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_SEED_ACC", max_hops=2)

    h1_edges = [e for e in res.trace.edges if e.hop_number == 1]
    assert len(h1_edges) == 1
    assert h1_edges[0].edge_type == "ROOT_SEED"


# ==============================================================================
# TEST 12: FIFO_ATTRIBUTION edge distinction
# ==============================================================================
def test_victim_fifo_attribution_edge_distinction():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_FIFO_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 500.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_FIFO_ACC", max_hops=2)

    h2_edges = [e for e in res.trace.edges if e.hop_number == 2]
    assert len(h2_edges) == 1
    assert h2_edges[0].edge_type == "FIFO_ATTRIBUTION"


# ==============================================================================
# TEST 13: Truncation warning propagation
# ==============================================================================
def test_victim_truncation_warning_propagation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = []
    # 51 outgoing from root
    for i in range(51):
        rows.append((f"T_{i}", "ROOT_TRUNC", f"DEST_{i}", "IFSC", "IFSC", 100.0, base + timedelta(minutes=i), "UPI", "", "1.1.1.1", "Mobile"))
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_TRUNC", max_branches_per_hop=50)

    assert res.trace.truncated is True
    assert res.trace.truncation_reason == "ROOT_OUTGOING_BRANCH_LIMIT"
    assert any("Trace branch expansion limit reached" in w for w in res.warnings)


# ==============================================================================
# TEST 14: Cycle warning propagation
# ==============================================================================
def test_victim_cycle_warning_propagation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    # A -> B -> C -> B (cycle)
    rows = [
        ("T1", "ROOT_CYCLE", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 900.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "B", "IFSC", "IFSC", 800.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_CYCLE", max_hops=4)

    assert len(res.trace.cycles_detected) >= 1
    assert any("Path cycles detected" in w for w in res.warnings)


# ==============================================================================
# TEST 15: Provenance presence in all tiers
# ==============================================================================
def test_victim_provenance_presence():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "ROOT_PROV", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_PROV")

    assert res.data_provenance.dataset_sha256 == "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    assert res.account_summary.account_provenance == "ANALYTICAL"
    assert res.roles.provenance == "DERIVED"
    assert res.velocity.provenance == "DERIVED"
    assert res.trace.provenance == "ATTRIBUTION"
    if res.victim_transactions:
        assert res.victim_transactions[0].provenance == "RAW"


# ==============================================================================
# TEST 16: Zero fabricated evidence
# ==============================================================================
def test_victim_no_fabricated_evidence():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_REAL_123", "ACC_REAL", "RECV_REAL", "IFSC1", "IFSC2", 777.77, base, "UPI", "real narration", "192.168.1.1", "Mobile")
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ACC_REAL")

    # The returned transaction must match the input row exactly
    tx = res.victim_transactions[0]
    assert tx.transaction_id == "TX_REAL_123"
    assert tx.sender_account == "ACC_REAL"
    assert tx.receiver_account == "RECV_REAL"
    assert tx.amount == 777.77
    assert tx.payment_mode == "UPI"
    assert tx.narration == "real narration"
    assert tx.ip_address == "192.168.1.1"


# ==============================================================================
# TEST 17: Deterministic investigation results on repeated runs
# ==============================================================================
def test_victim_deterministic_investigation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "DET_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res1 = investigate_victim_account(con, "DET_ACC")
    res2 = investigate_victim_account(con, "DET_ACC")

    assert res1.investigation_id == res2.investigation_id
    assert res1.account_number == res2.account_number
    assert res1.trace.total_attributed_amount == res2.trace.total_attributed_amount
    assert len(res1.trace.edges) == len(res2.trace.edges)
    assert len(res1.terminals) == len(res2.terminals)
    assert res1.evidence_summary.observed_activity == res2.evidence_summary.observed_activity


# ==============================================================================
# TEST 18: Malformed account ID handling
# ==============================================================================
def test_victim_malformed_account_id():
    con = _make_mem_investigation_db([])
    with pytest.raises(ValueError):
        investigate_victim_account(con, "   ")


# ==============================================================================
# TEST 19: Terminal accounts identification
# ==============================================================================
def test_victim_terminal_accounts_identification():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_TERM", "MULE_MID", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "MULE_MID", "TERM_1", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "MULE_MID", "TERM_2", "IFSC", "IFSC", 400.0, base + timedelta(minutes=6), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_investigation_db(rows)
    res = investigate_victim_account(con, "ROOT_TERM", max_hops=3)

    assert len(res.terminals) == 2
    term_accs = {t.account_number for t in res.terminals}
    assert term_accs == {"TERM_1", "TERM_2"}
    assert "MULE_MID" not in term_accs  # Mid forwarded funds, so it is not terminal


# ==============================================================================
# TEST 20: FastAPI TestClient live API endpoint verification
# ==============================================================================
def test_victim_live_api_endpoint():
    # Test valid account endpoint on known account
    res = client.get("/api/investigations/victim/KKBK10000402?max_hops=4")
    assert res.status_code == 200
    data = res.json()
    assert data["account_number"] == "KKBK10000402"
    assert data["status"] == "COMPLETED"
    assert "investigation_id" in data
    assert "account_summary" in data
    assert "risk" in data
    assert "roles" in data
    assert "velocity" in data
    assert "trace" in data
    assert "terminals" in data
    assert "evidence_summary" in data

    # Test 404 on non-existent account
    res_404 = client.get("/api/investigations/victim/NON_EXISTENT_ACC_00000")
    assert res_404.status_code == 404
