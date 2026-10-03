"""
Step 11 — Hardened Detection Evaluation Test Suite
Operation 'ABHEDYA-CHAKRA'

Comprehensive verification of:
1. no ground truth → AWAITING_GROUND_TRUTH without fabricated metrics
2. valid labelled accounts evaluation
3. duplicate ground-truth IDs detection
4. invalid / unrecognized labels handling
5. missing production accounts handling
6. TP/TN/FP/FN calculation
7. precision / recall / F1 / specificity / FPR mathematics
8. all-zero prediction policy boundary conditions
9. all-positive prediction policy boundary conditions
10. deterministic policy output and JSON/CSV artifact export
"""

import tempfile
import csv
import json
from pathlib import Path
import pytest

from scripts.evaluate_detection import (
    evaluate_ground_truth,
    compute_binary_metrics,
    parse_ground_truth_file,
    POLICY_REGISTRY,
)


class TestDetectionEvaluation:
    # -------------------------------------------------------------------------
    # Test 1: No ground truth -> AWAITING_GROUND_TRUTH
    # -------------------------------------------------------------------------
    def test_clean_status_when_ground_truth_absent(self):
        """Verifies that absence of ground truth produces explicit readiness message, not fabricated numbers."""
        non_existent = Path("data/non_existent_labels_xyz123.csv")
        res = evaluate_ground_truth(non_existent)
        assert res["status"] == "AWAITING_GROUND_TRUTH"
        assert res["ground_truth_status"] == "AWAITING_GROUND_TRUTH"
        assert res["ground_truth_supplied"] is False
        assert "Ground-truth labels were not available" in res["message"]
        assert "policies" in res
        # Check that candidate policy counts are reported without metrics
        assert "L1_candidate" in res["policies"]
        assert "Risk_GE_50" in res["policies"]
        for pol_name, pol_data in res["policies"].items():
            assert "predicted_positive_count" in pol_data
            assert "population_count" in pol_data
            assert "positive_rate" in pol_data
            assert "metrics" not in pol_data  # No fabricated TP/FP/TN/FN

    # -------------------------------------------------------------------------
    # Test 2: Valid labelled accounts
    # -------------------------------------------------------------------------
    def test_valid_labelled_accounts(self):
        """Verifies evaluation against a valid labeled ground-truth cohort."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tf:
            writer = csv.writer(tf)
            writer.writerow(["account_number", "label"])
            writer.writerow(["KKBK10000402", "mule"])
            writer.writerow(["AIRP10000595", "mule"])
            writer.writerow(["PYTM10001005", "regular"])
            writer.writerow(["PUNB10000806", "regular"])
            temp_path = Path(tf.name)

        try:
            res = evaluate_ground_truth(temp_path)
            assert res["status"] == "EVALUATED"
            assert res["ground_truth_supplied"] is True
            assert res["mule_labels_count"] == 2
            assert res["regular_labels_count"] == 2
            assert res["total_labeled_accounts"] == 4
            assert "L1_candidate" in res["policies"]
            assert "Risk_GE_50" in res["policies"]
            assert "PassThrough" in res["policies"]
            assert "Behavioral_AND_Role" in res["policies"]
            for pol_name, p_data in res["policies"].items():
                m = p_data["metrics"]
                assert "tp" in m and "tn" in m and "fp" in m and "fn" in m
                assert "precision" in m and "recall" in m and "f1" in m
                assert "specificity" in m and "false_positive_rate" in m
        finally:
            temp_path.unlink(missing_ok=True)

    # -------------------------------------------------------------------------
    # Test 3: Duplicate ground-truth IDs
    # -------------------------------------------------------------------------
    def test_duplicate_ground_truth_ids(self):
        """Verifies duplicate account numbers in ground truth are reported in cohort integrity."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tf:
            writer = csv.writer(tf)
            writer.writerow(["account_number", "label"])
            writer.writerow(["KKBK10000402", "mule"])
            writer.writerow(["KKBK10000402", "mule"])  # duplicate
            writer.writerow(["PYTM10001005", "regular"])
            temp_path = Path(tf.name)

        try:
            _, integrity = parse_ground_truth_file(temp_path)
            assert integrity["duplicate_id_count"] == 1
            assert "KKBK10000402" in integrity["duplicate_ids"]
            assert integrity["unique_account_ids"] == 2
        finally:
            temp_path.unlink(missing_ok=True)

    # -------------------------------------------------------------------------
    # Test 4: Invalid / unrecognized labels
    # -------------------------------------------------------------------------
    def test_invalid_labels(self):
        """Verifies non-standard labels are flagged in cohort integrity."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tf:
            writer = csv.writer(tf)
            writer.writerow(["account_number", "label"])
            writer.writerow(["KKBK10000402", "mule"])
            writer.writerow(["BARB10000427", "unknown_suspicious"])  # unrecognized
            writer.writerow(["PYTM10001005", "regular"])
            temp_path = Path(tf.name)

        try:
            labels, integrity = parse_ground_truth_file(temp_path)
            assert integrity["unrecognized_label_count"] == 1
            assert integrity["unrecognized_labels"][0]["account"] == "BARB10000427"
            assert integrity["unrecognized_labels"][0]["label"] == "unknown_suspicious"
            # Unrecognized account should not be in valid labels dict
            assert "BARB10000427" not in labels
            assert len(labels) == 2
        finally:
            temp_path.unlink(missing_ok=True)

    # -------------------------------------------------------------------------
    # Test 5: Missing production accounts
    # -------------------------------------------------------------------------
    def test_missing_production_accounts(self):
        """Verifies accounts not in the production database are detected and handled without error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as tf:
            writer = csv.writer(tf)
            writer.writerow(["account_number", "label"])
            writer.writerow(["KKBK10000402", "mule"])
            writer.writerow(["NON_EXISTENT_ACC_999999", "mule"])  # not in DB
            writer.writerow(["PYTM10001005", "regular"])
            temp_path = Path(tf.name)

        try:
            res = evaluate_ground_truth(temp_path)
            integ = res["cohort_integrity"]
            assert integ["ground_truth_missing_from_production_count"] >= 1
            assert "NON_EXISTENT_ACC_999999" in integ["ground_truth_missing_from_production"]
            # The missing mule account must be counted as FN across all policies
            for pol_data in res["policies"].values():
                assert pol_data["metrics"]["fn"] >= 1
        finally:
            temp_path.unlink(missing_ok=True)

    # -------------------------------------------------------------------------
    # Test 6: TP/TN/FP/FN calculation
    # -------------------------------------------------------------------------
    def test_tp_tn_fp_fn_calculation(self):
        """Verifies binary confusion matrix counters and totals."""
        m = compute_binary_metrics(tp=25, tn=75, fp=10, fn=5)
        assert m["tp"] == 25
        assert m["tn"] == 75
        assert m["fp"] == 10
        assert m["fn"] == 5
        assert m["total"] == 115

    # -------------------------------------------------------------------------
    # Test 7: Precision, Recall, F1, Specificity, FPR mathematics
    # -------------------------------------------------------------------------
    def test_precision_recall_f1_specificity_fpr(self):
        """Verifies mathematical correctness of all derived rate metrics."""
        # tp=40, fp=10 (precision = 40/50 = 0.8)
        # tp=40, fn=20 (recall = 40/60 = 0.6667)
        # tn=80, fp=10 (specificity = 80/90 = 0.8889, FPR = 10/90 = 0.1111)
        # f1 = 2 * (0.8 * 2/3) / (0.8 + 2/3) = 2 * (1.6/3) / (2.4/3 + 2/3) = (3.2/3) / (4.4/3) = 3.2 / 4.4 = 0.7273
        m = compute_binary_metrics(tp=40, tn=80, fp=10, fn=20)
        assert m["precision"] == 0.8
        assert m["recall"] == 0.6667
        assert m["f1"] == 0.7273
        assert m["specificity"] == 0.8889
        assert m["false_positive_rate"] == 0.1111
        assert round(m["specificity"] + m["false_positive_rate"], 4) == 1.0

    # -------------------------------------------------------------------------
    # Test 8: All-zero prediction policy boundary conditions
    # -------------------------------------------------------------------------
    def test_all_zero_prediction_policy(self):
        """When a policy predicts 0 positives (e.g. Risk >= 85), precision and recall must be 0.0 safely."""
        # tp=0, fp=0, fn=10, tn=90
        m = compute_binary_metrics(tp=0, tn=90, fp=0, fn=10)
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0
        assert m["specificity"] == 1.0
        assert m["false_positive_rate"] == 0.0

    # -------------------------------------------------------------------------
    # Test 9: All-positive prediction policy boundary conditions
    # -------------------------------------------------------------------------
    def test_all_positive_prediction_policy(self):
        """When a policy predicts everything as positive, recall=1.0 and specificity=0.0."""
        # tp=10, fp=90, fn=0, tn=0
        m = compute_binary_metrics(tp=10, tn=0, fp=90, fn=0)
        assert m["precision"] == 0.1
        assert m["recall"] == 1.0
        assert m["specificity"] == 0.0
        assert m["false_positive_rate"] == 1.0

    # -------------------------------------------------------------------------
    # Test 10: Deterministic policy output and JSON/CSV artifact export
    # -------------------------------------------------------------------------
    def test_deterministic_policy_output_and_export(self):
        """Verifies deterministic metadata, JSON and CSV export without random identifiers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "benchmark.json"
            csv_file = Path(tmpdir) / "benchmark.csv"

            # 1. Test awaiting ground truth export
            res_awaiting = evaluate_ground_truth(
                labels_path=Path(tmpdir) / "non_existent.csv",
                json_out=json_file,
                csv_out=csv_file,
            )
            assert json_file.exists()
            assert csv_file.exists()

            with open(json_file, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                assert data["status"] == "AWAITING_GROUND_TRUTH"
                assert "dataset_account_count" in data
                assert "evaluation_timestamp" in data

            with open(csv_file, "r", encoding="utf-8") as cf:
                reader = csv.DictReader(cf)
                rows = list(reader)
                assert len(rows) == len(POLICY_REGISTRY)
                assert rows[0]["ground_truth_status"] == "AWAITING_GROUND_TRUTH"

            # 2. Test evaluated export with fixture
            gt_file = Path(tmpdir) / "gt.csv"
            with open(gt_file, "w", encoding="utf-8", newline="") as gf:
                writer = csv.writer(gf)
                writer.writerow(["account_number", "label"])
                writer.writerow(["KKBK10000402", "1"])
                writer.writerow(["PYTM10001005", "0"])

            res_evaluated = evaluate_ground_truth(
                labels_path=gt_file,
                json_out=json_file,
                csv_out=csv_file,
            )
            assert res_evaluated["status"] == "EVALUATED"

            with open(json_file, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                assert data["status"] == "EVALUATED"
                assert "cohort_integrity" in data
                assert data["code_version"] == "0.1.0-base"

            with open(csv_file, "r", encoding="utf-8") as cf:
                reader = csv.DictReader(cf)
                rows = list(reader)
                assert len(rows) == len(POLICY_REGISTRY)
                assert "precision" in rows[0]
                assert "recall" in rows[0]
                assert "false_positive_rate" in rows[0]
