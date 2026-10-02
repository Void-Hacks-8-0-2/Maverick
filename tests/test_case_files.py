"""
Step 7: Evidence Package & Case File Tests for Operation 'ABHEDYA-CHAKRA'
Comprehensive verification of forensic case file generation, evidence snapshotting,
canonical SHA-256 integrity hashing, PDF compilation, official risk family points,
money conservation semantics, truncation/cycle warnings, and analytical determinism.
"""

import io
import hashlib
from datetime import datetime, timedelta
import pypdf
import pytest
import duckdb
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db
from backend.case_files.models import (
    CaseFileRequest,
    CaseFileResponse,
    CaseFileMetadata,
    EvidenceSnapshot,
)
from backend.case_files.generator import generate_forensic_case_file
from backend.case_files.store import CASE_FILE_STORE

client = TestClient(app)


def _make_mem_case_db(rows):
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
            0.98 AS pass_through_ratio,
            1 AS pass_through_event_count,
            420.0 AS median_incoming_to_outgoing_seconds,
            1 AS rapid_outflow_count,
            TRUE AS pass_through_candidate,
            total_inflow AS pass_through_incoming_volume,
            total_outflow AS pass_through_attributed_volume,
            outgoing_txn_count AS pass_through_outgoing_transaction_count,
            FALSE AS layer1_candidate,
            FALSE AS layer2_candidate,
            TRUE AS layer3_candidate,
            '[]' AS layer1_reasons,
            '[]' AS layer2_reasons,
            '[{"code": "L3_TEST", "observed_value": "11 transactions", "description": "Automated drain pattern observed"}]' AS layer3_reasons,
            0 AS layer1_signal_count,
            0 AS layer2_signal_count,
            1 AS layer3_signal_count,
            70.0 AS mule_risk_index,
            'HIGH' AS risk_band,
            '[{"code": "VEL_BURST", "family": "VELOCITY", "points": 25.0, "observed_value": 0.98, "description": "Rapid pass-through funds drain"}]' AS risk_reasons,
            '{"FLOW_STRUCTURE": 20.0, "VELOCITY": 25.0, "AUTOMATION": 14.0, "NETWORK_STRUCTURE": 2.0, "TRANSACTION_BEHAVIOR": 5.0, "ROLE_SUPPORT": 4.0}' AS risk_family_scores,
            'v1' AS risk_model_version,
            NULL::TIMESTAMP AS risk_computed_at,
            'DERIVED' AS risk_provenance,
            NULL::VARCHAR AS risk_factors,
            FALSE AS cycle_indicator
        FROM accounts_dimension;
    """)

    return con


# ==============================================================================
# TEST 1: Case file from valid investigation
# ==============================================================================
def test_case_file_valid_investigation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX1", "VICTIM_A", "MULE_B", "IFSC1", "IFSC2", 1000.0, base, "UPI", "narration 1", "1.1.1.1", "Mobile"),
        ("TX2", "MULE_B", "CASH_C", "IFSC2", "IFSC3", 900.0, base + timedelta(minutes=5), "IMPS", "narration 2", "2.2.2.2", "Web"),
    ]
    con = _make_mem_case_db(rows)
    req = CaseFileRequest(account_number="VICTIM_A", include_pdf=True, include_json=True)
    resp = generate_forensic_case_file(con, req)

    assert resp.metadata.subject_account == "VICTIM_A"
    assert resp.metadata.case_file_id.startswith("CASE-VICTIM_A-")
    assert resp.metadata.status in ("COMPLETED", "NO_QUALIFYING_OUTFLOW")
    assert resp.metadata.evidence_snapshot_sha256 is not None
    assert len(resp.metadata.evidence_snapshot_sha256) == 64
    assert resp.metadata.pdf_sha256 is not None
    assert len(resp.metadata.pdf_sha256) == 64
    assert resp.metadata.json_sha256 is not None


# ==============================================================================
# TEST 2: Invalid account returns 404
# ==============================================================================
def test_case_file_invalid_account_404():
    con = _make_mem_case_db([])
    with pytest.raises(ValueError):
        generate_forensic_case_file(con, CaseFileRequest(account_number="NON_EXISTENT_ACC"))


# ==============================================================================
# TEST 3: Evidence snapshot contains source transaction IDs
# ==============================================================================
def test_case_file_snapshot_contains_tx_ids():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_VERIFY_999", "ACC_SND", "ACC_RCV", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_SND"))
    
    assert "TX_VERIFY_999" in resp.evidence_snapshot.observed_facts.source_transaction_ids
    sample_ids = [t.transaction_id for t in resp.evidence_snapshot.transactions_sample]
    assert "TX_VERIFY_999" in sample_ids


# ==============================================================================
# TEST 4: Evidence snapshot contains row IDs
# ==============================================================================
def test_case_file_snapshot_contains_row_ids():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX1", "ACC_ROW", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_ROW"))
    
    assert len(resp.evidence_snapshot.observed_facts.source_row_ids) > 0
    assert isinstance(resp.evidence_snapshot.observed_facts.source_row_ids[0], int)


# ==============================================================================
# TEST 5: Dataset SHA-256 preserved
# ==============================================================================
def test_case_file_dataset_sha_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX1", "ACC_SHA", "B", "IFSC", "IFSC", 100.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_SHA"))

    expected_sha = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    assert resp.metadata.dataset_sha256 == expected_sha
    assert resp.evidence_snapshot.dataset_sha256 == expected_sha


# ==============================================================================
# TEST 6: Evidence SHA deterministic on repeated execution
# ==============================================================================
def test_case_file_evidence_sha_deterministic():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "DET_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_case_db(rows)
    resp1 = generate_forensic_case_file(con, CaseFileRequest(account_number="DET_ACC"))
    resp2 = generate_forensic_case_file(con, CaseFileRequest(account_number="DET_ACC"))

    assert resp1.metadata.evidence_snapshot_sha256 == resp2.metadata.evidence_snapshot_sha256
    assert resp1.metadata.case_file_id == resp2.metadata.case_file_id


# ==============================================================================
# TEST 7: Document (PDF) generated successfully
# ==============================================================================
def test_case_file_pdf_generated():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX1", "ACC_PDF", "B", "IFSC", "IFSC", 250.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_PDF", include_pdf=True))

    pdf_bytes = CASE_FILE_STORE.get_pdf(resp.metadata.case_file_id)
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


# ==============================================================================
# TEST 8: Document hash generated
# ==============================================================================
def test_case_file_document_hash_generated():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX1", "ACC_HASH", "B", "IFSC", "IFSC", 250.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_HASH", include_pdf=True))

    assert resp.metadata.pdf_sha256 is not None
    pdf_bytes = CASE_FILE_STORE.get_pdf(resp.metadata.case_file_id)
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()
    assert resp.metadata.pdf_sha256 == expected_hash


# ==============================================================================
# TEST 9: JSON package generated
# ==============================================================================
def test_case_file_json_package_generated():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("TX1", "ACC_JSON", "B", "IFSC", "IFSC", 250.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ACC_JSON", include_json=True))

    json_bytes = CASE_FILE_STORE.get_json(resp.metadata.case_file_id)
    assert json_bytes is not None
    assert resp.metadata.json_sha256 == hashlib.sha256(json_bytes).hexdigest()


# ==============================================================================
# TEST 10: ROOT_SEED preserved in case file trace
# ==============================================================================
def test_case_file_root_seed_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_SEED_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 800.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ROOT_SEED_ACC"))

    root_seeds = [e for e in resp.trace.edges if e.edge_type == "ROOT_SEED"]
    assert len(root_seeds) == 1
    assert root_seeds[0].source_account == "ROOT_SEED_ACC"
    assert resp.evidence_snapshot.attribution.root_seed_edge_count == 1
    assert resp.evidence_snapshot.attribution.root_seed_outflow == 1000.0


# ==============================================================================
# TEST 11: FIFO edges preserved in case file trace
# ==============================================================================
def test_case_file_fifo_edges_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "ROOT_FIFO_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 800.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ROOT_FIFO_ACC"))

    fifo_edges = [e for e in resp.trace.edges if e.edge_type == "FIFO_ATTRIBUTION"]
    assert len(fifo_edges) == 1
    assert fifo_edges[0].intermediary_account == "B"
    assert fifo_edges[0].destination_account == "C"
    assert resp.evidence_snapshot.attribution.downstream_fifo_edge_count == 1
    assert resp.evidence_snapshot.attribution.downstream_cumulative_attribution == 800.0


# ==============================================================================
# TEST 12: Risk score matches Step 5B
# ==============================================================================
def test_case_file_risk_score_matches():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "RISK_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="RISK_ACC"))

    assert resp.evidence_snapshot.official_risk.risk_index == 70.0
    assert resp.evidence_snapshot.official_risk.risk_band == "HIGH"


# ==============================================================================
# TEST 13: Official risk family scores preserved
# ==============================================================================
def test_case_file_official_risk_family_scores_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "FAM_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="FAM_ACC"))

    fam_points = resp.evidence_snapshot.official_risk.family_points
    expected_families = [
        "FLOW_STRUCTURE", "VELOCITY", "AUTOMATION",
        "NETWORK_STRUCTURE", "TRANSACTION_BEHAVIOR", "ROLE_SUPPORT"
    ]
    for ef in expected_families:
        assert ef in fam_points, f"Missing official risk family '{ef}'"
    assert fam_points["FLOW_STRUCTURE"] == 20.0
    assert fam_points["VELOCITY"] == 25.0


# ==============================================================================
# TEST 14: Velocity values match Step 5A
# ==============================================================================
def test_case_file_velocity_matches():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "VEL_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="VEL_ACC"))

    vel = resp.evidence_snapshot.velocity_profile
    assert vel.pass_through_candidate is True
    assert vel.pass_through_ratio == 0.98


# ==============================================================================
# TEST 15: Role values match Step 4
# ==============================================================================
def test_case_file_roles_match():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "ROLE_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="ROLE_ACC"))

    roles = resp.evidence_snapshot.mule_roles
    assert roles.l3_terminal_candidate is True
    assert roles.primary_role_label == "L3 Terminal Candidate"


# ==============================================================================
# TEST 16: Truncation warning preserved
# ==============================================================================
def test_case_file_truncation_warning_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    # Generate 5 outgoing transactions from root with max_branches_per_hop=2
    rows = [
        (f"T{i}", "TRUNC_ACC", f"RECV_{i}", "IFSC", "IFSC", 100.0, base + timedelta(minutes=i), "UPI", "", "1.1.1.1", "Mobile")
        for i in range(5)
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="TRUNC_ACC", max_branches_per_hop=2))

    assert resp.trace.truncated is True
    assert resp.evidence_snapshot.limitations.is_truncated is True
    assert len(resp.evidence_snapshot.limitations.truncation_reasons) > 0


# ==============================================================================
# TEST 17: Cycle warning preserved
# ==============================================================================
def test_case_file_cycle_warning_preserved():
    base = datetime(2025, 1, 1, 10, 0, 0)
    # Loop A -> B -> C -> B
    rows = [
        ("T1", "CYC_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 900.0, base + timedelta(minutes=1), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "B", "IFSC", "IFSC", 800.0, base + timedelta(minutes=2), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="CYC_ACC"))

    assert len(resp.trace.cycles_detected) > 0
    assert len(resp.evidence_snapshot.limitations.cycles_detected) > 0


# ==============================================================================
# TEST 18: Limitations included
# ==============================================================================
def test_case_file_limitations_included():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "LIM_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="LIM_ACC"))

    lim = resp.evidence_snapshot.limitations
    assert "15-day" in lim.dataset_observation_window
    assert "No external ground-truth labels" in lim.ground_truth_status
    assert "TEMPORAL_FIFO" in lim.legal_nature_disclaimer


# ==============================================================================
# TEST 19: No fabricated transaction evidence
# ==============================================================================
def test_case_file_no_fabricated_evidence():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("REAL_TX_007", "REAL_ACC", "REAL_RCV", "IFSC1", "IFSC2", 1234.56, base, "IMPS", "legit test", "192.168.1.5", "Desktop")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="REAL_ACC"))

    tx = resp.evidence_snapshot.transactions_sample[0]
    assert tx.transaction_id == "REAL_TX_007"
    assert tx.sender_account == "REAL_ACC"
    assert tx.receiver_account == "REAL_RCV"
    assert tx.amount == 1234.56
    assert tx.payment_mode == "IMPS"
    assert tx.narration == "legit test"
    assert tx.ip_address == "192.168.1.5"


# ==============================================================================
# TEST 20: No legal certainty language
# ==============================================================================
def test_case_file_no_legal_certainty_language():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "SAFE_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="SAFE_ACC", include_pdf=True))

    disclaimer = resp.metadata.disclaimer.lower()
    narrative = resp.evidence_narrative.lower()

    forbidden_words = ["guilty", "criminal", "fraudster", "proven to have committed", "court judgment"]
    for word in forbidden_words:
        assert word not in disclaimer, f"Forbidden legal certainty word '{word}' found in disclaimer!"
        assert word not in narrative, f"Forbidden legal certainty word '{word}' found in narrative!"


# ==============================================================================
# TEST 21: Arbitrary account investigation works (independent of demo accounts)
# ==============================================================================
def test_case_file_arbitrary_account():
    base = datetime(2025, 1, 1, 10, 0, 0)
    arb_acc = "ARBITRARY_EVAL_987654"
    rows = [
        ("T1", arb_acc, "B", "IFSC", "IFSC", 450.0, base, "UPI", "", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number=arb_acc))

    assert resp.metadata.subject_account == arb_acc
    assert resp.metadata.case_file_id.startswith(f"CASE-{arb_acc}-")


# ==============================================================================
# TEST 22: Case file generation does NOT modify production CSV
# ==============================================================================
def test_case_file_does_not_modify_production_csv():
    import os
    csv_path = os.path.join("data", "VoidHacks8_MuleAccount_2M_Transactions.csv")
    sha = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 8):
            sha.update(chunk)
    digest = sha.hexdigest()
    expected = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    assert digest == expected, f"Production CSV was modified! {digest} != {expected}"


# ==============================================================================
# TEST 23: Repeated generation produces analytically identical evidence
# ==============================================================================
def test_case_file_repeated_generation_analytically_identical():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "IDEM_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_case_db(rows)
    r1 = generate_forensic_case_file(con, CaseFileRequest(account_number="IDEM_ACC"))
    r2 = generate_forensic_case_file(con, CaseFileRequest(account_number="IDEM_ACC"))

    assert r1.metadata.evidence_snapshot_sha256 == r2.metadata.evidence_snapshot_sha256
    assert r1.evidence_snapshot.attribution.root_seed_outflow == r2.evidence_snapshot.attribution.root_seed_outflow
    assert r1.evidence_snapshot.attribution.downstream_cumulative_attribution == r2.evidence_snapshot.attribution.downstream_cumulative_attribution
    assert r1.evidence_snapshot.official_risk.family_points == r2.evidence_snapshot.official_risk.family_points


# ==============================================================================
# TEST 24: PDF content sections verified via pypdf
# ==============================================================================
def test_case_file_pdf_sections_verified():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "PDF_SEC_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="PDF_SEC_ACC", include_pdf=True))

    pdf_bytes = CASE_FILE_STORE.get_pdf(resp.metadata.case_file_id)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join(page.extract_text() for page in reader.pages)
    compact_text = full_text.replace("\n", "")

    required_sections = [
        "OPERATION ABHEDYA-CHAKRA",
        "INVESTIGATION METADATA",
        "INVESTIGATION SCOPE",
        "SUBJECT ACCOUNT ACTIVITY",
        "ROOT / VICTIM TRANSACTIONS",
        "TEMPORAL FIFO ATTRIBUTION",
        "4-HOP INVESTIGATION TRACE",
        "TERMINAL / DOWNSTREAM",
        "MULE RISK EVIDENCE",
        "VELOCITY EVIDENCE",
        "MULE ROLE INDICATORS",
        "ANALYTICAL LIMITATIONS",
        "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101",
    ]
    for sec in required_sections:
        assert sec in full_text or sec in compact_text, f"Required section '{sec}' missing in generated PDF!"


# ==============================================================================
# STEP 7 FINAL INTEGRITY AUDIT — New Regression Tests (Tests 25-31)
# ==============================================================================

# ==============================================================================
# TEST 25: pdf_sha256 in metadata exactly equals SHA-256 of stored PDF bytes
# ==============================================================================
def test_pdf_sha256_matches_actual_pdf_bytes():
    """
    Critical: pdf_sha256 returned in metadata must match SHA-256(final PDF bytes).
    The PDF is compiled first; the hash is then computed over the final binary.
    There is NO circularity — the hash is NOT embedded inside the PDF itself.
    """
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "PDFHASH_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="PDFHASH_ACC", include_pdf=True))

    assert resp.metadata.pdf_sha256 is not None, "pdf_sha256 must be set"

    pdf_bytes = CASE_FILE_STORE.get_pdf(resp.metadata.case_file_id)
    assert pdf_bytes is not None, "PDF bytes must be stored"

    actual_sha = hashlib.sha256(pdf_bytes).hexdigest()
    assert resp.metadata.pdf_sha256 == actual_sha, (
        f"pdf_sha256 mismatch!\n"
        f"  metadata.pdf_sha256 = {resp.metadata.pdf_sha256}\n"
        f"  SHA256(pdf_bytes)   = {actual_sha}"
    )


# ==============================================================================
# TEST 26: Downloaded PDF bytes (via GET endpoint) produce the same sha256
# ==============================================================================
def test_downloaded_pdf_bytes_match_stored_sha256():
    """
    Verifies GET /api/case-files/{id}/pdf returns the exact same binary content
    that was compiled at generation time. The SHA-256 of the download must match
    metadata.pdf_sha256.
    """
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "DLPDF_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="DLPDF_ACC", include_pdf=True))
    case_id = resp.metadata.case_file_id
    expected_sha = resp.metadata.pdf_sha256

    # Retrieve via the HTTP endpoint
    http_resp = client.get(f"/api/case-files/{case_id}/pdf")
    assert http_resp.status_code == 200
    downloaded_bytes = http_resp.content
    actual_sha = hashlib.sha256(downloaded_bytes).hexdigest()

    assert actual_sha == expected_sha, (
        f"Downloaded PDF SHA-256 mismatch!\n"
        f"  expected (metadata) = {expected_sha}\n"
        f"  actual (download)   = {actual_sha}"
    )


# ==============================================================================
# TEST 27: Evidence snapshot SHA-256 is deterministic across independent calls
# ==============================================================================
def test_evidence_snapshot_sha_is_deterministic():
    """
    Repeated case file generation for the same account and same data must produce
    the same evidence_snapshot_sha256. This proves canonical serialization is
    stable (sort_keys=True, indent=2).
    """
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "DET_ACC", "B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 800.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_case_db(rows)
    r1 = generate_forensic_case_file(con, CaseFileRequest(account_number="DET_ACC"))
    r2 = generate_forensic_case_file(con, CaseFileRequest(account_number="DET_ACC"))

    assert r1.metadata.evidence_snapshot_sha256 == r2.metadata.evidence_snapshot_sha256, (
        f"Evidence snapshot hash is NOT deterministic!\n"
        f"  run1: {r1.metadata.evidence_snapshot_sha256}\n"
        f"  run2: {r2.metadata.evidence_snapshot_sha256}"
    )


# ==============================================================================
# TEST 28: JSON hash follows documented canonicalization rule
# ==============================================================================
def test_json_hash_follows_canonicalization_rule():
    """
    json_sha256 must equal SHA-256(json.dumps(snapshot.model_dump(mode='json'),
    indent=2, sort_keys=True).encode('utf-8')).
    This verifies the documented canonicalization contract.
    """
    import json as _json

    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "JSONHASH_ACC", "B", "IFSC", "IFSC", 600.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="JSONHASH_ACC", include_json=True))

    assert resp.metadata.json_sha256 is not None, "json_sha256 must be set"

    # Independently compute canonical hash
    snapshot_dict = resp.evidence_snapshot.model_dump(mode="json")
    canonical_bytes = _json.dumps(snapshot_dict, indent=2, sort_keys=True).encode("utf-8")
    expected_sha = hashlib.sha256(canonical_bytes).hexdigest()

    assert resp.metadata.json_sha256 == expected_sha, (
        f"JSON hash does not match canonical rule!\n"
        f"  metadata.json_sha256 = {resp.metadata.json_sha256}\n"
        f"  canonical recompute  = {expected_sha}"
    )


# ==============================================================================
# TEST 29: JSON hash also equals SHA-256 of stored JSON bytes
# ==============================================================================
def test_json_sha256_matches_stored_json_bytes():
    """
    Verifies the stored raw JSON bytes in CASE_FILE_STORE produce the same
    SHA-256 as metadata.json_sha256.
    """
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "JSONSTORE_ACC", "B", "IFSC", "IFSC", 300.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="JSONSTORE_ACC", include_json=True))

    json_bytes = CASE_FILE_STORE.get_json(resp.metadata.case_file_id)
    assert json_bytes is not None, "JSON bytes must be stored"

    actual_sha = hashlib.sha256(json_bytes).hexdigest()
    assert resp.metadata.json_sha256 == actual_sha, (
        f"JSON store bytes SHA-256 mismatch!\n"
        f"  metadata.json_sha256 = {resp.metadata.json_sha256}\n"
        f"  SHA256(json_bytes)   = {actual_sha}"
    )


# ==============================================================================
# TEST 30: PDF text does not falsely claim to be a self-referential hash
# ==============================================================================
def test_pdf_does_not_claim_self_hash():
    """
    The PDF must NOT claim to contain its own final SHA-256 as an embedded hash.
    Instead, the PDF document must state that the document SHA is provided in
    the case-file metadata (not embedded in the PDF itself).
    """
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "SELFHASH_ACC", "B", "IFSC", "IFSC", 500.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    resp = generate_forensic_case_file(con, CaseFileRequest(account_number="SELFHASH_ACC", include_pdf=True))

    pdf_bytes = CASE_FILE_STORE.get_pdf(resp.metadata.case_file_id)
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    compact_text = full_text.replace("\n", "")

    # Confirm the PDF explicitly says hash is in metadata (not a self-claim)
    assert (
        "see metadata" in compact_text.lower() or
        "see case-file metadata" in compact_text.lower() or
        "supplied in the case-file metadata" in compact_text.lower() or
        "calculated over the final generated pdf bytes" in compact_text.lower()
    ), (
        "PDF must clarify that the document SHA-256 is supplied in case-file metadata "
        "and NOT claim self-referential hash integrity within the PDF body."
    )

    # Confirm the actual pdf_sha256 value is NOT embedded literally in the PDF
    # (which would make it circular — computing SHA over bytes containing that same SHA)
    assert resp.metadata.pdf_sha256 not in compact_text, (
        "pdf_sha256 value must NOT be embedded inside the PDF itself — "
        "that would create a circular/self-referential hash."
    )


# ==============================================================================
# TEST 31: Production dataset SHA remains unmodified
# ==============================================================================
def test_production_dataset_sha_unchanged_after_case_file_generation():
    """
    Case file generation must not modify the production CSV dataset.
    Verifies SHA-256 after a full generation cycle.
    """
    import os

    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [("T1", "CSVCHK_ACC", "B", "IFSC", "IFSC", 200.0, base, "UPI", "", "1.1.1.1", "Mobile")]
    con = _make_mem_case_db(rows)
    generate_forensic_case_file(con, CaseFileRequest(account_number="CSVCHK_ACC", include_pdf=True, include_json=True))

    csv_path = os.path.join("data", "VoidHacks8_MuleAccount_2M_Transactions.csv")
    sha = hashlib.sha256()
    with open(csv_path, "rb") as f:
        while chunk := f.read(1024 * 1024 * 8):
            sha.update(chunk)
    actual = sha.hexdigest()
    expected = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
    assert actual == expected, f"Production CSV was modified! {actual} != {expected}"
