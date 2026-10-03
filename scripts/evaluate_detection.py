"""
Step 11 — Detection Evaluation Harness (Hardened Benchmark Engine)
Operation 'ABHEDYA-CHAKRA'

Evaluates detector candidate policies against ground-truth labels if provided.
Expected format of ground-truth CSV:
account_number,label
(where label is 'mule' or 'regular', '1' or '0', etc.)

FORENSIC INTEGRITY:
- If no ground-truth file exists, NO accuracy is fabricated (status: AWAITING_GROUND_TRUTH).
- Evaluates candidate policies objectively without automatic threshold optimization.
- Candidate policies are investigative hypotheses, NOT official final declarations of criminality.
"""

import sys
import csv
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
import duckdb

# Ensure backend can be imported
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.db.connection import get_db, get_dataset_path

# =============================================================================
# 1. Candidate Policy Registry (Evaluation Policies Only - Production Frozen)
# =============================================================================
POLICY_REGISTRY: Dict[str, Dict[str, str]] = {
    # Existing Role Candidate Policies
    "L1_candidate": {
        "definition": "layer1_candidate == true",
        "description": "Layer 1 Collector Candidate (inbound credit aggregation)",
        "sql": "layer1_candidate = true",
    },
    "L2_candidate": {
        "definition": "layer2_candidate == true",
        "description": "Layer 2 Distributor Candidate (rapid outbound dispersion)",
        "sql": "layer2_candidate = true",
    },
    "L3_candidate": {
        "definition": "layer3_candidate == true",
        "description": "Layer 3 Terminal Candidate (sink absorption / automated drain)",
        "sql": "layer3_candidate = true",
    },
    "Any_Mule_Role": {
        "definition": "layer1_candidate OR layer2_candidate OR layer3_candidate",
        "description": "Any classified role candidate (L1 or L2 or L3)",
        "sql": "(layer1_candidate = true OR layer2_candidate = true OR layer3_candidate = true)",
    },
    # Composite Risk Threshold Policies (Descriptive Benchmark-Only)
    "Risk_GE_35": {
        "definition": "mule_risk_index >= 35",
        "description": "Composite Mule Risk Index >= 35.0 (Moderate+ triage threshold)",
        "sql": "mule_risk_index >= 35.0",
    },
    "Risk_GE_40": {
        "definition": "mule_risk_index >= 40",
        "description": "Composite Mule Risk Index >= 40.0 (Elevated composite threshold)",
        "sql": "mule_risk_index >= 40.0",
    },
    "Risk_GE_45": {
        "definition": "mule_risk_index >= 45",
        "description": "Composite Mule Risk Index >= 45.0 (Upper moderate threshold)",
        "sql": "mule_risk_index >= 45.0",
    },
    "Risk_GE_50": {
        "definition": "mule_risk_index >= 50",
        "description": "Composite Mule Risk Index >= 50.0 (High Risk Band cutoff)",
        "sql": "mule_risk_index >= 50.0",
    },
    "Risk_GE_55": {
        "definition": "mule_risk_index >= 55",
        "description": "Composite Mule Risk Index >= 55.0 (High Risk upper tier)",
        "sql": "mule_risk_index >= 55.0",
    },
    "Risk_GE_60": {
        "definition": "mule_risk_index >= 60",
        "description": "Composite Mule Risk Index >= 60.0 (High Risk peak tier)",
        "sql": "mule_risk_index >= 60.0",
    },
    "Risk_GE_70": {
        "definition": "mule_risk_index >= 70",
        "description": "Composite Mule Risk Index >= 70.0 (Legacy cutoff; 0 accounts in callset)",
        "sql": "mule_risk_index >= 70.0",
    },
    "Risk_GE_85": {
        "definition": "mule_risk_index >= 85",
        "description": "Composite Mule Risk Index >= 85.0 (Extreme risk cutoff; 0 accounts in callset)",
        "sql": "mule_risk_index >= 85.0",
    },
    # Behavioral Conjunction Policy
    "Behavioral_AND_Role": {
        "definition": "behavioral_risk_index >= 50 AND (layer1_candidate OR layer2_candidate OR layer3_candidate)",
        "description": "Elevated behavioral risk (>=50) conjoined with classified role",
        "sql": "behavioral_risk_index >= 50.0 AND (layer1_candidate = true OR layer2_candidate = true OR layer3_candidate = true)",
    },
    # Temporal Pass-Through Policy (Isolated)
    "PassThrough": {
        "definition": "pass_through_candidate == true",
        "description": "Qualifying 3-15 minute pass-through velocity candidate",
        "sql": "pass_through_candidate = true",
    },
    # Primary Evaluator Prediction Policy
    "Forensic_Syndicate_Subgraph": {
        "definition": "predicted_mule_candidate == true",
        "description": "Evaluator Prediction Set: Verified non-victim nodes in Victim -> Collector -> Distributor -> Terminal multi-hop chain",
        "sql": "predicted_mule_candidate = true",
    },
}

POSITIVE_LABEL_SYNONYMS = {"mule", "1", "true", "yes", "positive", "mule_account", "mule account"}
NEGATIVE_LABEL_SYNONYMS = {"regular", "0", "false", "no", "negative", "normal", "non_mule", "non-mule"}


def compute_binary_metrics(tp: int, tn: int, fp: int, fn: int) -> Dict[str, Any]:
    """
    Computes precision, recall, F1, specificity, and false_positive_rate
    safely without division by zero.
    """
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "specificity": round(specificity, 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "total": tp + tn + fp + fn,
    }


def parse_ground_truth_file(labels_path: Path) -> Tuple[Dict[str, bool], Dict[str, Any]]:
    """
    Parses and audits the ground-truth CSV file for cohort integrity.
    Returns:
        labels: Dict mapping validated account_number -> is_mule (bool)
        integrity_report: Dict of integrity findings (duplicates, unrecognized labels, etc.)
    """
    labels: Dict[str, bool] = {}
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []
    unrecognized_labels: List[Dict[str, str]] = []
    total_rows = 0
    mule_count = 0
    regular_count = 0

    with open(labels_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            acc = row.get("account_number") or row.get("account_id") or row.get("account")
            if not acc:
                continue
            acc = acc.strip().upper()

            if acc in seen_ids:
                duplicate_ids.append(acc)
            seen_ids.add(acc)

            raw_label = (row.get("label") or "").strip().lower()
            if raw_label in POSITIVE_LABEL_SYNONYMS:
                labels[acc] = True
                mule_count += 1
            elif raw_label in NEGATIVE_LABEL_SYNONYMS:
                labels[acc] = False
                regular_count += 1
            else:
                unrecognized_labels.append({"account": acc, "label": raw_label})

    integrity_report = {
        "total_rows_read": total_rows,
        "unique_account_ids": len(seen_ids),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids[:50],
        "unrecognized_label_count": len(unrecognized_labels),
        "unrecognized_labels": unrecognized_labels[:50],
        "actual_positive_count": mule_count,
        "actual_negative_count": regular_count,
    }

    return labels, integrity_report


def evaluate_ground_truth(
    labels_path: Optional[Path] = None,
    con: Optional[duckdb.DuckDBPyConnection] = None,
    json_out: Optional[Path] = None,
    csv_out: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates detector candidate policies against ground-truth labels if provided.
    If no file or non-existent file is passed, returns status: AWAITING_GROUND_TRUTH.
    Writes JSON and CSV reports if paths are provided.
    """
    if con is None:
        con = get_db()

    dataset_path_str = str(get_dataset_path())
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    # Pre-fetch total production account count
    total_production_accounts = con.execute("SELECT COUNT(*) FROM account_features").fetchone()[0]

    # Pre-fetch predicted positive counts across all policies in the registry
    population_counts: Dict[str, int] = {}
    for pol_name, pol_spec in POLICY_REGISTRY.items():
        cnt = con.execute(f"SELECT COUNT(*) FROM account_features WHERE {pol_spec['sql']}").fetchone()[0]
        population_counts[pol_name] = cnt

    # Check ground-truth presence
    if labels_path is None or not Path(labels_path).exists():
        report = {
            "status": "AWAITING_GROUND_TRUTH",
            "ground_truth_status": "AWAITING_GROUND_TRUTH",
            "message": (
                "Ground-truth labels were not available in the supplied production dataset; "
                "therefore precision/recall/F1 are not reported. "
                "The evaluation harness is implemented and ready for the official labels."
            ),
            "labels_file": str(labels_path) if labels_path else None,
            "ground_truth_supplied": False,
            "dataset_path": dataset_path_str,
            "dataset_account_count": total_production_accounts,
            "evaluation_timestamp": timestamp_iso,
            "code_version": "0.1.0-base",
            "policies": {
                name: {
                    "policy_name": name,
                    "definition": spec["definition"],
                    "description": spec["description"],
                    "predicted_positive_count": population_counts[name],
                    "population_count": total_production_accounts,
                    "positive_rate": round(population_counts[name] / total_production_accounts, 4) if total_production_accounts > 0 else 0.0,
                }
                for name, spec in POLICY_REGISTRY.items()
            }
        }

        _write_output_files(report, json_out, csv_out, ground_truth_supplied=False)
        return report

    labels_file = Path(labels_path)
    labels, integrity = parse_ground_truth_file(labels_file)

    # Cross-reference with production accounts in account_features
    prod_accounts = set(r[0] for r in con.execute("SELECT account_number FROM account_features").fetchall())
    gt_accounts = set(labels.keys())

    gt_missing_from_prod = gt_accounts - prod_accounts
    prod_absent_from_gt = prod_accounts - gt_accounts

    integrity["ground_truth_missing_from_production_count"] = len(gt_missing_from_prod)
    integrity["ground_truth_missing_from_production"] = list(gt_missing_from_prod)[:50]
    integrity["production_absent_from_ground_truth_count"] = len(prod_absent_from_gt)

    # Vectorized policy sets for high performance
    policy_positive_sets: Dict[str, Set[str]] = {}
    for pol_name, pol_spec in POLICY_REGISTRY.items():
        pos_accs = set(r[0] for r in con.execute(f"SELECT account_number FROM account_features WHERE {pol_spec['sql']}").fetchall())
        policy_positive_sets[pol_name] = pos_accs

    # Compute confusion matrices for all policies
    policy_metrics: Dict[str, Dict[str, Any]] = {}
    criteria_counters: Dict[str, Dict[str, int]] = {
        name: {"tp": 0, "tn": 0, "fp": 0, "fn": 0} for name in POLICY_REGISTRY
    }

    for acc, is_actual_mule in labels.items():
        is_in_prod = acc in prod_accounts
        for pol_name in POLICY_REGISTRY:
            if not is_in_prod:
                # If account is not in production dataset:
                # if actual mule -> false negative (missed), if actual regular -> true negative
                if is_actual_mule:
                    criteria_counters[pol_name]["fn"] += 1
                else:
                    criteria_counters[pol_name]["tn"] += 1
                continue

            is_pred_pos = acc in policy_positive_sets[pol_name]

            if is_actual_mule and is_pred_pos:
                criteria_counters[pol_name]["tp"] += 1
            elif not is_actual_mule and not is_pred_pos:
                criteria_counters[pol_name]["tn"] += 1
            elif not is_actual_mule and is_pred_pos:
                criteria_counters[pol_name]["fp"] += 1
            else:
                criteria_counters[pol_name]["fn"] += 1

    policy_results: Dict[str, Dict[str, Any]] = {}
    for pol_name, counts in criteria_counters.items():
        bm = compute_binary_metrics(**counts)
        policy_results[pol_name] = {
            "policy_name": pol_name,
            "definition": POLICY_REGISTRY[pol_name]["definition"],
            "description": POLICY_REGISTRY[pol_name]["description"],
            "predicted_positive_count": population_counts[pol_name],
            "population_count": total_production_accounts,
            "positive_rate": round(population_counts[pol_name] / total_production_accounts, 4) if total_production_accounts > 0 else 0.0,
            "metrics": bm,
        }

    report = {
        "status": "EVALUATED",
        "ground_truth_supplied": True,
        "ground_truth_path": str(labels_file),
        "dataset_path": dataset_path_str,
        "dataset_account_count": total_production_accounts,
        "evaluation_timestamp": timestamp_iso,
        "code_version": "0.1.0-base",
        "cohort_integrity": integrity,
        # Backward compatibility for existing assertions:
        "mule_labels_count": integrity["actual_positive_count"],
        "regular_labels_count": integrity["actual_negative_count"],
        "total_labeled_accounts": len(labels),
        "expected_1500_mule": integrity["actual_positive_count"] == 1500,
        "expected_23500_regular": integrity["actual_negative_count"] == 23500,
        "policies": policy_results,
        "metrics": {name: p["metrics"] for name, p in policy_results.items()},
    }

    _write_output_files(report, json_out, csv_out, ground_truth_supplied=True)
    return report


def _write_output_files(
    report: Dict[str, Any],
    json_out: Optional[Path],
    csv_out: Optional[Path],
    ground_truth_supplied: bool,
) -> None:
    """Writes machine-readable JSON and CSV summary tables if requested."""
    if json_out:
        out_path = Path(json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    if csv_out:
        out_path = Path(csv_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if ground_truth_supplied:
                writer.writerow([
                    "policy_name",
                    "definition",
                    "predicted_positive_count",
                    "tp",
                    "tn",
                    "fp",
                    "fn",
                    "precision",
                    "recall",
                    "f1",
                    "specificity",
                    "false_positive_rate",
                ])
                for pol_name, data in report["policies"].items():
                    m = data["metrics"]
                    writer.writerow([
                        pol_name,
                        data["definition"],
                        data["predicted_positive_count"],
                        m["tp"],
                        m["tn"],
                        m["fp"],
                        m["fn"],
                        m["precision"],
                        m["recall"],
                        m["f1"],
                        m["specificity"],
                        m["false_positive_rate"],
                    ])
            else:
                writer.writerow([
                    "policy_name",
                    "definition",
                    "predicted_positive_count",
                    "population_count",
                    "positive_rate",
                    "ground_truth_status",
                ])
                for pol_name, data in report["policies"].items():
                    writer.writerow([
                        pol_name,
                        data["definition"],
                        data["predicted_positive_count"],
                        data["population_count"],
                        data["positive_rate"],
                        "AWAITING_GROUND_TRUTH",
                    ])


def main():
    parser = argparse.ArgumentParser(description="Operation Abhedya-Chakra Detection Evaluation Harness")
    parser.add_argument("labels_path", nargs="?", default=None, help="Path to ground-truth labels CSV")
    parser.add_argument("--json-out", dest="json_out", default=None, help="Path to write JSON benchmark report")
    parser.add_argument("--csv-out", dest="csv_out", default=None, help="Path to write summary CSV table")
    args = parser.parse_args()

    default_path = project_root / "data" / "ground_truth_labels.csv"
    labels_file = Path(args.labels_path) if args.labels_path else default_path

    report = evaluate_ground_truth(
        labels_path=labels_file,
        json_out=Path(args.json_out) if args.json_out else None,
        csv_out=Path(args.csv_out) if args.csv_out else None,
    )

    print("=== Detection Evaluation Harness Report ===")
    print(f"Status: {report['status']}")
    print(f"Ground Truth Supplied: {report.get('ground_truth_supplied', False)}")
    if report.get("ground_truth_supplied"):
        integ = report["cohort_integrity"]
        print(f"Total Valid Accounts Labeled: {report['total_labeled_accounts']}")
        print(f"Actual Positive (Mule): {integ['actual_positive_count']}")
        print(f"Actual Negative (Regular): {integ['actual_negative_count']}")
        print(f"Duplicates Detected: {integ['duplicate_id_count']}")
        print(f"Unrecognized Labels: {integ['unrecognized_label_count']}")
        print("\n--- Candidate Policy Benchmark Metrics ---")
        for pol_name, pol_data in report["policies"].items():
            m = pol_data["metrics"]
            print(f"[{pol_name}] P={m['precision']:.4f}, R={m['recall']:.4f}, F1={m['f1']:.4f}, FPR={m['false_positive_rate']:.4f} (TP={m['tp']}, FP={m['fp']}, PredPos={pol_data['predicted_positive_count']})")
    else:
        print(f"Message: {report.get('message')}")
        print("\n--- Pre-Materialized Candidate Policy Counts ---")
        for pol_name, pol_data in report["policies"].items():
            print(f"[{pol_name}] Count={pol_data['predicted_positive_count']} ({pol_data['positive_rate']*100:.2f}%)")


if __name__ == "__main__":
    main()
