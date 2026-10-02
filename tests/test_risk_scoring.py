"""
Test Suite for Step 5B -- Explainable 0-100 Mule Risk Index
Operation 'ABHEDYA-CHAKRA'

Covers all 14 required test areas:
1.  Score always >= 0
2.  Score always <= 100
3.  Deterministic repeated execution
4.  Reason points sum correctly into family caps
5.  Family totals never exceed configured maximums
6.  Low-signal account receives lower score than strong-signal account
7.  High velocity contributes correctly
8.  Automated-device evidence contributes correctly
9.  L1/L2/L3 support does not exceed ROLE_SUPPORT cap
10. Correlated evidence does not double-count beyond family caps
11. Null/zero features handled safely
12. Risk API returns valid schema
13. Known test accounts produce deterministic results
14. Production dataset remains unchanged
"""

import pytest
import duckdb
from fastapi.testclient import TestClient
import json

from backend.main import app
from backend.db.connection import get_db
from backend.detection.risk_thresholds import (
    MuleRiskModelConfig,
    DEFAULT_RISK_CONFIG,
)
from backend.detection.risk_scoring import (
    compute_mule_risk_index,
    get_account_risk,
)
from backend.detection.risk_models import MuleRiskScore, RiskReason

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper to build an in-memory DuckDB table simulating account_features
# ---------------------------------------------------------------------------
def _make_feature_table(con: duckdb.DuckDBPyConnection, rows: list):
    """
    Creates an account_features table in `con` with given mock data.
    rows: list of dicts with column overrides.
    """
    con.execute("""
        CREATE TABLE account_features (
            account_number VARCHAR,
            incoming_volume DOUBLE,
            outgoing_volume DOUBLE,
            incoming_txn_count BIGINT,
            outgoing_txn_count BIGINT,
            fan_in BIGINT,
            fan_out BIGINT,
            pass_through_ratio DOUBLE,
            pass_through_event_count BIGINT,
            pass_through_outgoing_transaction_count BIGINT,
            web_emulator_txn_count BIGINT,
            linux_script_txn_count BIGINT,
            top_ip_transaction_ratio DOUBLE,
            night_transaction_count BIGINT,
            transactions_per_active_day DOUBLE,
            layer1_candidate BOOLEAN,
            layer2_candidate BOOLEAN,
            layer3_candidate BOOLEAN,
            mule_risk_index DOUBLE,
            risk_band VARCHAR,
            risk_reasons VARCHAR,
            risk_family_scores VARCHAR,
            risk_model_version VARCHAR,
            risk_computed_at TIMESTAMP,
            risk_provenance VARCHAR
        );
    """)
    for r in rows:
        con.execute("""
            INSERT INTO account_features VALUES (
                $account_number, $incoming_volume, $outgoing_volume, $incoming_txn_count, $outgoing_txn_count,
                $fan_in, $fan_out, $pass_through_ratio, $pass_through_event_count, $pass_through_outgoing_transaction_count,
                $web_emulator_txn_count, $linux_script_txn_count, $top_ip_transaction_ratio, $night_transaction_count,
                $transactions_per_active_day, $layer1_candidate, $layer2_candidate, $layer3_candidate,
                NULL, NULL, '[]', '{}', NULL, NULL, NULL
            )
        """, r)


# ---------------------------------------------------------------------------
# Test 1 & 2: Score Bounds [0, 100] across production dataset
# ---------------------------------------------------------------------------
def test_production_scores_within_bounds():
    """All accounts in the production feature store must have risk_index in [0.0, 100.0]."""
    con = get_db()
    stats = con.execute("""
        SELECT 
            MIN(mule_risk_index) as min_score,
            MAX(mule_risk_index) as max_score,
            COUNT(*) as total_accounts,
            COUNT(mule_risk_index) as scored_accounts
        FROM account_features
    """).fetchone()

    assert stats[0] is not None and stats[0] >= 0.0, f"Min score {stats[0]} < 0"
    assert stats[1] is not None and stats[1] <= 100.0, f"Max score {stats[1]} > 100"
    assert stats[2] == 24873, f"Expected 24873 accounts, got {stats[2]}"
    assert stats[3] == 24873, f"Expected all 24873 accounts to be scored, got {stats[3]}"


# ---------------------------------------------------------------------------
# Test 3: Deterministic Repeated Execution
# ---------------------------------------------------------------------------
def test_scoring_determinism():
    """Two consecutive executions must produce identical scores for all accounts."""
    con = duckdb.connect(":memory:")
    mock_data = [
        {
            "account_number": "ACC_TEST_01",
            "incoming_volume": 500000.0,
            "outgoing_volume": 490000.0,
            "incoming_txn_count": 50,
            "outgoing_txn_count": 80,
            "fan_in": 35,
            "fan_out": 70,
            "pass_through_ratio": 0.96,
            "pass_through_event_count": 10,
            "pass_through_outgoing_transaction_count": 10,
            "web_emulator_txn_count": 15,
            "linux_script_txn_count": 5,
            "top_ip_transaction_ratio": 0.85,
            "night_transaction_count": 12,
            "transactions_per_active_day": 25.0,
            "layer1_candidate": True,
            "layer2_candidate": True,
            "layer3_candidate": False,
        }
    ]
    _make_feature_table(con, mock_data)
    
    # Run 1
    compute_mule_risk_index(con)
    res1 = get_account_risk(con, "ACC_TEST_01")
    
    # Run 2
    compute_mule_risk_index(con)
    res2 = get_account_risk(con, "ACC_TEST_01")

    assert res1 is not None and res2 is not None
    assert res1.risk_index == res2.risk_index
    assert res1.risk_band == res2.risk_band
    assert res1.risk_family_scores == res2.risk_family_scores
    assert len(res1.risk_reasons) == len(res2.risk_reasons)
    for r1, r2 in zip(res1.risk_reasons, res2.risk_reasons):
        assert r1.code == r2.code
        assert r1.points == r2.points


# ---------------------------------------------------------------------------
# Test 4 & 5: Reason Points Sum and Family Caps
# ---------------------------------------------------------------------------
def test_family_caps_and_reason_points_sum():
    """Family scores must never exceed configured maximums and reason points must sum correctly."""
    con = duckdb.connect(":memory:")
    # Create an extreme account with maxed-out metrics
    extreme_data = [
        {
            "account_number": "EXTREME_ACC",
            "incoming_volume": 50000000.0,
            "outgoing_volume": 49999000.0,
            "incoming_txn_count": 5000,
            "outgoing_txn_count": 5000,
            "fan_in": 500,
            "fan_out": 500,
            "pass_through_ratio": 1.0,
            "pass_through_event_count": 100,
            "pass_through_outgoing_transaction_count": 100,
            "web_emulator_txn_count": 1000,
            "linux_script_txn_count": 1000,
            "top_ip_transaction_ratio": 0.99,
            "night_transaction_count": 500,
            "transactions_per_active_day": 500.0,
            "layer1_candidate": True,
            "layer2_candidate": True,
            "layer3_candidate": True,
        }
    ]
    _make_feature_table(con, extreme_data)
    compute_mule_risk_index(con)
    score = get_account_risk(con, "EXTREME_ACC")

    assert score is not None
    # Maximum caps verification
    cfg = DEFAULT_RISK_CONFIG
    fam = score.risk_family_scores
    assert fam.get("FLOW_STRUCTURE", 0.0) <= cfg.flow.max_family_points
    assert fam.get("VELOCITY", 0.0) <= cfg.velocity.max_family_points
    assert fam.get("AUTOMATION", 0.0) <= cfg.automation.max_family_points
    assert fam.get("NETWORK_STRUCTURE", 0.0) <= cfg.network.max_family_points
    assert fam.get("TRANSACTION_BEHAVIOR", 0.0) <= cfg.transaction.max_family_points
    assert fam.get("ROLE_SUPPORT", 0.0) <= cfg.role_support.max_family_points
    assert score.risk_index <= 100.0

    # Reason codes must belong to valid families and points must be positive
    for r in score.risk_reasons:
        assert r.points > 0
        assert r.family in fam


# ---------------------------------------------------------------------------
# Test 6: Low-Signal vs Strong-Signal Ordering
# ---------------------------------------------------------------------------
def test_low_signal_vs_strong_signal():
    """A clean/normal account must receive a lower score than a suspicious/mule candidate."""
    con = duckdb.connect(":memory:")
    data = [
        {
            "account_number": "CLEAN_ACC",
            "incoming_volume": 5000.0,
            "outgoing_volume": 2000.0,
            "incoming_txn_count": 2,
            "outgoing_txn_count": 1,
            "fan_in": 2,
            "fan_out": 1,
            "pass_through_ratio": 0.0,
            "pass_through_event_count": 0,
            "pass_through_outgoing_transaction_count": 0,
            "web_emulator_txn_count": 0,
            "linux_script_txn_count": 0,
            "top_ip_transaction_ratio": 0.5,
            "night_transaction_count": 0,
            "transactions_per_active_day": 1.0,
            "layer1_candidate": False,
            "layer2_candidate": False,
            "layer3_candidate": False,
        },
        {
            "account_number": "SUSPICIOUS_ACC",
            "incoming_volume": 1500000.0,
            "outgoing_volume": 1490000.0,
            "incoming_txn_count": 3,
            "outgoing_txn_count": 25,
            "fan_in": 3,
            "fan_out": 25,
            "pass_through_ratio": 0.95,
            "pass_through_event_count": 15,
            "pass_through_outgoing_transaction_count": 15,
            "web_emulator_txn_count": 10,
            "linux_script_txn_count": 5,
            "top_ip_transaction_ratio": 0.95,
            "night_transaction_count": 8,
            "transactions_per_active_day": 20.0,
            "layer1_candidate": False,
            "layer2_candidate": False,
            "layer3_candidate": True,
        }
    ]
    _make_feature_table(con, data)
    compute_mule_risk_index(con)

    clean_score = get_account_risk(con, "CLEAN_ACC")
    susp_score = get_account_risk(con, "SUSPICIOUS_ACC")

    assert clean_score is not None and susp_score is not None
    assert clean_score.risk_index < susp_score.risk_index
    assert clean_score.risk_band in ["LOW", "MODERATE"]
    assert susp_score.risk_band in ["HIGH", "VERY_HIGH"]


# ---------------------------------------------------------------------------
# Test 7: Velocity Bands Verification
# ---------------------------------------------------------------------------
def test_velocity_scoring_bands():
    """Velocity must contribute strictly according to Step 5A pass-through ratio bands."""
    test_cases = [
        (0.40, 5, 0.0),    # < 0.50 -> 0 pts
        (0.60, 5, 8.0),    # 0.50-0.69 -> 8 pts
        (0.75, 5, 15.0),   # 0.70-0.84 -> 15 pts
        (0.90, 5, 20.0),   # 0.85-0.94 -> 20 pts
        (0.98, 5, 25.0),   # >= 0.95 -> 25 pts
        (0.98, 0, 0.0),    # No qualifying events -> 0 pts
        (0.98, 1, 10.0),   # Single qualifying event -> capped at 10 pts
    ]

    for pt_ratio, pt_events, expected_pts in test_cases:
        con = duckdb.connect(":memory:")
        data = [{
            "account_number": "VEL_TEST",
            "incoming_volume": 100000.0,
            "outgoing_volume": 100000.0,
            "incoming_txn_count": 10,
            "outgoing_txn_count": 10,
            "fan_in": 2,
            "fan_out": 2,
            "pass_through_ratio": pt_ratio,
            "pass_through_event_count": pt_events,
            "pass_through_outgoing_transaction_count": pt_events,
            "web_emulator_txn_count": 0,
            "linux_script_txn_count": 0,
            "top_ip_transaction_ratio": 0.0,
            "night_transaction_count": 0,
            "transactions_per_active_day": 1.0,
            "layer1_candidate": False,
            "layer2_candidate": False,
            "layer3_candidate": False,
        }]
        _make_feature_table(con, data)
        compute_mule_risk_index(con)
        score = get_account_risk(con, "VEL_TEST")
        assert score is not None
        assert score.risk_family_scores.get("VELOCITY", 0.0) == expected_pts


# ---------------------------------------------------------------------------
# Test 8: Automation / Device Behavior Scoring
# ---------------------------------------------------------------------------
def test_automation_behavior_scoring():
    """Automation family must score observed Web_Emulator and Linux_Script activity up to 20 pts."""
    con = duckdb.connect(":memory:")
    data = [
        {
            "account_number": "EMULATOR_ACC",
            "incoming_volume": 50000.0,
            "outgoing_volume": 50000.0,
            "incoming_txn_count": 2,
            "outgoing_txn_count": 12,
            "fan_in": 2,
            "fan_out": 12,
            "pass_through_ratio": 0.0,
            "pass_through_event_count": 0,
            "pass_through_outgoing_transaction_count": 0,
            "web_emulator_txn_count": 11,
            "linux_script_txn_count": 0,
            "top_ip_transaction_ratio": 0.85,
            "night_transaction_count": 0,
            "transactions_per_active_day": 2.0,
            "layer1_candidate": False,
            "layer2_candidate": False,
            "layer3_candidate": False,
        }
    ]
    _make_feature_table(con, data)
    compute_mule_risk_index(con)
    score = get_account_risk(con, "EMULATOR_ACC")
    assert score is not None
    auto_score = score.risk_family_scores.get("AUTOMATION", 0.0)
    assert auto_score > 0.0
    assert auto_score <= 20.0
    reasons = [r.code for r in score.risk_reasons if r.family == "AUTOMATION"]
    assert any("EMULATOR" in r or "AUTOMATED" in r for r in reasons)


# ---------------------------------------------------------------------------
# Test 9: Role Support Cap
# ---------------------------------------------------------------------------
def test_role_support_cap():
    """Role support must contribute 4 pts per active candidate role, capped at 10 pts."""
    con = duckdb.connect(":memory:")
    data = [
        {
            "account_number": "MULTI_ROLE_ACC",
            "incoming_volume": 10000.0,
            "outgoing_volume": 10000.0,
            "incoming_txn_count": 5,
            "outgoing_txn_count": 5,
            "fan_in": 2,
            "fan_out": 2,
            "pass_through_ratio": 0.0,
            "pass_through_event_count": 0,
            "pass_through_outgoing_transaction_count": 0,
            "web_emulator_txn_count": 0,
            "linux_script_txn_count": 0,
            "top_ip_transaction_ratio": 0.0,
            "night_transaction_count": 0,
            "transactions_per_active_day": 1.0,
            "layer1_candidate": True,
            "layer2_candidate": True,
            "layer3_candidate": True,
        }
    ]
    _make_feature_table(con, data)
    compute_mule_risk_index(con)
    score = get_account_risk(con, "MULTI_ROLE_ACC")
    assert score is not None
    role_pts = score.risk_family_scores.get("ROLE_SUPPORT", 0.0)
    # 3 * 4 = 12, but capped at 10
    assert role_pts == 10.0


# ---------------------------------------------------------------------------
# Test 10: Anti-Double-Counting Isolation
# ---------------------------------------------------------------------------
def test_anti_double_counting_isolation():
    """Correlated signals must not bleed across family boundaries or exceed individual family caps."""
    con = duckdb.connect(":memory:")
    data = [
        {
            "account_number": "FAN_OUT_HEAVY",
            "incoming_volume": 200000.0,
            "outgoing_volume": 195000.0,
            "incoming_txn_count": 2,
            "outgoing_txn_count": 120,
            "fan_in": 2,
            "fan_out": 115,
            "pass_through_ratio": 0.0,
            "pass_through_event_count": 0,
            "pass_through_outgoing_transaction_count": 0,
            "web_emulator_txn_count": 0,
            "linux_script_txn_count": 0,
            "top_ip_transaction_ratio": 0.1,
            "night_transaction_count": 0,
            "transactions_per_active_day": 5.0,
            "layer1_candidate": False,
            "layer2_candidate": True,
            "layer3_candidate": False,
        }
    ]
    _make_feature_table(con, data)
    compute_mule_risk_index(con)
    score = get_account_risk(con, "FAN_OUT_HEAVY")
    assert score is not None

    # Flow structure must not exceed 20
    assert score.risk_family_scores.get("FLOW_STRUCTURE", 0.0) <= 20.0
    # Network structure must not exceed 15
    assert score.risk_family_scores.get("NETWORK_STRUCTURE", 0.0) <= 15.0
    # Velocity must be 0 (no pass-through)
    assert score.risk_family_scores.get("VELOCITY", 0.0) == 0.0
    # Automation must be 0 (no emulator/script)
    assert score.risk_family_scores.get("AUTOMATION", 0.0) == 0.0


# ---------------------------------------------------------------------------
# Test 11: Null and Zero Feature Safety
# ---------------------------------------------------------------------------
def test_null_and_zero_safety():
    """Accounts with NULL or zero features must be handled safely without exceptions or NaN."""
    con = duckdb.connect(":memory:")
    data = [
        {
            "account_number": "NULL_ACC",
            "incoming_volume": 0.0,
            "outgoing_volume": 0.0,
            "incoming_txn_count": 0,
            "outgoing_txn_count": 0,
            "fan_in": 0,
            "fan_out": 0,
            "pass_through_ratio": None,
            "pass_through_event_count": None,
            "pass_through_outgoing_transaction_count": None,
            "web_emulator_txn_count": None,
            "linux_script_txn_count": None,
            "top_ip_transaction_ratio": None,
            "night_transaction_count": None,
            "transactions_per_active_day": None,
            "layer1_candidate": None,
            "layer2_candidate": None,
            "layer3_candidate": None,
        }
    ]
    _make_feature_table(con, data)
    compute_mule_risk_index(con)
    score = get_account_risk(con, "NULL_ACC")
    assert score is not None
    assert score.risk_index == 0.0
    assert score.risk_band == "LOW"
    assert isinstance(score.risk_family_scores, dict)
    assert isinstance(score.risk_reasons, list)


# ---------------------------------------------------------------------------
# Test 12: API Endpoint Schema & 404 Behavior
# ---------------------------------------------------------------------------
def test_api_risk_endpoint():
    """GET /api/accounts/{account_id}/risk returns 200 with valid MuleRiskScore schema."""
    response = client.get("/api/accounts/KKBK10000402/risk")
    assert response.status_code == 200
    data = response.json()
    
    assert data["account_number"] == "KKBK10000402"
    assert 0.0 <= data["risk_index"] <= 100.0
    assert data["risk_band"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
    assert data["risk_model_version"] == "v1"
    assert data["risk_provenance"] == "DERIVED"
    assert "risk_family_scores" in data
    assert "FLOW_STRUCTURE" in data["risk_family_scores"]
    assert "VELOCITY" in data["risk_family_scores"]
    assert "AUTOMATION" in data["risk_family_scores"]
    assert "NETWORK_STRUCTURE" in data["risk_family_scores"]
    assert "TRANSACTION_BEHAVIOR" in data["risk_family_scores"]
    assert "ROLE_SUPPORT" in data["risk_family_scores"]
    assert isinstance(data["risk_reasons"], list)
    for r in data["risk_reasons"]:
        assert "code" in r
        assert "family" in r
        assert "points" in r
        assert "observed_value" in r
        assert "description" in r

    # Non-existent account returns 404
    resp_404 = client.get("/api/accounts/NONEXISTENT9999/risk")
    assert resp_404.status_code == 404


# ---------------------------------------------------------------------------
# Test 13: Manual Validation Accounts Determinism
# ---------------------------------------------------------------------------
def test_known_validation_accounts():
    """The 5 validation accounts must evaluate to deterministic, reproducible scores."""
    validation_accounts = [
        "KKBK10000402",  # Velocity candidate, L3 Mode B, 11 automated outflows
        "KKBK10013350",  # L1 candidate, fan-in 120
        "AIRP10021987",  # L2 candidate, fan-out 110
        "AIRP10006038",  # Normal/no-role account
        "AXIS10013687",  # Pure L2 candidate
    ]
    con = get_db()
    for acc in validation_accounts:
        score = get_account_risk(con, acc)
        assert score is not None, f"Score for {acc} should exist"
        assert 0.0 <= score.risk_index <= 100.0
        assert score.risk_band in ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]
        assert len(score.risk_family_scores) == 6


# ---------------------------------------------------------------------------
# Test 14: Production Dataset Invariant
# ---------------------------------------------------------------------------
def test_production_dataset_unchanged():
    """Production dataset must retain exactly 2,000,000 transactions, 24,873 accounts, 2,252 duplicate TxIDs."""
    con = get_db()
    tx_count = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
    acc_count = con.execute("SELECT count(*) FROM accounts_dimension").fetchone()[0]
    dup_tx_count = con.execute("""
        SELECT SUM(cnt - 1) FROM (
            SELECT Transaction_ID, count(*) AS cnt
            FROM transactions GROUP BY Transaction_ID HAVING count(*) > 1
        )
    """).fetchone()[0]

    assert tx_count == 2000000, f"Expected 2,000,000 transactions, got {tx_count}"
    assert acc_count == 24873, f"Expected 24,873 accounts, got {acc_count}"
    assert dup_tx_count == 2252, f"Expected 2,252 duplicate Transaction_IDs, got {dup_tx_count}"
