"""
Step 11 — Detection Evaluation Test Suite
Operation 'ABHEDYA-CHAKRA'

Tests:
1. When ground-truth labels are absent, the harness cleanly reports readiness without fabricating metrics.
2. Binary metrics calculation (TP, TN, FP, FN, precision, recall, F1, specificity).
3. Evaluator validation with a temporary test fixture to verify correct evaluation execution.
"""

import tempfile
import csv
from pathlib import Path
import pytest

from scripts.evaluate_detection import evaluate_ground_truth, compute_binary_metrics


class TestDetectionEvaluation:
    def test_clean_status_when_ground_truth_absent(self):
        """Verifies that absence of ground truth produces explicit readiness message, not fabricated numbers."""
        non_existent = Path("data/non_existent_labels_xyz123.csv")
        res = evaluate_ground_truth(non_existent)
        assert res["status"] == "AWAITING_GROUND_TRUTH"
        assert res["ground_truth_supplied"] is False
        assert "Ground-truth labels were not available" in res["message"]

    def test_compute_binary_metrics_math(self):
        """Verifies mathematical correctness of TP/TN/FP/FN/precision/recall/F1/specificity."""
        # 10 TP, 10 TN, 0 FP, 0 FN -> perfect 1.0
        m = compute_binary_metrics(tp=10, tn=10, fp=0, fn=0)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["specificity"] == 1.0

        # Division by zero handled gracefully (0 predictions)
        m_zero = compute_binary_metrics(tp=0, tn=0, fp=0, fn=0)
        assert m_zero["precision"] == 0.0
        assert m_zero["recall"] == 0.0
        assert m_zero["f1"] == 0.0
        assert m_zero["specificity"] == 0.0

        # Partial precision/recall
        # TP=50, FP=50 (precision = 0.5), FN=50 (recall = 0.5) -> F1 = 0.5
        m_part = compute_binary_metrics(tp=50, tn=100, fp=50, fn=50)
        assert m_part["precision"] == 0.5
        assert m_part["recall"] == 0.5
        assert m_part["f1"] == 0.5
        assert m_part["specificity"] == round(100 / 150, 4)

    def test_harness_with_synthetic_fixture(self):
        """Creates a temporary labeled fixture of benchmark accounts and verifies execution."""
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
            assert "L1_candidate" in res["metrics"]
            assert "Risk_GE_70" in res["metrics"]
            for crit, m in res["metrics"].items():
                assert "tp" in m and "fp" in m and "f1" in m
        finally:
            temp_path.unlink(missing_ok=True)
