#!/usr/bin/env python3
"""
OPERATION "ABHEDYA-CHAKRA"
Forensic Dataset Inspection & Profiler Tool (P0 Step 1)

Authoritative Reference: Void Hacks() 8.0 Problem Statement
Architecture Reference: Blueprint v2.0
"""

import os
import sys
import json
import time
import argparse
import hashlib
import platform
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import psutil
import duckdb

PROFILER_VERSION = "2.0.0-forensic"

EXPECTED_SCHEMA = [
    "Transaction_ID",
    "Sender_Account",
    "Receiver_Account",
    "Sender_IFSC",
    "Receiver_IFSC",
    "Amount",
    "Timestamp",
    "Payment_Mode",
    "Narration",
    "IP_Address",
    "Device_Type"
]

CANDIDATE_EXTENSIONS = [".csv", ".csv.gz", ".parquet", ".parquet.gz", ".sqlite", ".db", ".duckdb"]


def check_schema_match(file_path: Path) -> bool:
    """Quick check if a file matches the expected transaction schema."""
    try:
        ext = file_path.suffix.lower()
        con = duckdb.connect(database=":memory:")
        if ext in [".csv", ".txt"]:
            cols = [desc[0] for desc in con.execute(f"SELECT * FROM read_csv('{file_path}', header=true, sample_size=50) LIMIT 0").description]
        elif ext in [".parquet"]:
            cols = [desc[0] for desc in con.execute(f"SELECT * FROM read_parquet('{file_path}') LIMIT 0").description]
        else:
            return False
        # If it has at least 5 of the required columns, consider it a real candidate
        matched = set(cols).intersection(set(EXPECTED_SCHEMA))
        return len(matched) >= 5
    except Exception:
        return False


def discover_datasets(search_paths: List[str]) -> List[Dict[str, Any]]:
    """Scan candidate directories for transaction data and ground-truth label files."""
    candidates = []
    seen = set()
    for sp in search_paths:
        p = Path(sp).resolve()
        if not p.exists():
            continue
        if p.is_file():
            files = [p]
        else:
            files = [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in CANDIDATE_EXTENSIONS]
        
        for f in files:
            norm = str(f.resolve())
            if norm in seen:
                continue
            seen.add(norm)
            # Skip python venvs and test directories from auto-discovery
            if any(k in norm.lower() for k in ["venv", ".venv", "site-packages", "tests", "fixtures"]):
                continue
            size = f.stat().st_size
            candidates.append({
                "path": str(f),
                "name": f.name,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "extension": f.suffix.lower(),
                "is_likely_ground_truth": any(k in f.name.lower() for k in ["ground_truth", "label", "mule", "truth"]),
                "matches_schema": check_schema_match(f)
            })
    return candidates


def discover_ground_truth(search_paths: List[str]) -> Dict[str, Any]:
    """Search specifically for official ground-truth labels."""
    candidates = discover_datasets(search_paths)
    gt_candidates = [c for c in candidates if c["is_likely_ground_truth"]]
    if not gt_candidates:
        return {
            "ground_truth_found": False,
            "status": "Ground truth unavailable in repository. No synthetic labels will be substituted for evaluation.",
            "candidates": []
        }
    return {
        "ground_truth_found": True,
        "status": f"Found {len(gt_candidates)} potential ground-truth candidate file(s).",
        "candidates": gt_candidates
    }


def compute_file_hash(file_path: Path, max_bytes: int = 500 * 1024 * 1024) -> str:
    """Compute SHA-256 for file if within threshold, else report reason."""
    size = file_path.stat().st_size
    if size > max_bytes:
        return f"OMITTED_EXCEEDS_500MB (file size: {round(size / (1024*1024), 2)} MB)"
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class ForensicProfiler:
    def __init__(self, file_path: str, con: Optional[duckdb.DuckDBPyConnection] = None):
        self.file_path = Path(file_path).resolve()
        self.con = con or duckdb.connect(database=":memory:")
        self.profile: Dict[str, Any] = {}
        self.process = psutil.Process(os.getpid())

    def run(self) -> Dict[str, Any]:
        start_time = time.perf_counter()
        initial_rss = self.process.memory_info().rss

        if not self.file_path.exists():
            raise FileNotFoundError(f"Target dataset file not found: {self.file_path}")

        file_size = self.file_path.stat().st_size
        file_ext = self.file_path.suffix.lower()

        # 1. File Metadata
        file_info = {
            "path": str(self.file_path),
            "filename": self.file_path.name,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "size_gb": round(file_size / (1024 * 1024 * 1024), 4),
            "extension": file_ext,
            "sha256": compute_file_hash(self.file_path),
            "compressed": file_ext in [".gz", ".zip"]
        }

        # 2. Raw Line Count and Header Inspection
        total_raw_lines = 0
        header_line = ""
        encoding_detected = "utf-8"
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
                header_line = f.readline().strip()
                # Fast line count for manageable files
                total_raw_lines = 1
                for _ in f:
                    total_raw_lines += 1
        except Exception as e:
            header_line = f"ERROR_READING_HEADER: {e}"

        file_info["raw_line_count"] = total_raw_lines
        file_info["header_sample"] = header_line

        # 3. DuckDB Table Loading & Schema Verification
        # We explicitly load without silent truncation/ignore_errors
        table_name = "raw_transactions"
        self.con.execute(f"DROP TABLE IF EXISTS {table_name}")

        actual_columns = []
        schema_comparison = {}
        malformed_count = 0
        malformed_details = []

        try:
            if file_ext in [".csv", ".txt"]:
                # First inspect actual header columns
                header_cols_query = self.con.execute(
                    f"SELECT * FROM read_csv('{self.file_path}', header=true, sample_size=100) LIMIT 0"
                )
                actual_columns = [desc[0] for desc in header_cols_query.description]
                
                # Check for malformed rows using DuckDB reject / sniffing diagnostics if available
                # Load with strict VARCHAR casting for all fields to preserve original data exactly
                self.con.execute(f"""
                    CREATE TABLE {table_name} AS 
                    SELECT * FROM read_csv(
                        '{self.file_path}',
                        header=true,
                        all_varchar=true,
                        auto_detect=true
                    )
                """)
            elif file_ext in [".parquet"]:
                actual_columns = [desc[0] for desc in self.con.execute(
                    f"SELECT * FROM read_parquet('{self.file_path}') LIMIT 0"
                ).description]
                self.con.execute(f"""
                    CREATE TABLE {table_name} AS 
                    SELECT * FROM read_parquet('{self.file_path}')
                """)
            else:
                raise ValueError(f"Unsupported forensic file format for profiler: {file_ext}")
        except Exception as e:
            malformed_count += 1
            malformed_details.append(str(e))
            # Fallback with safe loading attempt
            try:
                self.con.execute(f"""
                    CREATE TABLE {table_name} AS 
                    SELECT * FROM read_csv_auto('{self.file_path}', ignore_errors=false)
                """)
            except Exception as e2:
                raise RuntimeError(f"Forensic dataset loading failed without silent discard: {e2}")

        # Check Schema Conformance
        expected_set = set(EXPECTED_SCHEMA)
        actual_set = set(actual_columns)
        missing_columns = [c for c in EXPECTED_SCHEMA if c not in actual_set]
        unexpected_columns = [c for c in actual_columns if c not in expected_set]
        column_order_matches = (actual_columns == EXPECTED_SCHEMA)

        schema_result = {
            "expected_columns": EXPECTED_SCHEMA,
            "actual_columns": actual_columns,
            "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
            "column_order_matches": column_order_matches,
            "duplicate_column_names": len(actual_columns) != len(set(actual_columns)),
            "status": "PASS" if not missing_columns and not unexpected_columns else "MISMATCH"
        }

        # 4. Record Counts
        total_records = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        record_counts = {
            "total_records": total_records,
            "data_rows_reported": total_records,
            "header_rows": 1 if total_raw_lines > 0 else 0,
            "malformed_rows_quarantined": malformed_count,
            "successfully_parsed_rows": total_records,
            "reference_target": 2000000,
            "target_benchmark_status": "PASS" if total_records >= 2000000 else "MEASURED_BELOW_REFERENCE"
        }

        # 5. Detailed Column-by-Column Profiling
        columns_profile = {}
        for col in actual_columns:
            stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) AS total_count,
                    COUNT("{col}") AS non_null_count,
                    COUNT(DISTINCT "{col}") AS distinct_count,
                    MIN(CAST("{col}" AS VARCHAR)) AS min_sample,
                    MAX(CAST("{col}" AS VARCHAR)) AS max_sample
                FROM {table_name}
            """).fetchone()

            total_c, non_null_c, distinct_c, min_s, max_s = stats
            null_count = total_c - non_null_c
            null_pct = round((null_count / total_c) * 100, 4) if total_c > 0 else 0.0

            # Sample non-null values
            samples = [row[0] for row in self.con.execute(f"""
                SELECT DISTINCT "{col}" FROM {table_name} 
                WHERE "{col}" IS NOT NULL LIMIT 3
            """).fetchall()]

            columns_profile[col] = {
                "detected_type": "VARCHAR (Preserved String)",
                "total_count": total_c,
                "null_count": null_count,
                "null_percentage": null_pct,
                "distinct_count": distinct_c,
                "example_samples": samples,
                "validation_status": "VALID" if null_count == 0 else "CONTAINS_NULLS"
            }

        # 6. Specific Account Format Analysis (Sender_Account & Receiver_Account)
        account_analysis = {}
        if "Sender_Account" in actual_columns and "Receiver_Account" in actual_columns:
            acc_stats = self.con.execute(f"""
                SELECT 
                    COUNT(DISTINCT Sender_Account) AS unique_senders,
                    COUNT(DISTINCT Receiver_Account) AS unique_receivers,
                    -- Sender lengths
                    SUM(CASE WHEN LENGTH(Sender_Account) = 12 THEN 1 ELSE 0 END) AS sender_len_12,
                    SUM(CASE WHEN LENGTH(Sender_Account) < 12 THEN 1 ELSE 0 END) AS sender_len_lt12,
                    SUM(CASE WHEN LENGTH(Sender_Account) > 12 THEN 1 ELSE 0 END) AS sender_len_gt12,
                    SUM(CASE WHEN Sender_Account LIKE '0%' THEN 1 ELSE 0 END) AS sender_leading_zeros,
                    SUM(CASE WHEN REGEXP_MATCHES(Sender_Account, '^[0-9]+$') THEN 0 ELSE 1 END) AS sender_non_digit,
                    -- Receiver lengths
                    SUM(CASE WHEN LENGTH(Receiver_Account) = 12 THEN 1 ELSE 0 END) AS receiver_len_12,
                    SUM(CASE WHEN LENGTH(Receiver_Account) < 12 THEN 1 ELSE 0 END) AS receiver_len_lt12,
                    SUM(CASE WHEN LENGTH(Receiver_Account) > 12 THEN 1 ELSE 0 END) AS receiver_len_gt12,
                    SUM(CASE WHEN Receiver_Account LIKE '0%' THEN 1 ELSE 0 END) AS receiver_leading_zeros,
                    SUM(CASE WHEN REGEXP_MATCHES(Receiver_Account, '^[0-9]+$') THEN 0 ELSE 1 END) AS receiver_non_digit
                FROM {table_name}
            """).fetchone()

            # Unique accounts across sender UNION receiver
            total_unique_accounts = self.con.execute(f"""
                SELECT COUNT(DISTINCT account) FROM (
                    SELECT Sender_Account AS account FROM {table_name}
                    UNION ALL
                    SELECT Receiver_Account AS account FROM {table_name}
                )
            """).fetchone()[0]

            account_analysis = {
                "unique_senders": acc_stats[0],
                "unique_receivers": acc_stats[1],
                "total_unique_accounts": total_unique_accounts,
                "reference_expected_accounts": "~25,000 (1,500 mules + 23,500 regular)",
                "sender_account": {
                    "exactly_12_digits": acc_stats[2],
                    "less_than_12_digits": acc_stats[3],
                    "greater_than_12_digits": acc_stats[4],
                    "leading_zeros": acc_stats[5],
                    "contains_non_digits": acc_stats[6]
                },
                "receiver_account": {
                    "exactly_12_digits": acc_stats[7],
                    "less_than_12_digits": acc_stats[8],
                    "greater_than_12_digits": acc_stats[9],
                    "leading_zeros": acc_stats[10],
                    "contains_non_digits": acc_stats[11]
                }
            }

        # 7. Transaction ID Validation
        tx_id_analysis = {}
        if "Transaction_ID" in actual_columns:
            tx_stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) - COUNT(Transaction_ID) AS null_count,
                    COUNT(*) - COUNT(DISTINCT Transaction_ID) AS duplicate_count,
                    MIN(LENGTH(Transaction_ID)) AS min_len,
                    MAX(LENGTH(Transaction_ID)) AS max_len
                FROM {table_name}
            """).fetchone()

            # Sample duplicates if any
            dupes = []
            if tx_stats[1] > 0:
                dupes = [r[0] for r in self.con.execute(f"""
                    SELECT Transaction_ID FROM {table_name}
                    GROUP BY Transaction_ID HAVING COUNT(*) > 1 LIMIT 5
                """).fetchall()]

            tx_id_analysis = {
                "null_count": tx_stats[0],
                "duplicate_count": tx_stats[1],
                "duplicate_samples": dupes,
                "min_length": tx_stats[2],
                "max_length": tx_stats[3],
                "integrity_status": "VALID" if tx_stats[0] == 0 and tx_stats[1] == 0 else "INTEGRITY_WARNING"
            }

        # 8. IFSC Validation
        ifsc_analysis = {}
        if "Sender_IFSC" in actual_columns and "Receiver_IFSC" in actual_columns:
            ifsc_stats = self.con.execute(f"""
                SELECT 
                    COUNT(DISTINCT Sender_IFSC) AS unique_sender_ifsc,
                    COUNT(DISTINCT Receiver_IFSC) AS unique_receiver_ifsc,
                    SUM(CASE WHEN LENGTH(Sender_IFSC) = 11 THEN 1 ELSE 0 END) AS sender_len_11,
                    SUM(CASE WHEN LENGTH(Receiver_IFSC) = 11 THEN 1 ELSE 0 END) AS receiver_len_11,
                    SUM(CASE WHEN REGEXP_MATCHES(Sender_IFSC, '^[A-Z]{{4}}0[A-Z0-9]{{6}}$') THEN 1 ELSE 0 END) AS sender_standard_pattern,
                    SUM(CASE WHEN REGEXP_MATCHES(Receiver_IFSC, '^[A-Z]{{4}}0[A-Z0-9]{{6}}$') THEN 1 ELSE 0 END) AS receiver_standard_pattern
                FROM {table_name}
            """).fetchone()

            unique_combined_ifsc = self.con.execute(f"""
                SELECT COUNT(DISTINCT ifsc) FROM (
                    SELECT Sender_IFSC AS ifsc FROM {table_name}
                    UNION ALL
                    SELECT Receiver_IFSC AS ifsc FROM {table_name}
                )
            """).fetchone()[0]

            ifsc_analysis = {
                "unique_sender_ifsc": ifsc_stats[0],
                "unique_receiver_ifsc": ifsc_stats[1],
                "unique_combined_ifsc": unique_combined_ifsc,
                "sender_ifsc_11_char_count": ifsc_stats[2],
                "receiver_ifsc_11_char_count": ifsc_stats[3],
                "sender_standard_rbi_pattern_matches": ifsc_stats[4],
                "receiver_standard_rbi_pattern_matches": ifsc_stats[5]
            }

        # 9. Amount Analysis
        amount_analysis = {}
        if "Amount" in actual_columns:
            amt_stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) AS count_total,
                    SUM(CASE WHEN TRY_CAST(Amount AS DOUBLE) IS NULL THEN 1 ELSE 0 END) AS unparseable,
                    SUM(CASE WHEN TRY_CAST(Amount AS DOUBLE) = 0 THEN 1 ELSE 0 END) AS zero_count,
                    SUM(CASE WHEN TRY_CAST(Amount AS DOUBLE) < 0 THEN 1 ELSE 0 END) AS negative_count,
                    MIN(TRY_CAST(Amount AS DOUBLE)) AS min_amt,
                    MAX(TRY_CAST(Amount AS DOUBLE)) AS max_amt,
                    AVG(TRY_CAST(Amount AS DOUBLE)) AS avg_amt,
                    MEDIAN(TRY_CAST(Amount AS DOUBLE)) AS median_amt,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.25) AS p25,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.50) AS p50,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.75) AS p75,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.90) AS p90,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.95) AS p95,
                    QUANTILE_CONT(TRY_CAST(Amount AS DOUBLE), 0.99) AS p99,
                    SUM(TRY_CAST(Amount AS DOUBLE)) AS sum_total
                FROM {table_name}
            """).fetchone()

            amount_analysis = {
                "total_count": amt_stats[0],
                "unparseable_null_count": amt_stats[1],
                "zero_amount_count": amt_stats[2],
                "negative_amount_count": amt_stats[3],
                "min": amt_stats[4],
                "max": amt_stats[5],
                "mean": round(amt_stats[6], 2) if amt_stats[6] else 0.0,
                "median": amt_stats[7],
                "percentiles": {
                    "p25": amt_stats[8],
                    "p50": amt_stats[9],
                    "p75": amt_stats[10],
                    "p90": amt_stats[11],
                    "p95": amt_stats[12],
                    "p99": amt_stats[13]
                },
                "total_transaction_volume_inr": round(amt_stats[14], 2) if amt_stats[14] else 0.0
            }

        # 10. Timestamp Analysis
        timestamp_analysis = {}
        if "Timestamp" in actual_columns:
            ts_stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) - COUNT(Timestamp) AS null_count,
                    SUM(CASE WHEN TRY_CAST(Timestamp AS TIMESTAMP) IS NULL THEN 1 ELSE 0 END) AS unparseable,
                    MIN(TRY_CAST(Timestamp AS TIMESTAMP)) AS min_ts,
                    MAX(TRY_CAST(Timestamp AS TIMESTAMP)) AS max_ts
                FROM {table_name}
            """).fetchone()

            min_ts = ts_stats[2]
            max_ts = ts_stats[3]
            span_days = None
            if min_ts and max_ts:
                span_diff = self.con.execute(f"""
                    SELECT DATEDIFF('day', MIN(TRY_CAST(Timestamp AS TIMESTAMP)), MAX(TRY_CAST(Timestamp AS TIMESTAMP)))
                    FROM {table_name}
                """).fetchone()[0]
                span_days = span_diff

            # Chronological order check
            out_of_order_count = self.con.execute(f"""
                WITH ordered_check AS (
                    SELECT 
                        TRY_CAST(Timestamp AS TIMESTAMP) AS ts,
                        LAG(TRY_CAST(Timestamp AS TIMESTAMP)) OVER() AS prev_ts
                    FROM {table_name}
                )
                SELECT COUNT(*) FROM ordered_check WHERE ts < prev_ts
            """).fetchone()[0]

            # Daily distribution sample
            daily_dist = [
                {"date": str(r[0]), "count": r[1]} for r in self.con.execute(f"""
                    SELECT CAST(TRY_CAST(Timestamp AS TIMESTAMP) AS DATE) AS tx_date, COUNT(*) 
                    FROM {table_name} 
                    WHERE TRY_CAST(Timestamp AS TIMESTAMP) IS NOT NULL
                    GROUP BY tx_date ORDER BY tx_date ASC
                """).fetchall()
            ]

            timestamp_analysis = {
                "null_count": ts_stats[0],
                "unparseable_count": ts_stats[1],
                "min_timestamp": str(min_ts),
                "max_timestamp": str(max_ts),
                "span_days": span_days,
                "reference_span_days": "15-day window",
                "out_of_order_record_count": out_of_order_count,
                "chronologically_sorted": (out_of_order_count == 0),
                "daily_distribution": daily_dist
            }

        # 11. Payment Mode Analysis
        payment_mode_analysis = {}
        if "Payment_Mode" in actual_columns:
            pm_counts = self.con.execute(f"""
                SELECT Payment_Mode, COUNT(*) AS cnt, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) AS pct
                FROM {table_name}
                GROUP BY Payment_Mode ORDER BY cnt DESC
            """).fetchall()
            expected_pm = {"UPI", "IMPS", "NEFT", "RTGS"}
            observed_pm = [r[0] for r in pm_counts]
            unexpected_pm = [p for p in observed_pm if p not in expected_pm]

            payment_mode_analysis = {
                "frequencies": [{"mode": r[0], "count": r[1], "percentage": r[2]} for r in pm_counts],
                "unexpected_modes": unexpected_pm,
                "conformance": "PASS" if not unexpected_pm else "UNEXPECTED_VALUES_OBSERVED"
            }

        # 12. Device Type Analysis
        device_type_analysis = {}
        if "Device_Type" in actual_columns:
            dev_counts = self.con.execute(f"""
                SELECT Device_Type, COUNT(*) AS cnt, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 2) AS pct
                FROM {table_name}
                GROUP BY Device_Type ORDER BY cnt DESC
            """).fetchall()
            expected_dev = {"Android", "iOS", "Windows_Browser", "Web_Emulator", "Linux_Script"}
            observed_dev = [r[0] for r in dev_counts]
            unexpected_dev = [d for d in observed_dev if d not in expected_dev]

            device_type_analysis = {
                "frequencies": [{"device": r[0], "count": r[1], "percentage": r[2]} for r in dev_counts],
                "unexpected_devices": unexpected_dev,
                "conformance": "PASS" if not unexpected_dev else "UNEXPECTED_VALUES_OBSERVED"
            }

        # 13. IP Address Analysis
        ip_analysis = {}
        if "IP_Address" in actual_columns:
            ip_stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) - COUNT(IP_Address) AS null_count,
                    COUNT(DISTINCT IP_Address) AS unique_ips,
                    SUM(CASE WHEN IP_Address LIKE '185.%' THEN 1 ELSE 0 END) AS ip_prefix_185_count,
                    SUM(CASE WHEN IP_Address LIKE '194.%' THEN 1 ELSE 0 END) AS ip_prefix_194_count,
                    SUM(CASE WHEN IP_Address LIKE '10.%' OR IP_Address LIKE '192.168.%' OR IP_Address LIKE '172.16.%' THEN 1 ELSE 0 END) AS private_rfc1918_count
                FROM {table_name}
            """).fetchone()

            ip_analysis = {
                "null_count": ip_stats[0],
                "unique_ips": ip_stats[1],
                "count_with_185_prefix": ip_stats[2],
                "count_with_194_prefix": ip_stats[3],
                "count_private_rfc1918": ip_stats[4],
                "note": "Prefix observation only. Final foreign classification deferred to calibrated detection step."
            }

        # 14. Narration Analysis
        narration_analysis = {}
        if "Narration" in actual_columns:
            narr_stats = self.con.execute(f"""
                SELECT 
                    COUNT(*) - COUNT(Narration) AS null_count,
                    COUNT(DISTINCT Narration) AS unique_narrations
                FROM {table_name}
            """).fetchone()

            top_narrations = [
                {"narration": r[0], "count": r[1]} for r in self.con.execute(f"""
                    SELECT Narration, COUNT(*) AS cnt 
                    FROM {table_name} 
                    GROUP BY Narration ORDER BY cnt DESC LIMIT 10
                """).fetchall()
            ]

            # Exploratory keyword scan
            keywords = ["crypto", "usdt", "binance", "p2p", "paxful", "telegram", "wallet", "commission", "task", "refund"]
            kw_counts = {}
            for kw in keywords:
                cnt = self.con.execute(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE LOWER(Narration) LIKE '%{kw}%'
                """).fetchone()[0]
                kw_counts[kw] = cnt

            narration_analysis = {
                "null_count": narr_stats[0],
                "unique_narrations": narr_stats[1],
                "top_10_narrations": top_narrations,
                "exploratory_keyword_matches": kw_counts,
                "note": "Exploratory signal profiling only; not treated as criminal flags in Step 1."
            }

        # 15. Graph-Relevant Structural Statistics
        graph_stats = {}
        if "Sender_Account" in actual_columns and "Receiver_Account" in actual_columns:
            self_loops = self.con.execute(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE Sender_Account = Receiver_Account
            """).fetchone()[0]

            account_roles = self.con.execute(f"""
                WITH senders AS (SELECT DISTINCT Sender_Account AS acc FROM {table_name}),
                     receivers AS (SELECT DISTINCT Receiver_Account AS acc FROM {table_name})
                SELECT 
                    (SELECT COUNT(*) FROM senders WHERE acc NOT IN (SELECT acc FROM receivers)) AS outgoing_only,
                    (SELECT COUNT(*) FROM receivers WHERE acc NOT IN (SELECT acc FROM senders)) AS incoming_only,
                    (SELECT COUNT(*) FROM senders WHERE acc IN (SELECT acc FROM receivers)) AS both_in_and_out
            """).fetchone()

            # Degree distribution percentiles
            fan_in_dist = self.con.execute(f"""
                WITH in_deg AS (
                    SELECT Receiver_Account, COUNT(*) AS in_cnt 
                    FROM {table_name} GROUP BY Receiver_Account
                )
                SELECT 
                    MIN(in_cnt),
                    MEDIAN(in_cnt),
                    QUANTILE_CONT(in_cnt, 0.75),
                    QUANTILE_CONT(in_cnt, 0.90),
                    QUANTILE_CONT(in_cnt, 0.95),
                    QUANTILE_CONT(in_cnt, 0.99),
                    MAX(in_cnt)
                FROM in_deg
            """).fetchone()

            fan_out_dist = self.con.execute(f"""
                WITH out_deg AS (
                    SELECT Sender_Account, COUNT(*) AS out_cnt 
                    FROM {table_name} GROUP BY Sender_Account
                )
                SELECT 
                    MIN(out_cnt),
                    MEDIAN(out_cnt),
                    QUANTILE_CONT(out_cnt, 0.75),
                    QUANTILE_CONT(out_cnt, 0.90),
                    QUANTILE_CONT(out_cnt, 0.95),
                    QUANTILE_CONT(out_cnt, 0.99),
                    MAX(out_cnt)
                FROM out_deg
            """).fetchone()

            top_incoming = [
                {"account": r[0], "in_degree": r[1]} for r in self.con.execute(f"""
                    SELECT Receiver_Account, COUNT(*) AS cnt 
                    FROM {table_name} GROUP BY Receiver_Account ORDER BY cnt DESC LIMIT 5
                """).fetchall()
            ]

            top_outgoing = [
                {"account": r[0], "out_degree": r[1]} for r in self.con.execute(f"""
                    SELECT Sender_Account, COUNT(*) AS cnt 
                    FROM {table_name} GROUP BY Sender_Account ORDER BY cnt DESC LIMIT 5
                """).fetchall()
            ]

            graph_stats = {
                "self_loop_transactions": self_loops,
                "accounts_outgoing_only": account_roles[0],
                "accounts_incoming_only": account_roles[1],
                "accounts_both_incoming_and_outgoing": account_roles[2],
                "fan_in_percentiles": {
                    "min": fan_in_dist[0],
                    "p50": fan_in_dist[1],
                    "p75": fan_in_dist[2],
                    "p90": fan_in_dist[3],
                    "p95": fan_in_dist[4],
                    "p99": fan_in_dist[5],
                    "max": fan_in_dist[6]
                },
                "fan_out_percentiles": {
                    "min": fan_out_dist[0],
                    "p50": fan_out_dist[1],
                    "p75": fan_out_dist[2],
                    "p90": fan_out_dist[3],
                    "p95": fan_out_dist[4],
                    "p99": fan_out_dist[5],
                    "max": fan_out_dist[6]
                },
                "top_5_incoming_accounts": top_incoming,
                "top_5_outgoing_accounts": top_outgoing
            }

        # 16. Temporal Velocity Exploratory Profiling
        velocity_profile = {}
        if "Sender_Account" in actual_columns and "Receiver_Account" in actual_columns and "Timestamp" in actual_columns:
            # For accounts with both incoming and outgoing, examine gap between incoming and subsequent outgoing
            try:
                vel_stats = self.con.execute(f"""
                    WITH in_tx AS (
                        SELECT Receiver_Account AS acc, TRY_CAST(Timestamp AS TIMESTAMP) AS t_in
                        FROM {table_name}
                    ),
                    out_tx AS (
                        SELECT Sender_Account AS acc, TRY_CAST(Timestamp AS TIMESTAMP) AS t_out
                        FROM {table_name}
                    ),
                    deltas AS (
                        SELECT 
                            i.acc,
                            DATEDIFF('minute', i.t_in, MIN(o.t_out)) AS delta_mins
                        FROM in_tx i
                        JOIN out_tx o ON i.acc = o.acc AND o.t_out >= i.t_in
                        GROUP BY i.acc, i.t_in
                    )
                    SELECT 
                        SUM(CASE WHEN delta_mins < 1 THEN 1 ELSE 0 END) AS lt_1m,
                        SUM(CASE WHEN delta_mins >= 1 AND delta_mins < 3 THEN 1 ELSE 0 END) AS b_1_3m,
                        SUM(CASE WHEN delta_mins >= 3 AND delta_mins < 5 THEN 1 ELSE 0 END) AS b_3_5m,
                        SUM(CASE WHEN delta_mins >= 5 AND delta_mins < 10 THEN 1 ELSE 0 END) AS b_5_10m,
                        SUM(CASE WHEN delta_mins >= 10 AND delta_mins < 15 THEN 1 ELSE 0 END) AS b_10_15m,
                        SUM(CASE WHEN delta_mins >= 15 AND delta_mins < 30 THEN 1 ELSE 0 END) AS b_15_30m,
                        SUM(CASE WHEN delta_mins >= 30 AND delta_mins < 60 THEN 1 ELSE 0 END) AS b_30_60m,
                        SUM(CASE WHEN delta_mins >= 60 AND delta_mins < 360 THEN 1 ELSE 0 END) AS b_1_6h,
                        SUM(CASE WHEN delta_mins >= 360 AND delta_mins < 1440 THEN 1 ELSE 0 END) AS b_6_24h,
                        SUM(CASE WHEN delta_mins >= 1440 AND delta_mins < 2880 THEN 1 ELSE 0 END) AS b_24_48h,
                        SUM(CASE WHEN delta_mins >= 2880 THEN 1 ELSE 0 END) AS gt_48h
                    FROM deltas
                """).fetchone()

                velocity_profile = {
                    "less_than_1_min": vel_stats[0],
                    "1_to_3_mins": vel_stats[1],
                    "3_to_5_mins": vel_stats[2],
                    "5_to_10_mins": vel_stats[3],
                    "10_to_15_mins": vel_stats[4],
                    "15_to_30_mins": vel_stats[5],
                    "30_to_60_mins": vel_stats[6],
                    "1_to_6_hours": vel_stats[7],
                    "6_to_24_hours": vel_stats[8],
                    "24_to_48_hours": vel_stats[9],
                    "greater_than_48_hours": vel_stats[10],
                    "note": "Exploratory latency profiling only. Pass-through threshold tuning deferred."
                }
            except Exception as e:
                velocity_profile = {"error": f"Velocity calculation failed: {e}"}

        # 17. Dataset Health Synthesis
        health_summary = {
            "schema_conformity": "VALID" if schema_result["status"] == "PASS" else "ERROR",
            "row_integrity": "VALID" if malformed_count == 0 else "WARNING",
            "account_integrity": "VALID" if account_analysis.get("sender_account", {}).get("contains_non_digits", 0) == 0 else "WARNING",
            "transaction_id_integrity": tx_id_analysis.get("integrity_status", "NOT_DETERMINED"),
            "timestamp_integrity": "VALID" if timestamp_analysis.get("unparseable_count", 0) == 0 else "WARNING",
            "amount_integrity": "VALID" if amount_analysis.get("unparseable_null_count", 0) == 0 and amount_analysis.get("negative_amount_count", 0) == 0 else "WARNING",
            "ifsc_integrity": "VALID" if ifsc_analysis.get("sender_ifsc_11_char_count", 0) == total_records else "WARNING",
            "payment_mode_integrity": payment_mode_analysis.get("conformance", "NOT_DETERMINED"),
            "device_integrity": device_type_analysis.get("conformance", "NOT_DETERMINED"),
            "ip_integrity": "VALID" if ip_analysis.get("null_count", 0) == 0 else "WARNING",
            "narration_integrity": "VALID" if narration_analysis.get("null_count", 0) == 0 else "WARNING"
        }

        # Performance and End Metrics
        end_time = time.perf_counter()
        final_rss = self.process.memory_info().rss
        profiler_duration = round(end_time - start_time, 2)
        peak_rss_mb = round(final_rss / (1024 * 1024), 2)

        self.profile = {
            "meta": {
                "profiler_version": PROFILER_VERSION,
                "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "python_version": sys.version.split()[0],
                "duckdb_version": duckdb.__version__,
                "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
                "execution_duration_seconds": profiler_duration,
                "peak_process_rss_mb": peak_rss_mb
            },
            "file_info": file_info,
            "schema_result": schema_result,
            "record_counts": record_counts,
            "health_summary": health_summary,
            "column_profiles": columns_profile,
            "account_analysis": account_analysis,
            "transaction_id_analysis": tx_id_analysis,
            "ifsc_analysis": ifsc_analysis,
            "amount_analysis": amount_analysis,
            "timestamp_analysis": timestamp_analysis,
            "payment_mode_analysis": payment_mode_analysis,
            "device_type_analysis": device_type_analysis,
            "ip_analysis": ip_analysis,
            "narration_analysis": narration_analysis,
            "graph_structural_statistics": graph_stats,
            "temporal_velocity_profile": velocity_profile
        }

        return self.profile

    def save_reports(self, output_json: str, output_md: str):
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(output_md).parent.mkdir(parents=True, exist_ok=True)

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=2)

        # Generate Markdown Report
        md = []
        md.append("# Operation 'ABHEDYA-CHAKRA' — Forensic Dataset Profile Report\n")
        md.append(f"**Generated:** {self.profile['meta']['timestamp_utc']} | **Profiler Version:** {self.profile['meta']['profiler_version']}")
        md.append(f"**Platform:** {self.profile['meta']['platform']} | **DuckDB:** {self.profile['meta']['duckdb_version']}\n")
        md.append("---\n")

        # 1. Dataset Discovery & Health
        md.append("## 1. Dataset Health & Integrity Summary\n")
        md.append("| Check | Status |")
        md.append("| :--- | :--- |")
        for k, v in self.profile["health_summary"].items():
            md.append(f"| **{k.replace('_', ' ').title()}** | `{v}` |")
        md.append("\n")

        # 2. File & Record Counts
        md.append("## 2. File Information & Record Counts\n")
        fi = self.profile["file_info"]
        rc = self.profile["record_counts"]
        md.append(f"- **Path:** `{fi['path']}`")
        md.append(f"- **Size:** {fi['size_mb']} MB ({fi['size_bytes']:,} bytes)")
        md.append(f"- **SHA-256:** `{fi['sha256']}`")
        md.append(f"- **Total Parsed Records:** **{rc['total_records']:,}** (Target Reference: {rc['reference_target']:,})")
        md.append(f"- **Target Benchmark Status:** `{rc['target_benchmark_status']}`")
        md.append(f"- **Malformed Records Quarantined:** `{rc['malformed_rows_quarantined']}`\n")

        # 3. Schema Conformance
        md.append("## 3. Schema Conformance\n")
        sc = self.profile["schema_result"]
        md.append(f"- **Status:** `{sc['status']}`")
        md.append(f"- **Column Order Exact Match:** `{sc['column_order_matches']}`")
        md.append(f"- **Missing Columns:** `{sc['missing_columns'] or 'None'}`")
        md.append(f"- **Unexpected Columns:** `{sc['unexpected_columns'] or 'None'}`\n")

        # 4. Account Cardinality
        md.append("## 4. Account Distribution & Cardinality\n")
        acc = self.profile.get("account_analysis", {})
        md.append(f"- **Total Unique Accounts (Sender ∪ Receiver):** **{acc.get('total_unique_accounts', 0):,}**")
        md.append(f"- **Unique Senders:** {acc.get('unique_senders', 0):,}")
        md.append(f"- **Unique Receivers:** {acc.get('unique_receivers', 0):,}")
        md.append(f"- **Problem Statement Reference:** {acc.get('reference_expected_accounts', 'N/A')}")
        md.append(f"- **Sender Non-Digit Accounts:** `{acc.get('sender_account', {}).get('contains_non_digits', 0)}`")
        md.append(f"- **Receiver Non-Digit Accounts:** `{acc.get('receiver_account', {}).get('contains_non_digits', 0)}`\n")

        # 5. Financial Volume
        md.append("## 5. Financial Volume & Amount Statistics (INR ₹)\n")
        amt = self.profile.get("amount_analysis", {})
        md.append(f"- **Total Observed Volume:** ₹{amt.get('total_transaction_volume_inr', 0):,.2f}")
        md.append(f"- **Min Amount:** ₹{amt.get('min', 0):,.2f}")
        md.append(f"- **Max Amount:** ₹{amt.get('max', 0):,.2f}")
        md.append(f"- **Median Amount:** ₹{amt.get('median', 0):,.2f}")
        md.append(f"- **Unparseable / Negative Amounts:** `{amt.get('negative_amount_count', 0)}`\n")

        # 6. Temporal Span
        md.append("## 6. Temporal Analysis\n")
        ts = self.profile.get("timestamp_analysis", {})
        md.append(f"- **Start Timestamp:** `{ts.get('min_timestamp')}`")
        md.append(f"- **End Timestamp:** `{ts.get('max_timestamp')}`")
        md.append(f"- **Observed Span:** {ts.get('span_days')} days (Reference: {ts.get('reference_span_days')})")
        md.append(f"- **Chronologically Sorted:** `{ts.get('chronologically_sorted')}`")
        md.append(f"- **Out-of-Order Rows:** `{ts.get('out_of_order_record_count', 0):,}`\n")

        # 7. Categorical Distributions
        md.append("## 7. Categorical Channels & Client Profiles\n")
        md.append("### Payment Modes Observed\n")
        md.append("| Mode | Count | Percentage |")
        md.append("| :--- | :--- | :--- |")
        for pm in self.profile.get("payment_mode_analysis", {}).get("frequencies", []):
            md.append(f"| **{pm['mode']}** | {pm['count']:,} | {pm['percentage']}% |")
        md.append("\n### Client Device Types Observed\n")
        md.append("| Device Type | Count | Percentage |")
        md.append("| :--- | :--- | :--- |")
        for dev in self.profile.get("device_type_analysis", {}).get("frequencies", []):
            md.append(f"| **{dev['device']}** | {dev['count']:,} | {dev['percentage']}% |")
        md.append("\n")

        # 8. Forensic Signals
        md.append("## 8. Forensic Signals & IP/Narration Observations\n")
        ip = self.profile.get("ip_analysis", {})
        md.append(f"- **Unique IP Addresses:** {ip.get('unique_ips', 0):,}")
        md.append(f"- **185.x.x.x Prefix Count:** `{ip.get('count_with_185_prefix', 0):,}`")
        md.append(f"- **194.x.x.x Prefix Count:** `{ip.get('count_with_194_prefix', 0):,}`")
        md.append(f"- **RFC1918 Private IP Count:** `{ip.get('count_private_rfc1918', 0):,}`")
        
        narr = self.profile.get("narration_analysis", {})
        md.append(f"- **Unique Narrations:** {narr.get('unique_narrations', 0):,}")
        md.append("- **Exploratory Keyword Matches:**")
        for kw, cnt in narr.get("exploratory_keyword_matches", {}).items():
            md.append(f"  - `{kw}`: {cnt:,}")
        md.append("\n")

        # 9. Performance
        md.append("## 9. Profiler Execution Performance\n")
        meta = self.profile["meta"]
        md.append(f"- **Execution Duration:** {meta['execution_duration_seconds']} seconds")
        md.append(f"- **Peak Process RSS:** {meta['peak_process_rss_mb']} MB (OS-level via psutil)\n")

        with open(output_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md))


def main():
    parser = argparse.ArgumentParser(description="Forensic Dataset Inspection & Profiler for Operation Abhedya-Chakra")
    parser.add_argument("--input", "-i", type=str, help="Path to transaction dataset file or directory")
    parser.add_argument("--output-json", default="reports/data_profile.json", help="Path to machine-readable JSON output")
    parser.add_argument("--output-md", default="reports/data_profile_report.md", help="Path to human-readable Markdown output")
    parser.add_argument("--search-paths", nargs="+", default=["data", ".", "..", str(Path.home() / "Downloads"), str(Path.home() / "OneDrive" / "Desktop")],
                        help="Candidate paths to search if --input is omitted")
    args = parser.parse_args()

    print(f"=== OPERATION ABHEDYA-CHAKRA: FORENSIC DATA PROFILER v{PROFILER_VERSION} ===")

    target_file = None
    if args.input:
        in_path = Path(args.input).resolve()
        if in_path.is_file():
            target_file = in_path
        elif in_path.is_dir():
            print(f"Scanning directory: {in_path}")
            candidates = discover_datasets([str(in_path)])
            if candidates:
                # Prefer larger files or files with transaction in name
                candidates.sort(key=lambda c: c["size_bytes"], reverse=True)
                target_file = Path(candidates[0]["path"])
                print(f"Found {len(candidates)} candidate(s). Selected largest: {target_file} ({candidates[0]['size_mb']} MB)")
    else:
        print("No --input specified. Performing automated candidate discovery...")
        candidates = discover_datasets(args.search_paths)
        if candidates:
            print(f"Discovered {len(candidates)} candidate file(s):")
            for c in candidates:
                print(f"  - [{c['size_mb']} MB] {c['path']} (Matches schema: {c['matches_schema']}, Ground truth: {c['is_likely_ground_truth']})")
            # Select candidate that matches schema
            tx_candidates = [c for c in candidates if c["matches_schema"] and not c["is_likely_ground_truth"]]
            if tx_candidates:
                tx_candidates.sort(key=lambda c: c["size_bytes"], reverse=True)
                target_file = Path(tx_candidates[0]["path"])
                print(f"\nSelected verified transaction candidate: {target_file}")
            else:
                target_file = None
        
    # Check ground truth
    gt_discovery = discover_ground_truth(args.search_paths)
    print("\n[GROUND TRUTH DISCOVERY]")
    print(f"  Ground Truth Found: {'YES' if gt_discovery['ground_truth_found'] else 'NO'}")
    print(f"  Status: {gt_discovery['status']}")
    if gt_discovery["ground_truth_found"]:
        for c in gt_discovery["candidates"]:
            print(f"  - Candidate: {c['path']} ({c['size_mb']} MB)")

    if not target_file or not target_file.exists():
        print("\n" + "="*70)
        print("  OFFICIAL DATASET NOT FOUND")
        print("  Step 1 cannot be considered complete against the real dataset.")
        print("  Synthetic data generation is deferred to a separate stress-test task.")
        print("="*70 + "\n")
        
        # Save discovery report even if dataset not found
        discovery_report = {
            "status": "OFFICIAL_DATASET_NOT_FOUND",
            "message": "Official transaction dataset was not found in scanned paths.",
            "searched_paths": args.search_paths,
            "ground_truth_discovery": gt_discovery,
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(discovery_report, f, indent=2)
        sys.exit(2)

    print(f"\nExecuting forensic profiling on: {target_file}")
    profiler = ForensicProfiler(str(target_file))
    profile = profiler.run()
    profiler.save_reports(args.output_json, args.output_md)

    print("\n" + "="*70)
    print("  FORENSIC PROFILING COMPLETED")
    print("="*70)
    print(f"  Rows Parsed:        {profile['record_counts']['total_records']:,}")
    print(f"  Schema Status:      {profile['schema_result']['status']}")
    print(f"  Total Unique Accs:  {profile.get('account_analysis', {}).get('total_unique_accounts', 'N/A')}")
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print(f"  Total Volume (INR): INR {profile.get('amount_analysis', {}).get('total_transaction_volume_inr', 0):,.2f}")
    print(f"  Time Span (Days):   {profile.get('timestamp_analysis', {}).get('span_days', 'N/A')}")
    print(f"  Profiler Latency:   {profile['meta']['execution_duration_seconds']}s")
    print(f"  Peak Process RSS:   {profile['meta']['peak_process_rss_mb']} MB")
    print(f"  Markdown Report:    {args.output_md}")
    print(f"  JSON Report:        {args.output_json}")
    print("="*70)


if __name__ == "__main__":
    main()
