"""
Test Suite for Forensic Role Classifier Engine (Step 4)
Operation 'ABHEDYA-CHAKRA'

Validates:
1. Complete 24,873 entity coverage (deterministic true/false, zero NULLs for candidates)
2. Layer 1 multi-signal logic (high fan-in, insufficient fan-in, single-signal exclusion)
3. Layer 2 multi-signal logic (high fan-out, insufficient fan-out, single-signal exclusion)
4. Layer 3 multi-signal logic (supported terminal sinks, automated egress, automation-alone exclusion)
5. Multiple concurrent candidate roles (no artificial mutual exclusivity)
6. Explainability contract (stable codes, observed values, thresholds, factual descriptions)
7. Deterministic reproducibility across multiple runs
8. Production dataset preservation (2,000,000 rows, 2,252 duplicate TxIDs, 24,873 accounts)
"""

import json
import pytest
import duckdb
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db
from backend.detection.thresholds import (
    RoleClassificationThresholds,
    Layer1Thresholds,
    Layer2Thresholds,
    Layer3Thresholds,
    DEFAULT_THRESHOLDS,
)
from backend.detection.role_classifier import classify_account_roles
from backend.features.models import AccountFeatures, CandidateReason
from backend.features.behavioral import get_account_features, compute_account_features

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Dataset Coverage & Candidate Semantics
# ---------------------------------------------------------------------------
def test_all_accounts_receive_deterministic_candidate_flags():
    """
    Validates that every single account entity (24,873) in account_features
    receives deterministic true/false values for all 3 candidate layers (ZERO NULLs).
    """
    con = get_db()
    total_count = con.execute("SELECT COUNT(*) FROM account_features").fetchone()[0]
    assert total_count == 24873

    # Check for any NULL candidates (must be 0)
    null_counts = con.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE layer1_candidate IS NULL) AS l1_nulls,
            COUNT(*) FILTER (WHERE layer2_candidate IS NULL) AS l2_nulls,
            COUNT(*) FILTER (WHERE layer3_candidate IS NULL) AS l3_nulls
        FROM account_features;
    """).fetchone()

    assert null_counts[0] == 0, "layer1_candidate contains NULL values"
    assert null_counts[1] == 0, "layer2_candidate contains NULL values"
    assert null_counts[2] == 0, "layer3_candidate contains NULL values"


# ---------------------------------------------------------------------------
# 2. Layer 1 Collector Candidate Logic & Single-Signal Exclusion
# ---------------------------------------------------------------------------
def test_layer1_collector_multi_signal_logic():
    """
    Tests Layer 1 candidate logic using an in-memory fixture:
    - High fan-in + high count + high volume + dominance triggers candidate.
    - High fan-in ALONE (with low volume) must NOT trigger candidate.
    - High volume ALONE (with low fan-in) must NOT trigger candidate.
    """
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("""
        CREATE TABLE account_features (
            account_number VARCHAR,
            fan_in BIGINT,
            fan_out BIGINT,
            incoming_txn_count BIGINT,
            outgoing_txn_count BIGINT,
            incoming_volume DOUBLE,
            outgoing_volume DOUBLE,
            net_flow_delta DOUBLE,
            inflow_to_outflow_ratio DOUBLE,
            outflow_to_inflow_ratio DOUBLE,
            web_emulator_txn_count BIGINT,
            linux_script_txn_count BIGINT,
            top_ip_transaction_ratio DOUBLE,
            top_ip_transaction_count BIGINT
        );
    """)

    # Row 1: Valid Layer 1 (fan_in=100, in_tx=100, in_vol=200k, net_flow_delta=50k, fan_in > fan_out)
    # Row 2: High fan_in alone (fan_in=100, in_tx=100, in_vol=1000.0 [below 150k threshold])
    # Row 3: High volume alone (in_vol=300k, but fan_in=2, in_tx=2 [below 95 threshold])
    # Row 4: Low activity baseline
    mem_con.execute("""
        INSERT INTO account_features VALUES
        ('ACC_L1_VALID', 100, 50, 100, 50, 200000.0, 50000.0, 150000.0, 4.0, 0.25, 0, 0, 0.05, 5),
        ('ACC_L1_FAN_IN_ONLY', 100, 50, 100, 50, 1000.0, 500.0, 500.0, 2.0, 0.5, 0, 0, 0.05, 5),
        ('ACC_L1_VOL_ONLY', 2, 2, 2, 2, 300000.0, 50000.0, 250000.0, 6.0, 0.16, 0, 0, 0.05, 1),
        ('ACC_NORMAL', 10, 10, 10, 10, 15000.0, 15000.0, 0.0, 1.0, 1.0, 0, 0, 0.05, 1);
    """)

    classify_account_roles(mem_con, DEFAULT_THRESHOLDS)

    res = mem_con.execute("""
        SELECT account_number, layer1_candidate, layer1_signal_count, layer1_reasons
        FROM account_features ORDER BY account_number;
    """).fetchall()

    results = {r[0]: (r[1], r[2], json.loads(r[3])) for r in res}

    # ACC_L1_VALID must be candidate with structured reasons
    is_cand, sig_cnt, reasons = results["ACC_L1_VALID"]
    assert is_cand is True
    assert sig_cnt >= 3
    assert len(reasons) >= 3
    reason_codes = [r["code"] for r in reasons]
    assert "HIGH_FAN_IN" in reason_codes
    assert "HIGH_INBOUND_TRANSACTION_COUNT" in reason_codes
    assert "HIGH_INBOUND_VOLUME" in reason_codes

    # ACC_L1_FAN_IN_ONLY must NOT trigger (insufficient volume)
    is_cand, sig_cnt, _ = results["ACC_L1_FAN_IN_ONLY"]
    assert is_cand is False
    assert sig_cnt == 0

    # ACC_L1_VOL_ONLY must NOT trigger (insufficient fan-in)
    is_cand, sig_cnt, _ = results["ACC_L1_VOL_ONLY"]
    assert is_cand is False
    assert sig_cnt == 0

    # Normal account must not trigger
    assert results["ACC_NORMAL"][0] is False


# ---------------------------------------------------------------------------
# 3. Layer 2 Distributor Candidate Logic & Single-Signal Exclusion
# ---------------------------------------------------------------------------
def test_layer2_distributor_multi_signal_logic():
    """
    Tests Layer 2 candidate logic using an in-memory fixture:
    - High fan-out + high count + high volume + dominance triggers candidate.
    - High fan-out ALONE (low volume) must NOT trigger candidate.
    - High volume ALONE (low fan-out) must NOT trigger candidate.
    """
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("""
        CREATE TABLE account_features (
            account_number VARCHAR,
            fan_in BIGINT,
            fan_out BIGINT,
            incoming_txn_count BIGINT,
            outgoing_txn_count BIGINT,
            incoming_volume DOUBLE,
            outgoing_volume DOUBLE,
            net_flow_delta DOUBLE,
            inflow_to_outflow_ratio DOUBLE,
            outflow_to_inflow_ratio DOUBLE,
            web_emulator_txn_count BIGINT,
            linux_script_txn_count BIGINT,
            top_ip_transaction_ratio DOUBLE,
            top_ip_transaction_count BIGINT
        );
    """)

    mem_con.execute("""
        INSERT INTO account_features VALUES
        ('ACC_L2_VALID', 40, 105, 40, 105, 50000.0, 220000.0, -170000.0, 0.22, 4.4, 0, 0, 0.05, 5),
        ('ACC_L2_FAN_OUT_ONLY', 40, 105, 40, 105, 500.0, 1200.0, -700.0, 0.41, 2.4, 0, 0, 0.05, 5),
        ('ACC_L2_VOL_ONLY', 1, 1, 1, 1, 10000.0, 500000.0, -490000.0, 0.02, 50.0, 0, 0, 0.05, 1);
    """)

    classify_account_roles(mem_con, DEFAULT_THRESHOLDS)

    res = mem_con.execute("""
        SELECT account_number, layer2_candidate, layer2_signal_count, layer2_reasons
        FROM account_features ORDER BY account_number;
    """).fetchall()

    results = {r[0]: (r[1], r[2], json.loads(r[3])) for r in res}

    # ACC_L2_VALID must be candidate
    is_cand, sig_cnt, reasons = results["ACC_L2_VALID"]
    assert is_cand is True
    assert sig_cnt >= 3
    reason_codes = [r["code"] for r in reasons]
    assert "HIGH_FAN_OUT" in reason_codes
    assert "HIGH_OUTBOUND_TRANSACTION_COUNT" in reason_codes
    assert "HIGH_OUTBOUND_VOLUME" in reason_codes

    # ACC_L2_FAN_OUT_ONLY must NOT trigger
    assert results["ACC_L2_FAN_OUT_ONLY"][0] is False

    # ACC_L2_VOL_ONLY must NOT trigger
    assert results["ACC_L2_VOL_ONLY"][0] is False


# ---------------------------------------------------------------------------
# 4. Layer 3 Terminal Node Logic & Automation-Alone Exclusion
# ---------------------------------------------------------------------------
def test_layer3_terminal_candidate_logic():
    """
    Tests Layer 3 candidate logic:
    - Mode A: Terminal accumulation sink (high inbound, zero outbound) triggers.
    - Mode B: Automated outflow drain (automation + high outbound volume + dominance) triggers.
    - Automation ALONE (without significant outbound volume) must NOT trigger.
    - High outbound volume without automation or terminal sink must NOT trigger Layer 3.
    """
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("""
        CREATE TABLE account_features (
            account_number VARCHAR,
            fan_in BIGINT,
            fan_out BIGINT,
            incoming_txn_count BIGINT,
            outgoing_txn_count BIGINT,
            incoming_volume DOUBLE,
            outgoing_volume DOUBLE,
            net_flow_delta DOUBLE,
            inflow_to_outflow_ratio DOUBLE,
            outflow_to_inflow_ratio DOUBLE,
            web_emulator_txn_count BIGINT,
            linux_script_txn_count BIGINT,
            top_ip_transaction_ratio DOUBLE,
            top_ip_transaction_count BIGINT
        );
    """)

    mem_con.execute("""
        INSERT INTO account_features VALUES
        -- Mode A: Pure Terminal Sink (Inflow=150k, InTx=4, OutTx=0)
        ('ACC_L3_SINK', 4, 0, 4, 0, 150000.0, 0.0, 150000.0, NULL, 0.0, 0, 0, 0.25, 1),
        -- Mode B: Automated Cash-Out (Web_Emulator=3, OutVol=180k, OutTx=3 >= InTx=1)
        ('ACC_L3_AUTO', 1, 3, 1, 3, 15000.0, 180000.0, -165000.0, 0.08, 12.0, 3, 0, 0.33, 1),
        -- Automation Alone (Web_Emulator=2, but OutVol=500, normal traffic) -> MUST NOT TRIGGER
        ('ACC_AUTO_ALONE', 2, 2, 2, 2, 5000.0, 500.0, 4500.0, 10.0, 0.1, 2, 0, 0.25, 1),
        -- High Outbound Volume Alone (OutVol=200k, but Windows Browser, no sink, no emulator) -> MUST NOT TRIGGER L3
        ('ACC_OUT_NORMAL', 5, 5, 5, 5, 190000.0, 200000.0, -10000.0, 0.95, 1.05, 0, 0, 0.05, 1);
    """)

    classify_account_roles(mem_con, DEFAULT_THRESHOLDS)

    res = mem_con.execute("""
        SELECT account_number, layer3_candidate, layer3_signal_count, layer3_reasons
        FROM account_features ORDER BY account_number;
    """).fetchall()

    results = {r[0]: (r[1], r[2], json.loads(r[3])) for r in res}

    # Sink candidate
    is_cand, _, reasons = results["ACC_L3_SINK"]
    assert is_cand is True
    reason_codes = [r["code"] for r in reasons]
    assert "TERMINAL_FLOW_SINK" in reason_codes
    assert "ZERO_OUTBOUND_DISBURSEMENT" in reason_codes

    # Automated cashout candidate
    is_cand, _, reasons = results["ACC_L3_AUTO"]
    assert is_cand is True
    reason_codes = [r["code"] for r in reasons]
    assert "AUTOMATION_DEVICE_ACTIVITY" in reason_codes
    assert "HIGH_OUTBOUND_DISBURSEMENT" in reason_codes

    # Automation ALONE must NOT trigger Layer 3
    assert results["ACC_AUTO_ALONE"][0] is False
    assert results["ACC_AUTO_ALONE"][1] == 0

    # Normal high-volume outflow without terminal conditions must NOT trigger Layer 3
    assert results["ACC_OUT_NORMAL"][0] is False


# ---------------------------------------------------------------------------
# 5. Multiple Roles (Simultaneous L1 + L2 Candidates)
# ---------------------------------------------------------------------------
def test_simultaneous_multi_role_candidacy():
    """
    Verifies that the architecture supports accounts that simultaneously satisfy
    both Layer 1 (aggregation) and Layer 2 (distribution) candidate roles
    without enforcing artificial mutual exclusivity.
    """
    mem_con = duckdb.connect(":memory:")
    mem_con.execute("""
        CREATE TABLE account_features (
            account_number VARCHAR,
            fan_in BIGINT,
            fan_out BIGINT,
            incoming_txn_count BIGINT,
            outgoing_txn_count BIGINT,
            incoming_volume DOUBLE,
            outgoing_volume DOUBLE,
            net_flow_delta DOUBLE,
            inflow_to_outflow_ratio DOUBLE,
            outflow_to_inflow_ratio DOUBLE,
            web_emulator_txn_count BIGINT,
            linux_script_txn_count BIGINT,
            top_ip_transaction_ratio DOUBLE,
            top_ip_transaction_count BIGINT
        );
    """)

    # Account with very high inflow AND very high outflow (pass-through / hub)
    mem_con.execute("""
        INSERT INTO account_features VALUES
        ('ACC_L1_AND_L2', 110, 115, 110, 115, 250000.0, 260000.0, -10000.0, 0.96, 1.04, 0, 0, 0.05, 5);
    """)

    classify_account_roles(mem_con, DEFAULT_THRESHOLDS)

    row = mem_con.execute("""
        SELECT layer1_candidate, layer2_candidate, layer3_candidate,
               layer1_signal_count, layer2_signal_count
        FROM account_features WHERE account_number = 'ACC_L1_AND_L2';
    """).fetchone()

    assert row[0] is True, "Expected Layer 1 candidacy"
    assert row[1] is True, "Expected Layer 2 candidacy"
    assert row[2] is False, "Did not expect Layer 3 candidacy"
    assert row[3] >= 3
    assert row[4] >= 3


# ---------------------------------------------------------------------------
# 6. Structured Evidence & Explainability
# ---------------------------------------------------------------------------
def test_structured_reason_contracts():
    """
    Validates that every reason object produced adheres to the typed CandidateReason contract:
    - Stable uppercase reason code
    - Observed value present
    - Configured threshold reference present
    - Factual non-assertive description
    """
    con = get_db()
    # Check sample candidate from production
    cand = con.execute("""
        SELECT layer1_reasons, layer2_reasons, layer3_reasons
        FROM account_features
        WHERE layer1_candidate = true OR layer2_candidate = true OR layer3_candidate = true
        LIMIT 10;
    """).fetchall()

    for l1_r, l2_r, l3_r in cand:
        for r_json in [l1_r, l2_r, l3_r]:
            reasons = json.loads(r_json)
            for r in reasons:
                parsed = CandidateReason(**r)
                assert parsed.code.isupper()
                assert parsed.observed_value is not None
                assert len(parsed.description) > 5
                # Prohibited subjective / speculative phrases
                assert "ai" not in parsed.description.lower()
                assert "criminal" not in parsed.description.lower()
                assert "guilty" not in parsed.description.lower()


# ---------------------------------------------------------------------------
# 7. Determinism & Idempotency
# ---------------------------------------------------------------------------
def test_classification_determinism_and_reproducibility():
    """
    Validates that re-running classification on the exact same dataset
    produces bitwise identical candidate flags, signal counts, and reason strings.
    """
    con = get_db()
    
    # Snapshot 1
    snap1 = con.execute("""
        SELECT account_number, layer1_candidate, layer2_candidate, layer3_candidate,
               layer1_reasons, layer2_reasons, layer3_reasons,
               layer1_signal_count, layer2_signal_count, layer3_signal_count
        FROM account_features
        ORDER BY account_number;
    """).fetchall()

    # Re-run classification
    classify_account_roles(con, DEFAULT_THRESHOLDS)

    # Snapshot 2
    snap2 = con.execute("""
        SELECT account_number, layer1_candidate, layer2_candidate, layer3_candidate,
               layer1_reasons, layer2_reasons, layer3_reasons,
               layer1_signal_count, layer2_signal_count, layer3_signal_count
        FROM account_features
        ORDER BY account_number;
    """).fetchall()

    assert snap1 == snap2, "Classification results must be perfectly deterministic"


# ---------------------------------------------------------------------------
# 8. Production Dataset Integrity & Preservation
# ---------------------------------------------------------------------------
def test_production_dataset_preservation():
    """
    Verifies that the underlying production dataset and dimensions remain intact:
    - 2,000,000 raw transaction rows
    - 2,252 duplicate Transaction_ID rows
    - 24,873 unique account entities
    """
    con = get_db()
    tx_count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert tx_count == 2000000

    dup_count = con.execute("""
        SELECT SUM(cnt - 1) FROM (
            SELECT Transaction_ID, COUNT(*) as cnt FROM transactions GROUP BY Transaction_ID HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert dup_count == 2252

    dim_count = con.execute("SELECT COUNT(*) FROM accounts_dimension").fetchone()[0]
    assert dim_count == 24873

    feat_count = con.execute("SELECT COUNT(*) FROM account_features").fetchone()[0]
    assert feat_count == 24873


# ---------------------------------------------------------------------------
# 9. API Features Endpoint Contract
# ---------------------------------------------------------------------------
def test_api_features_endpoint_step4_contract():
    """
    Tests GET /api/accounts/{account_id}/features for candidate role serialization.
    """
    con = get_db()
    
    # Pick known L1 candidate
    l1_acc = con.execute("SELECT account_number FROM account_features WHERE layer1_candidate = true LIMIT 1").fetchone()[0]
    res = client.get(f"/api/accounts/{l1_acc}/features")
    assert res.status_code == 200
    data = res.json()
    assert data["account_number"] == l1_acc
    assert data["layer1_candidate"] is True
    assert isinstance(data["layer1_reasons"], list)
    assert len(data["layer1_reasons"]) > 0
    assert data["classification_version"] == "v1"
    assert data["classification_provenance"] == "CANDIDATE_CLASSIFICATION"

    # Pick known non-candidate account
    no_role_acc = con.execute("""
        SELECT account_number FROM account_features 
        WHERE NOT layer1_candidate AND NOT layer2_candidate AND NOT layer3_candidate
        LIMIT 1;
    """).fetchone()[0]
    res_no = client.get(f"/api/accounts/{no_role_acc}/features")
    assert res_no.status_code == 200
    data_no = res_no.json()
    assert data_no["layer1_candidate"] is False
    assert data_no["layer2_candidate"] is False
    assert data_no["layer3_candidate"] is False
    assert data_no["layer1_reasons"] == []
    assert data_no["layer2_reasons"] == []
    assert data_no["layer3_reasons"] == []
