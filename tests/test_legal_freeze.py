"""
Step 9: Legal Freeze + Bank Requisition Draft Workflow Tests
Operation 'ABHEDYA-CHAKRA'

Covers:
- Evidence extraction & determinism (verified accounts, transactions, exact amounts)
- Separation of root seed outflow vs downstream cumulative attribution
- Exact official Step 5B risk family points & Step 4 role indicators preserved
- All 4 document types (FREEZE, PRESERVATION, REQUISITION, ANNEXURE)
- Missing information normalization & explicit placeholders (no fabrication)
- Legal safety: non-judicial status (REVIEW_REQUIRED), no guilt/freeze claims
- Cryptographic integrity:
  * pdf_sha256 == SHA-256(final PDF bytes)
  * json_sha256 == SHA-256(stored JSON bytes)
  * No circular hash inside PDF
- API endpoints: create, retrieve, download PDF, download JSON, list, 404 handling
- Regression: existing endpoints remain functional
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import List
import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.legal_freeze.models import (
    LegalDocumentType,
    LegalDraftStatus,
    LegalDraftRequest,
    LegalDraftPackage,
    LegalDraftResponse,
    OfficerDetails,
    SubjectAccountLegalEvidence,
    LegalEvidenceSnapshot,
)
from backend.legal_freeze.evidence import (
    extract_legal_evidence,
    normalize_officer_details,
    OFFICER_PLACEHOLDER,
    BANK_PLACEHOLDER,
    BRANCH_PLACEHOLDER,
    PRESERVATION_PERIOD_PLACEHOLDER,
)
from backend.legal_freeze.templates import build_legal_draft_document
from backend.legal_freeze.pdf_generator import generate_legal_draft_pdf
from backend.legal_freeze.generator import generate_legal_draft
from backend.legal_freeze.store import LEGAL_DRAFT_STORE
from backend.investigations.orchestrator import investigate_victim_account

client = TestClient(app)


# ===========================================================================
# In-Memory DB Helper
# ===========================================================================

def _make_test_db(rows: list) -> duckdb.DuckDBPyConnection:
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
        )
    """)
    con.executemany(
        "INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    con.execute("""
        CREATE OR REPLACE VIEW accounts_dimension AS
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
    con.execute("""
        CREATE OR REPLACE VIEW account_features AS
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
            42.0 AS mule_risk_index,
            'HIGH' AS risk_band,
            '[]' AS risk_reasons,
            '{"FLOW_STRUCTURE": 10.0, "VELOCITY": 15.0, "AUTOMATION": 5.0, "NETWORK_STRUCTURE": 5.0, "TRANSACTION_BEHAVIOR": 5.0, "ROLE_SUPPORT": 2.0}' AS risk_family_scores,
            'v2_two_axis' AS risk_model_version,
            NULL::TIMESTAMP AS risk_computed_at,
            'DERIVED' AS risk_provenance,
            NULL::VARCHAR AS risk_factors,
            FALSE AS cycle_indicator,
            30.0 AS structural_risk_index,
            20.0 AS behavioral_risk_index,
            'LOW CURRENT INDICATOR' AS investigative_signal,
            'Both indicators currently limited.' AS investigative_summary,
            FALSE AS multi_modal_confirmation
        FROM accounts_dimension;
    """)
    return con


def _make_sample_db():
    base = datetime(2025, 3, 1, 10, 0, 0)
    rows = [
        ("TX101", "SRC01", "TARGET01", "SBIN0001", "HDFC0001", 50000.0, base, "NEFT", "Salary", "192.168.1.1", "Desktop"),
        ("TX102", "SRC02", "TARGET01", "ICIC0001", "HDFC0001", 25000.0, base + timedelta(minutes=4), "IMPS", "Transfer", "192.168.1.2", "Mobile"),
        ("TX103", "TARGET01", "HOP1A", "HDFC0001", "KKBK0001", 30000.0, base + timedelta(minutes=10), "UPI", "Payment", "192.168.1.1", "Mobile"),
        ("TX104", "TARGET01", "HOP1B", "HDFC0001", "PUNB0001", 40000.0, base + timedelta(minutes=14), "IMPS", "Vendor", "192.168.1.1", "Mobile"),
        ("TX105", "HOP1A", "TERM01", "KKBK0001", "AIRP0001", 28000.0, base + timedelta(minutes=30), "UPI", "Cashout", "10.0.0.1", "Android"),
    ]
    return _make_test_db(rows)


# ===========================================================================
# TEST GROUP 1: Legal Evidence Extraction
# ===========================================================================

class TestLegalEvidenceExtraction:

    def test_extract_legal_evidence_deterministic(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(subject_account="TARGET01")
        ev1 = extract_legal_evidence(inv, req)
        ev2 = extract_legal_evidence(inv, req)
        assert ev1.evidence_snapshot_sha256 == ev2.evidence_snapshot_sha256
        assert len(ev1.evidence_snapshot_sha256) == 64

    def test_exact_amounts_and_accounts_preserved(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(subject_account="TARGET01")
        ev = extract_legal_evidence(inv, req)

        assert ev.subject_account.account_number == "TARGET01"
        assert ev.subject_account.observed_inflow == 75000.0
        assert ev.subject_account.observed_outflow == 70000.0
        assert ev.subject_account.observed_net_flow_delta == 5000.0

        # Check transactions
        tx_ids = [t.transaction_id for t in ev.transactions_sample]
        assert "TX101" in tx_ids
        assert "TX103" in tx_ids
        for t in ev.transactions_sample:
            if t.transaction_id == "TX101":
                assert t.amount == 50000.0
                assert t.sender_account == "SRC01"
                assert t.receiver_account == "TARGET01"

    def test_attribution_distinction_preserved(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(subject_account="TARGET01")
        ev = extract_legal_evidence(inv, req)

        assert ev.attribution.root_seed_outflow == 70000.0
        assert "Downstream cumulative attribution" in ev.attribution.conservation_note
        assert "must NOT be summed" in ev.attribution.conservation_note

    def test_official_risk_family_points_preserved(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(subject_account="TARGET01")
        ev = extract_legal_evidence(inv, req)

        assert ev.risk.risk_index == 42.0
        assert ev.risk.risk_band == "HIGH"
        assert isinstance(ev.risk.family_contributions, dict)
        assert "FLOW_STRUCTURE" in ev.risk.family_contributions


# ===========================================================================
# TEST GROUP 2: Missing Information & Placeholders
# ===========================================================================

class TestMissingInformationHandling:

    def test_missing_fields_produce_explicit_placeholders(self):
        req = LegalDraftRequest(subject_account="TARGET01")
        officer = normalize_officer_details(req)

        assert officer.officer_name == OFFICER_PLACEHOLDER
        assert officer.police_station == OFFICER_PLACEHOLDER
        assert officer.case_reference == OFFICER_PLACEHOLDER
        assert officer.recipient_bank == BANK_PLACEHOLDER
        assert officer.recipient_branch == BRANCH_PLACEHOLDER
        assert officer.preservation_period == PRESERVATION_PERIOD_PLACEHOLDER

    def test_supplied_fields_are_honored(self):
        req = LegalDraftRequest(
            subject_account="TARGET01",
            officer_name="Inspector Vikram Sharma",
            officer_designation="Cyber Crime Investigator",
            police_station="Cyber Police Station Central",
            case_reference="FIR-2025-0892",
            recipient_bank="State Bank of India",
            recipient_branch="Nariman Point Branch",
            preservation_period="90 Days",
        )
        officer = normalize_officer_details(req)

        assert officer.officer_name == "Inspector Vikram Sharma"
        assert officer.police_station == "Cyber Police Station Central"
        assert officer.case_reference == "FIR-2025-0892"
        assert officer.recipient_bank == "State Bank of India"
        assert officer.preservation_period == "90 Days"

    def test_no_fabricated_data_invented(self):
        req = LegalDraftRequest(subject_account="TARGET01")
        officer = normalize_officer_details(req)

        # Confirm no fake FIR numbers or fake names are generated
        assert "FIR" not in officer.case_reference
        assert "Police Station" not in officer.police_station
        assert "Bank" not in officer.recipient_bank or officer.recipient_bank == BANK_PLACEHOLDER


# ===========================================================================
# TEST GROUP 3: Document Templates
# ===========================================================================

class TestDocumentTemplates:

    def test_account_freeze_request_template(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(
            subject_account="TARGET01",
            document_type=LegalDocumentType.ACCOUNT_FREEZE_REQUEST,
        )
        officer = normalize_officer_details(req)
        ev = extract_legal_evidence(inv, req)
        doc = build_legal_draft_document(req.document_type, ev, officer)

        assert "ACCOUNT FREEZE / HOLD REQUEST DRAFT" in doc.title
        assert doc.draft_notice == "DRAFT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW"
        assert any(s["id"] == "requested_action" for s in doc.sections)
        assert any(s["id"] == "basis_of_request" for s in doc.sections)
        assert any(s["id"] == "relevant_transactions" for s in doc.sections)
        assert "TARGET01" in doc.plain_text_content

    def test_record_preservation_request_template(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(
            subject_account="TARGET01",
            document_type=LegalDocumentType.RECORD_PRESERVATION_REQUEST,
        )
        officer = normalize_officer_details(req)
        ev = extract_legal_evidence(inv, req)
        doc = build_legal_draft_document(req.document_type, ev, officer)

        assert "RECORD PRESERVATION REQUEST DRAFT" in doc.title
        assert any(s["id"] == "preservation_request" for s in doc.sections)
        assert PRESERVATION_PERIOD_PLACEHOLDER in doc.plain_text_content

    def test_bank_information_requisition_template(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(
            subject_account="TARGET01",
            document_type=LegalDocumentType.BANK_INFORMATION_REQUISITION,
        )
        officer = normalize_officer_details(req)
        ev = extract_legal_evidence(inv, req)
        doc = build_legal_draft_document(req.document_type, ev, officer)

        assert "BANK INFORMATION REQUISITION DRAFT" in doc.title
        assert any(s["id"] == "requisition_items" for s in doc.sections)

    def test_evidence_annexure_template(self):
        con = _make_sample_db()
        inv = investigate_victim_account(con, "TARGET01")
        req = LegalDraftRequest(
            subject_account="TARGET01",
            document_type=LegalDocumentType.EVIDENCE_ANNEXURE,
        )
        officer = normalize_officer_details(req)
        ev = extract_legal_evidence(inv, req)
        doc = build_legal_draft_document(req.document_type, ev, officer)

        assert "SUPPORTING EVIDENCE ANNEXURE" in doc.title
        assert any(s["id"] == "section_b" for s in doc.sections)
        assert any(s["id"] == "section_h" for s in doc.sections)


# ===========================================================================
# TEST GROUP 4: Legal Safety & Non-Judicial Disclaimers
# ===========================================================================

class TestLegalSafety:

    def test_draft_status_is_review_required(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        assert res.draft.status == LegalDraftStatus.REVIEW_REQUIRED
        assert res.draft.status != "APPROVED"
        assert res.draft.status != "ISSUED"
        assert res.draft.status != "EXECUTED"

    def test_no_guilt_or_criminal_liability_claims(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        plain_text = res.draft.document.plain_text_content.lower()
        assert "guilty of" not in plain_text
        assert "convicted" not in plain_text
        assert "criminal syndicate has been established" not in plain_text
        assert "is guilty" not in plain_text

    def test_no_false_claims_of_executed_freeze(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        plain_text = res.draft.document.plain_text_content.lower()
        assert "account has been frozen" not in plain_text
        assert "court has ordered" not in plain_text
        assert "bank has executed" not in plain_text


# ===========================================================================
# TEST GROUP 5: Cryptographic Hash Integrity
# ===========================================================================

class TestHashIntegrity:

    def test_pdf_sha256_matches_actual_pdf_bytes(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        pdf_bytes = LEGAL_DRAFT_STORE.get_pdf(res.draft.package_id)
        assert pdf_bytes is not None
        actual_sha = hashlib.sha256(pdf_bytes).hexdigest()
        assert res.draft.pdf_sha256 == actual_sha

    def test_json_sha256_matches_stored_json_bytes(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        json_bytes = LEGAL_DRAFT_STORE.get_json(res.draft.package_id)
        assert json_bytes is not None
        actual_sha = hashlib.sha256(json_bytes).hexdigest()
        assert res.draft.json_sha256 == actual_sha

    def test_pdf_does_not_embed_its_own_sha(self):
        con = _make_sample_db()
        req = LegalDraftRequest(subject_account="TARGET01")
        res = generate_legal_draft(con, req)

        pdf_bytes = LEGAL_DRAFT_STORE.get_pdf(res.draft.package_id)
        assert pdf_bytes is not None
        pdf_text = pdf_bytes.decode("latin1", errors="ignore")
        # Ensure the PDF does NOT contain its own hex string to prevent circular hash
        assert res.draft.pdf_sha256 not in pdf_text


# ===========================================================================
# TEST GROUP 6: API Endpoints
# ===========================================================================

class TestLegalDraftAPI:

    def test_create_and_retrieve_legal_draft(self):
        resp = client.post("/api/legal-freeze/drafts", json={
            "subject_account": "KKBK10000402",
            "document_type": "ACCOUNT_FREEZE_REQUEST",
            "max_hops": 2,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        draft = data["draft"]
        draft_id = draft["package_id"]
        assert draft["subject_account"] == "KKBK10000402"
        assert draft["status"] == "REVIEW_REQUIRED"
        assert draft["pdf_sha256"] is not None

        # Retrieve
        get_resp = client.get(f"/api/legal-freeze/drafts/{draft_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["draft"]["package_id"] == draft_id

    def test_download_pdf_and_verify_bytes(self):
        resp = client.post("/api/legal-freeze/drafts", json={
            "subject_account": "AIRP10000595",
            "document_type": "RECORD_PRESERVATION_REQUEST",
            "max_hops": 2,
        })
        assert resp.status_code == 200
        draft_id = resp.json()["draft"]["package_id"]
        expected_sha = resp.json()["draft"]["pdf_sha256"]

        pdf_resp = client.get(f"/api/legal-freeze/drafts/{draft_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        actual_sha = hashlib.sha256(pdf_resp.content).hexdigest()
        assert actual_sha == expected_sha

    def test_download_json_and_verify_bytes(self):
        resp = client.post("/api/legal-freeze/drafts", json={
            "subject_account": "PYTM10001005",
            "document_type": "BANK_INFORMATION_REQUISITION",
            "max_hops": 2,
        })
        assert resp.status_code == 200
        draft_id = resp.json()["draft"]["package_id"]
        expected_sha = resp.json()["draft"]["json_sha256"]

        json_resp = client.get(f"/api/legal-freeze/drafts/{draft_id}/json")
        assert json_resp.status_code == 200
        assert "application/json" in json_resp.headers["content-type"]
        actual_sha = hashlib.sha256(json_resp.content).hexdigest()
        assert actual_sha == expected_sha

    def test_nonexistent_draft_returns_404(self):
        resp = client.get("/api/legal-freeze/drafts/DRAFT-NONEXISTENT-999")
        assert resp.status_code == 404

    def test_invalid_account_returns_404(self):
        resp = client.post("/api/legal-freeze/drafts", json={
            "subject_account": "INVALID_ACCOUNT_9999",
            "document_type": "ACCOUNT_FREEZE_REQUEST",
        })
        assert resp.status_code == 404

    def test_list_drafts_endpoint(self):
        resp = client.get("/api/legal-freeze/drafts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ===========================================================================
# TEST GROUP 7: Regression Baseline
# ===========================================================================

class TestRegressionBaselines:

    def test_health_check_unaffected(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_case_file_endpoint_unaffected(self):
        resp = client.get("/api/case-files/CASE-NONEXISTENT")
        assert resp.status_code == 404

    def test_case_diary_endpoint_unaffected(self):
        resp = client.get("/api/case-diaries/DIARY-NONEXISTENT")
        assert resp.status_code == 404
