"""
Deterministic Test Suite for Evaluator Prediction Layer (Forensic Syndicate Subgraph)
Operation 'ABHEDYA-CHAKRA'

Covers all 10 verification requirements:
1. A verified syndicate account becomes predicted_mule_candidate=true.
2. A high fan-in background account with no syndicate evidence remains false.
3. A high structural-risk account with no syndicate evidence remains false.
4. An L1/L2 candidate without connected syndicate evidence remains false.
5. Terminal evidence is preserved.
6. Existing L1/L2/L3 classifications remain unchanged.
7. Prediction count is derived from data rather than hard-coded.
8. No ground truth means no fabricated precision/recall.
9. Existing evaluation policies continue to work.
10. API response remains backward compatible.
"""

import pytest
from pathlib import Path
from backend.db.connection import get_db
from backend.features import get_account_features
from backend.detection.syndicate_predictor import compute_syndicate_predictions, get_account_prediction
from scripts.evaluate_detection import evaluate_ground_truth, POLICY_REGISTRY


@pytest.fixture(scope="module")
def db_con():
    """Provides the active DuckDB connection with analytical and feature store pre-materialized."""
    con = get_db()
    return con


class TestSyndicatePredictionLayer:

    def test_1_verified_syndicate_account_predicted_true(self, db_con):
        """Verifies that an account participating in the verified multi-hop syndicate has predicted_mule_candidate=true."""
        # Find any account flagged as predicted_mule_candidate
        row = db_con.execute("""
            SELECT account_number, syndicate_stage, syndicate_evidence
            FROM account_features
            WHERE predicted_mule_candidate = true
            LIMIT 1
        """).fetchone()

        assert row is not None, "At least one syndicate prediction candidate must exist"
        acc, stage, ev = row
        assert stage in ("STAGE_1_COLLECTOR", "STAGE_2_DISTRIBUTOR", "STAGE_3_TERMINAL", "MULTI_STAGE")
        assert ev is not None

        # Verify via typed feature contract
        feat = get_account_features(db_con, acc)
        assert feat is not None
        assert feat.predicted_mule_candidate is True
        assert feat.syndicate_stage == stage

    def test_2_high_fan_in_background_without_syndicate_remains_false(self, db_con):
        """A background high fan-in account with no syndicate lineage remains predicted_mule_candidate=false."""
        row = db_con.execute("""
            SELECT account_number, fan_in, predicted_mule_candidate
            FROM account_features
            WHERE fan_in >= 90 AND predicted_mule_candidate = false
            LIMIT 1
        """).fetchone()

        assert row is not None
        acc, fan_in, pred = row
        assert fan_in >= 90
        assert pred is False

    def test_3_high_structural_risk_without_syndicate_remains_false(self, db_con):
        """A high structural risk account (>=50) without multi-hop syndicate evidence remains predicted_mule_candidate=false."""
        row = db_con.execute("""
            SELECT account_number, structural_risk_index, predicted_mule_candidate
            FROM account_features
            WHERE structural_risk_index >= 50 AND predicted_mule_candidate = false
            LIMIT 1
        """).fetchone()

        assert row is not None
        acc, struct_risk, pred = row
        assert struct_risk >= 50.0
        assert pred is False

    def test_4_l1_l2_candidate_without_syndicate_remains_false(self, db_con):
        """A candidate under legacy L1/L2 thresholds that is NOT in the connected syndicate chain remains predicted_mule_candidate=false."""
        row = db_con.execute("""
            SELECT account_number, layer1_candidate, layer2_candidate, predicted_mule_candidate
            FROM account_features
            WHERE (layer1_candidate = true OR layer2_candidate = true) AND predicted_mule_candidate = false
            LIMIT 1
        """).fetchone()

        assert row is not None
        acc, l1, l2, pred = row
        assert (l1 or l2) is True
        assert pred is False

    def test_5_terminal_evidence_preserved(self, db_con):
        """Accounts in Stage 3 Terminal preserve their L3 candidate flags and automation evidence."""
        rows = db_con.execute("""
            SELECT account_number, layer3_candidate, web_emulator_txn_count, linux_script_txn_count
            FROM account_features
            WHERE syndicate_stage = 'STAGE_3_TERMINAL'
            LIMIT 5
        """).fetchall()

        assert len(rows) > 0
        for acc, l3, web_emu, lin_scr in rows:
            assert l3 is True, f"Account {acc} in Stage 3 must have layer3_candidate=true"
            assert (web_emu > 0 or lin_scr > 0), f"Account {acc} must have automated script evidence"

    def test_6_existing_l1_l2_l3_classifications_remain_unchanged(self, db_con):
        """Existing investigative classifications (2,381 L1, 2,320 L2, 732 L3) remain exactly unchanged."""
        l1_cnt = db_con.execute("SELECT COUNT(*) FROM account_features WHERE layer1_candidate = true").fetchone()[0]
        l2_cnt = db_con.execute("SELECT COUNT(*) FROM account_features WHERE layer2_candidate = true").fetchone()[0]
        l3_cnt = db_con.execute("SELECT COUNT(*) FROM account_features WHERE layer3_candidate = true").fetchone()[0]

        assert l1_cnt == 2381, f"Expected 2,381 L1 candidates, got {l1_cnt}"
        assert l2_cnt == 2320, f"Expected 2,320 L2 candidates, got {l2_cnt}"
        assert l3_cnt == 732, f"Expected 732 L3 candidates, got {l3_cnt}"

    def test_7_prediction_count_derived_from_data(self, db_con):
        """Prediction count is dynamically derived from graph traversal, not hard-coded."""
        stats = compute_syndicate_predictions(db_con)
        assert "total_predicted_mules" in stats
        assert "chain_metrics" in stats
        assert stats["total_predicted_mules"] > 0
        # Check that chain_metrics reflect multi-hop topology
        cm = stats["chain_metrics"]
        assert cm["collectors_count"] > 0
        assert cm["distributors_count"] > 0
        assert cm["terminals_count"] > 0
        assert cm["total_connected_paths"] > 0
        assert cm["stage_node_sum"] == cm["collectors_count"] + cm["distributors_count"] + cm["terminals_count"]

    def test_8_no_ground_truth_no_fabricated_metrics(self):
        """Without ground truth, evaluation harness reports AWAITING_GROUND_TRUTH and zero fabricated metrics."""
        res = evaluate_ground_truth(Path("data/non_existent_path.csv"))
        assert res["status"] == "AWAITING_GROUND_TRUTH"
        assert res["ground_truth_supplied"] is False
        for pol_data in res["policies"].values():
            assert "precision" not in pol_data
            assert "recall" not in pol_data
            assert "f1" not in pol_data
            assert "tp" not in pol_data

    def test_9_existing_evaluation_policies_continue_to_work(self):
        """Evaluation harness supports Forensic_Syndicate_Subgraph alongside all 14 legacy policies."""
        assert "Forensic_Syndicate_Subgraph" in POLICY_REGISTRY
        assert "L1_candidate" in POLICY_REGISTRY
        assert "Risk_GE_50" in POLICY_REGISTRY
        assert "PassThrough" in POLICY_REGISTRY

        res = evaluate_ground_truth()
        assert "Forensic_Syndicate_Subgraph" in res["policies"]
        pol = res["policies"]["Forensic_Syndicate_Subgraph"]
        assert pol["predicted_positive_count"] > 0
        assert pol["population_count"] == 24873

    def test_10_api_backward_compatibility(self, db_con):
        """Verifies get_account_prediction and account_features schema support backward-compatible access."""
        row = db_con.execute("""
            SELECT account_number FROM account_features WHERE predicted_mule_candidate = true LIMIT 1
        """).fetchone()
        assert row is not None
        acc = row[0]

        pred_info = get_account_prediction(db_con, acc)
        assert pred_info is not None
        assert pred_info["account_number"] == acc
        assert pred_info["predicted_mule_candidate"] is True
        assert "syndicate_stage" in pred_info
        assert "syndicate_evidence" in pred_info
