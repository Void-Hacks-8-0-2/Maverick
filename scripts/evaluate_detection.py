"""
Step 11 — Detection Evaluation Harness
Operation 'ABHEDYA-CHAKRA'

Evaluates detector predictions against ground-truth labels if provided.
Expected format of ground-truth CSV:
account_number,label
(where label is 'mule' or 'regular')

When official labels are provided:
- Validates 1,500 mule and 23,500 regular accounts if present.
- Calculates TP, TN, FP, FN, Precision, Recall, F1, and Specificity across:
  * L1 candidate
  * L2 candidate
  * L3 candidate
  * Any Mule role candidate (L1 or L2 or L3)
  * Mule Risk Index thresholds (>= 50, >= 70, >= 85)

FORENSIC INTEGRITY:
If no ground-truth file exists, NO accuracy is fabricated.
The script reports that the harness is ready for official labels.
"""

import sys
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb

# Ensure backend can be imported
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.db.connection import get_db
from backend.features import get_account_features


def compute_binary_metrics(tp: int, tn: int, fp: int, fn: int) -> Dict[str, Any]:
    """Computes precision, recall, F1, specificity safely without division by zero."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),
        "total": tp + tn + fp + fn,
    }


def evaluate_ground_truth(labels_path: Path, con: Optional[duckdb.DuckDBPyConnection] = None) -> Dict[str, Any]:
    """
    Evaluates detector performance against a ground-truth CSV file.
    Returns metrics dictionary, or a readiness message if the file is absent.
    """
    if not labels_path.exists():
        return {
            "status": "AWAITING_GROUND_TRUTH",
            "message": (
                "Ground-truth labels were not available in the supplied production dataset; "
                "therefore precision/recall/F1 are not reported. "
                "The evaluation harness is implemented and ready for the official labels."
            ),
            "labels_file": str(labels_path),
            "ground_truth_supplied": False,
        }

    # Load labels
    labels: Dict[str, bool] = {}  # account_number -> is_mule
    mule_count = 0
    regular_count = 0

    with open(labels_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            acc = row.get("account_number") or row.get("account_id") or row.get("account")
            label_str = (row.get("label") or "").strip().lower()
            if not acc:
                continue
            is_mule = label_str in ("mule", "1", "true", "yes")
            labels[acc] = is_mule
            if is_mule:
                mule_count += 1
            else:
                regular_count += 1

    if con is None:
        con = get_db()

    # Confusion matrix counters
    criteria = {
        "L1_candidate": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "L2_candidate": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "L3_candidate": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "Any_Mule_Role": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "Risk_GE_50": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "Risk_GE_70": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
        "Risk_GE_85": {"tp": 0, "tn": 0, "fp": 0, "fn": 0},
    }

    # Evaluate each labeled account
    for acc, is_actual_mule in labels.items():
        feat = get_account_features(con, acc)
        if feat is None:
            # Not in dataset: if mule -> FN, if regular -> TN
            for crit in criteria.values():
                if is_actual_mule:
                    crit["fn"] += 1
                else:
                    crit["tn"] += 1
            continue

        pred_l1 = feat.layer1_candidate
        pred_l2 = feat.layer2_candidate
        pred_l3 = feat.layer3_candidate
        pred_any = pred_l1 or pred_l2 or pred_l3
        risk = feat.mule_risk_index

        preds = {
            "L1_candidate": pred_l1,
            "L2_candidate": pred_l2,
            "L3_candidate": pred_l3,
            "Any_Mule_Role": pred_any,
            "Risk_GE_50": risk >= 50.0,
            "Risk_GE_70": risk >= 70.0,
            "Risk_GE_85": risk >= 85.0,
        }

        for k, is_pred_positive in preds.items():
            if is_actual_mule and is_pred_positive:
                criteria[k]["tp"] += 1
            elif not is_actual_mule and not is_pred_positive:
                criteria[k]["tn"] += 1
            elif not is_actual_mule and is_pred_positive:
                criteria[k]["fp"] += 1
            else:
                criteria[k]["fn"] += 1

    results = {
        "status": "EVALUATED",
        "ground_truth_supplied": True,
        "mule_labels_count": mule_count,
        "regular_labels_count": regular_count,
        "total_labeled_accounts": len(labels),
        "expected_1500_mule": mule_count == 1500,
        "expected_23500_regular": regular_count == 23500,
        "metrics": {k: compute_binary_metrics(**counts) for k, counts in criteria.items()}
    }

    return results


if __name__ == "__main__":
    default_path = project_root / "data" / "ground_truth_labels.csv"
    labels_file = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    report = evaluate_ground_truth(labels_file)
    print("=== Detection Evaluation Harness Report ===")
    for k, v in report.items():
        print(f"{k}: {v}")
