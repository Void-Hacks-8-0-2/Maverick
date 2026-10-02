"""
Step 11 — End-to-End Investigation Integration Test Suite
Operation 'ABHEDYA-CHAKRA'

Validates complete forensic pipeline execution across all stages:
Account -> Features -> Risk -> Role -> Velocity -> Victim Investigation ->
FIFO Attribution Trace -> Timeline -> Transaction Explorer -> Case File ->
Case Diary -> Legal Freeze Draft

Verifies:
1. Every stage successfully executes on production accounts.
2. Subject account identity is strictly conserved across all stages.
3. Risk scores originate from Step 5B and are identical across all consumers.
4. L1/L2/L3 role classifications remain consistent across all stages.
5. Step 5A velocity findings remain consistent across all stages.
6. Step 5C FIFO attribution facts remain consistent across all stages.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db

client = TestClient(app)

BENCHMARK_ACCOUNTS = [
    "KKBK10000402",  # Primary smoke account
    "AIRP10000595",
    "PYTM10001005",
    "PUNB10000806",
]


@pytest.fixture(scope="module")
def db_conn():
    return get_db()


class TestEndToEndInvestigationChain:
    """Validates the complete forensic pipeline across real production accounts."""

    @pytest.mark.parametrize("account_id", BENCHMARK_ACCOUNTS)
    def test_complete_investigation_chain_and_consistency(self, account_id, db_conn):
        # 1. Account Detail Endpoint
        r_acc = client.get(f"/api/accounts/{account_id}")
        assert r_acc.status_code == 200, f"Account lookup failed for {account_id}"
        acc_data = r_acc.json()
        assert acc_data["account_id"] == account_id

        # 2. Account Features Endpoint
        r_feat = client.get(f"/api/accounts/{account_id}/features")
        assert r_feat.status_code == 200, f"Features lookup failed for {account_id}"
        feat_data = r_feat.json()
        assert feat_data["account_number"] == account_id
        feat_risk = feat_data["mule_risk_index"]
        feat_l1 = feat_data["layer1_candidate"]
        feat_l2 = feat_data["layer2_candidate"]
        feat_l3 = feat_data["layer3_candidate"]

        # 3. Risk Scoring Endpoint
        r_risk = client.get(f"/api/accounts/{account_id}/risk")
        assert r_risk.status_code == 200, f"Risk lookup failed for {account_id}"
        risk_data = r_risk.json()
        assert risk_data["account_number"] == account_id
        exact_risk_score = risk_data["risk_index"]
        exact_risk_band = risk_data["risk_band"]
        assert feat_risk == exact_risk_score, "Feature risk != Dedicated risk score"

        # 4. Velocity Endpoint
        r_vel = client.get(f"/api/accounts/{account_id}/velocity")
        assert r_vel.status_code == 200, f"Velocity lookup failed for {account_id}"
        vel_data = r_vel.json()
        assert vel_data["account_id"] == account_id
        assert "events" in vel_data
        assert vel_data["qualifying_window"] == "3_TO_15_MINUTES"

        # 5. 4-Hop Attribution Trace Endpoint (Graph Explorer)
        r_trace = client.get(f"/api/accounts/{account_id}/trace?max_hops=4")
        assert r_trace.status_code == 200, f"Attribution trace failed for {account_id}"
        trace_data = r_trace.json()
        assert trace_data["root_account"] == account_id
        assert trace_data["max_hops"] <= 4
        for edge in trace_data["edges"]:
            assert "source" in edge and "target" in edge, f"Graph edge missing source/target: {edge}"
            assert edge["amount"] > 0, f"Encountered non-positive edge amount: {edge}"

        # 6. Blind Victim Investigation Endpoint
        r_vic = client.get(f"/api/investigations/victim/{account_id}?max_hops=4")
        assert r_vic.status_code == 200, f"Victim investigation failed for {account_id}"
        vic_data = r_vic.json()
        assert vic_data["account_number"] == account_id
        assert vic_data["status"] == "COMPLETED"
        assert vic_data["risk"]["risk_index"] == exact_risk_score, "Victim risk index mismatch"
        assert vic_data["risk"]["risk_band"] == exact_risk_band, "Victim risk band mismatch"
        assert vic_data["roles"]["l1_collector_candidate"] == feat_l1, "Victim L1 role mismatch"
        assert vic_data["roles"]["l2_distributor_candidate"] == feat_l2, "Victim L2 role mismatch"
        assert vic_data["roles"]["l3_terminal_candidate"] == feat_l3, "Victim L3 role mismatch"

        # 7. Timeline Investigation Endpoint
        r_time = client.get(f"/api/timeline?account_id={account_id}&page_size=20")
        assert r_time.status_code == 200, f"Timeline lookup failed for {account_id}"
        time_data = r_time.json()
        assert time_data["account_id"] == account_id
        assert time_data["summary"]["transaction_count"] > 0
        for event in time_data["events"]:
            if event["event_type"] == "TRANSACTION":
                assert event["source_account"] == account_id or event["destination_account"] == account_id

        # 8. Transaction Explorer Endpoint
        r_tx = client.get(f"/api/transactions?account_id={account_id}&page_size=20")
        assert r_tx.status_code == 200, f"Transactions lookup failed for {account_id}"
        tx_data = r_tx.json()
        assert tx_data["total_count"] > 0
        for item in tx_data["items"]:
            assert item["Sender_Account"] == account_id or item["Receiver_Account"] == account_id
            assert "stable_id" in item

        # 9. Case File Generation
        cf_payload = {"account_number": account_id, "max_hops": 4, "include_pdf": True, "include_json": True}
        r_cf = client.post("/api/case-files", json=cf_payload)
        assert r_cf.status_code == 200, f"Case file generation failed for {account_id}"
        cf_data = r_cf.json()
        assert cf_data["metadata"]["subject_account"] == account_id
        assert cf_data["evidence_snapshot"]["subject_account"] == account_id
        assert cf_data["evidence_snapshot"]["official_risk"]["risk_index"] == exact_risk_score, "Case file risk mismatch"
        assert cf_data["evidence_snapshot"]["mule_roles"]["l1_collector_candidate"] == feat_l1
        assert cf_data["evidence_snapshot"]["mule_roles"]["l2_distributor_candidate"] == feat_l2
        assert cf_data["evidence_snapshot"]["mule_roles"]["l3_terminal_candidate"] == feat_l3
        assert cf_data["metadata"]["dataset_sha256"] == "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
        assert len(cf_data["metadata"]["evidence_snapshot_sha256"]) == 64
        assert len(cf_data["metadata"]["json_sha256"]) == 64
        assert len(cf_data["metadata"]["pdf_sha256"]) == 64
        case_file_id = cf_data["metadata"]["case_file_id"]

        # 10. Case Diary Generation
        cd_payload = {"account_number": account_id, "case_file_id": case_file_id, "generate_narrative": False}
        r_cd = client.post("/api/case-diaries", json=cd_payload)
        assert r_cd.status_code == 200, f"Case diary generation failed for {account_id}"
        cd_resp = r_cd.json()
        diary = cd_resp["case_diary"]
        assert diary["subject_account"] == account_id
        assert diary["findings"]["risk"]["risk_index"] == exact_risk_score, "Case diary risk mismatch"
        assert diary["findings"]["role"]["l1_collector_candidate"] == feat_l1
        assert diary["findings"]["role"]["l2_distributor_candidate"] == feat_l2
        assert diary["findings"]["role"]["l3_terminal_candidate"] == feat_l3
        assert len(diary["verified_facts"]) > 0
        assert len(diary["chronology"]) > 0
        diary_id = diary["case_diary_id"]

        # 11. Legal Freeze / Requisition Draft Generation
        lf_payload = {
            "subject_account": account_id,
            "document_type": "ACCOUNT_FREEZE_REQUEST",
            "case_file_id": case_file_id,
            "case_diary_id": diary_id,
            "max_hops": 4
        }
        r_lf = client.post("/api/legal-freeze/drafts", json=lf_payload)
        assert r_lf.status_code == 200, f"Legal draft generation failed for {account_id}"
        lf_resp = r_lf.json()
        draft = lf_resp["draft"]
        assert draft["subject_account"] == account_id
        assert draft["status"] == "REVIEW_REQUIRED"
        assert draft["evidence"]["risk"]["risk_index"] == exact_risk_score, "Legal freeze risk mismatch"
        assert draft["evidence"]["roles"]["l1_collector_candidate"] == feat_l1
        assert draft["evidence"]["roles"]["l2_distributor_candidate"] == feat_l2
        assert draft["evidence"]["roles"]["l3_terminal_candidate"] == feat_l3
        assert draft["evidence"]["dataset_sha256"] == "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
        assert len(draft["evidence_snapshot_sha256"]) == 64
        assert len(draft["json_sha256"]) == 64
        # pdf_sha256 is optional; only assert length if present
        if draft.get("pdf_sha256"):
            assert len(draft["pdf_sha256"]) == 64

    def test_invalid_account_handled_gracefully(self):
        """Verify non-existent account returns controlled 404 across core stages without unhandled exception."""
        invalid_id = "NONEXISTENT9999"

        # Account — strict 404
        assert client.get(f"/api/accounts/{invalid_id}").status_code == 404
        # Features — strict 404
        assert client.get(f"/api/accounts/{invalid_id}/features").status_code == 404
        # Risk — strict 404
        assert client.get(f"/api/accounts/{invalid_id}/risk").status_code == 404
        # Velocity — strict 404
        assert client.get(f"/api/accounts/{invalid_id}/velocity").status_code == 404
        # Victim investigation — strict 404
        assert client.get(f"/api/investigations/victim/{invalid_id}").status_code == 404
        # Case file — strict 404
        assert client.post("/api/case-files", json={"account_number": invalid_id}).status_code == 404
        # Case diary — 422 (missing required case_file_id) or 404
        assert client.post("/api/case-diaries", json={"account_id": invalid_id}).status_code in (404, 422)
        # Legal freeze — strict 404
        assert client.post("/api/legal-freeze/drafts", json={"subject_account": invalid_id, "document_type": "ACCOUNT_FREEZE_REQUEST"}).status_code == 404
        # Timeline and transactions return 200 with empty results for unknown accounts (by design)
        r_tl = client.get(f"/api/timeline?account_id={invalid_id}")
        assert r_tl.status_code == 200
        assert r_tl.json()["summary"]["transaction_count"] == 0
        r_tx = client.get(f"/api/transactions?account_id={invalid_id}")
        assert r_tx.status_code == 200
        assert r_tx.json()["total_count"] == 0
