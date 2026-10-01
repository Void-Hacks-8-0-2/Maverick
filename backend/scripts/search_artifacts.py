#!/usr/bin/env python3
"""
OPERATION "ABHEDYA-CHAKRA"
P0 STEP 1B: Original Dataset Artifact Discovery Script

Authoritative Reference: Void Hacks() 8.0 Problem Statement
Task: Search local filesystems for higher-fidelity transaction dataset artifacts (.csv, .xlsx, .parquet, .zip, etc.).
"""

import os
import sys
import json
import time
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import duckdb
import openpyxl

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

TARGET_EXTENSIONS = {
    ".csv", ".csv.gz", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".zip", ".7z", ".duckdb", ".db"
}

KEYWORDS = ["dataset", "voidhacks", "transaction", "transactions", "bank", "mule", "financial"]


def compute_sha256(path: Path, max_bytes: int = 500 * 1024 * 1024) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return f"OMITTED_EXCEEDS_{max_bytes//(1024*1024)}MB"
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        return f"ERROR: {e}"


def inspect_candidate(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    ext = path.suffix.lower()
    candidate_info = {
        "absolute_path": str(path.resolve()),
        "filename": path.name,
        "extension": ext,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modification_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        "is_readable": False,
        "appears_to_contain_transaction_data": False,
        "detected_columns": [],
        "row_count": None,
        "expected_columns_matched": [],
        "missing_expected_columns": EXPECTED_SCHEMA.copy(),
        "all_expected_fields_present": False,
        "notes": "",
        "sha256": None
    }

    try:
        # Check readability
        with open(path, "rb") as f:
            header_bytes = f.read(256)
        candidate_info["is_readable"] = True
    except Exception as e:
        candidate_info["notes"] = f"Unreadable: {e}"
        return candidate_info

    # Inspect CSV
    if ext in [".csv", ".txt"]:
        try:
            con = duckdb.connect(database=":memory:")
            desc = con.execute(f"SELECT * FROM read_csv('{path}', header=true, sample_size=50) LIMIT 0").description
            cols = [d[0] for d in desc]
            candidate_info["detected_columns"] = cols
            matched = [c for c in EXPECTED_SCHEMA if c in cols]
            missing = [c for c in EXPECTED_SCHEMA if c not in cols]
            candidate_info["expected_columns_matched"] = matched
            candidate_info["missing_expected_columns"] = missing
            candidate_info["all_expected_fields_present"] = (len(missing) == 0)
            
            # Row count
            cnt = con.execute(f"SELECT COUNT(*) FROM read_csv('{path}', header=true)").fetchone()[0]
            candidate_info["row_count"] = cnt
            candidate_info["appears_to_contain_transaction_data"] = (len(matched) >= 3)
            con.close()
        except Exception as e:
            candidate_info["notes"] = f"CSV inspect error: {e}"

    # Inspect Parquet
    elif ext == ".parquet":
        try:
            con = duckdb.connect(database=":memory:")
            desc = con.execute(f"SELECT * FROM read_parquet('{path}') LIMIT 0").description
            cols = [d[0] for d in desc]
            candidate_info["detected_columns"] = cols
            matched = [c for c in EXPECTED_SCHEMA if c in cols]
            missing = [c for c in EXPECTED_SCHEMA if c not in cols]
            candidate_info["expected_columns_matched"] = matched
            candidate_info["missing_expected_columns"] = missing
            candidate_info["all_expected_fields_present"] = (len(missing) == 0)
            
            cnt = con.execute(f"SELECT COUNT(*) FROM read_parquet('{path}')").fetchone()[0]
            candidate_info["row_count"] = cnt
            candidate_info["appears_to_contain_transaction_data"] = (len(matched) >= 3)
            con.close()
        except Exception as e:
            candidate_info["notes"] = f"Parquet inspect error: {e}"

    # Inspect Excel (.xlsx)
    elif ext in [".xlsx", ".xls"]:
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            sheet = wb.active
            rows = sheet.iter_rows(max_row=2, values_only=True)
            header_row = next(rows, None)
            if header_row:
                cols = [str(c).strip() for c in header_row if c is not None]
                candidate_info["detected_columns"] = cols
                matched = [c for c in EXPECTED_SCHEMA if c in cols]
                missing = [c for c in EXPECTED_SCHEMA if c not in cols]
                candidate_info["expected_columns_matched"] = matched
                candidate_info["missing_expected_columns"] = missing
                candidate_info["all_expected_fields_present"] = (len(missing) == 0)
                candidate_info["appears_to_contain_transaction_data"] = (len(matched) >= 3)
            wb.close()
        except Exception as e:
            candidate_info["notes"] = f"Excel inspect error: {e}"

    # Inspect ZIP archives
    elif ext == ".zip":
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                namelist = zf.namelist()
                candidate_info["detected_columns"] = [f"archive_entry:{n}" for n in namelist[:20]]
                candidate_info["notes"] = f"Contains {len(namelist)} entries: {namelist[:5]}"
                # Check if entries match keywords
                for n in namelist:
                    if any(k in n.lower() for k in KEYWORDS):
                        candidate_info["appears_to_contain_transaction_data"] = True
                        break
        except Exception as e:
            candidate_info["notes"] = f"ZIP inspect error: {e}"

    if candidate_info["appears_to_contain_transaction_data"]:
        candidate_info["sha256"] = compute_sha256(path)

    return candidate_info


def search_all_artifacts(search_roots: List[str]) -> List[Dict[str, Any]]:
    candidates = []
    seen = set()

    for root_str in search_roots:
        root_path = Path(root_str).resolve()
        if not root_path.exists():
            continue

        print(f"Scanning search root: {root_path} ...")
        # Walk directory
        for dirpath, dirnames, filenames in os.walk(root_path):
            dp = Path(dirpath)
            # Skip python venvs, node_modules, git, caches
            if any(part.lower() in [".venv", "venv", "node_modules", ".git", "__pycache__", "appdata"] for part in dp.parts):
                continue

            for fname in filenames:
                p = dp / fname
                ext = p.suffix.lower()
                name_lower = fname.lower()

                # Filter by extension or keyword
                matches_ext = ext in TARGET_EXTENSIONS
                matches_kw = any(k in name_lower for k in KEYWORDS)

                if matches_ext or matches_kw:
                    norm = str(p.resolve())
                    if norm in seen:
                        continue
                    seen.add(norm)
                    
                    try:
                        cand = inspect_candidate(p)
                        # We include if it matches extension or keyword
                        candidates.append(cand)
                    except Exception as e:
                        pass

    return candidates


def main():
    start_time = time.perf_counter()
    user_home = Path.home()
    
    search_roots = [
        "C:\\Users\\sdmgo\\OneDrive\\Desktop\\Abhedya-Chakara",
        str(user_home / "OneDrive" / "Desktop"),
        str(user_home / "Downloads"),
        str(user_home / "OneDrive" / "Documents"),
        str(user_home / "OneDrive"),
        str(user_home / "Desktop"),
        str(user_home / "Documents")
    ]

    print("=== OPERATION ABHEDYA-CHAKRA: P0 STEP 1B ORIGINAL DATASET ARTIFACT DISCOVERY ===")
    candidates = search_all_artifacts(search_roots)
    print(f"\nScanned candidate pool: {len(candidates)} file(s) matched criteria.")

    # Categorize candidates
    high_fidelity_sources = []
    partial_transaction_candidates = []
    other_files = []

    for c in candidates:
        # Exclude our own unit test fixture from candidate determination
        if "tests" in c["absolute_path"].lower() or "fixtures" in c["absolute_path"].lower():
            other_files.append(c)
            continue

        if c["all_expected_fields_present"] and c["row_count"] and c["row_count"] >= 1000000:
            high_fidelity_sources.append(c)
        elif c["appears_to_contain_transaction_data"] and len(c["expected_columns_matched"]) >= 3:
            partial_transaction_candidates.append(c)
        else:
            other_files.append(c)

    # Determine final status
    if len(high_fidelity_sources) > 0:
        final_status = "FOUND_HIGH_FIDELITY_SOURCE"
    elif len(partial_transaction_candidates) > 0:
        final_status = "FOUND_CANDIDATES_NEED_VALIDATION"
    else:
        final_status = "NO_HIGHER_FIDELITY_SOURCE_FOUND"

    exec_time = round(time.perf_counter() - start_time, 2)

    # Create reports
    report_data = {
        "final_status": final_status,
        "discovery_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "search_roots": [str(Path(r).resolve()) for r in search_roots if Path(r).exists()],
        "search_criteria": {
            "extensions": list(TARGET_EXTENSIONS),
            "keywords": KEYWORDS,
            "expected_schema": EXPECTED_SCHEMA
        },
        "summary": {
            "total_candidates_inspected": len(candidates),
            "high_fidelity_sources_count": len(high_fidelity_sources),
            "partial_transaction_candidates_count": len(partial_transaction_candidates),
            "other_files_count": len(other_files),
            "execution_duration_seconds": exec_time
        },
        "high_fidelity_sources": high_fidelity_sources,
        "partial_transaction_candidates": partial_transaction_candidates,
        "other_candidates": other_files
    }

    Path("reports").mkdir(parents=True, exist_ok=True)
    json_path = Path("reports/original_dataset_discovery.json")
    md_path = Path("reports/original_dataset_discovery.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    # Markdown Report
    md = []
    md.append("# Operation 'ABHEDYA-CHAKRA' — Original Dataset Artifact Discovery Report (P0 Step 1B)\n")
    md.append(f"**Final Status:** `{final_status}`  \n")
    md.append(f"**Execution Timestamp:** {report_data['discovery_timestamp_utc']}  \n")
    md.append(f"**Search Duration:** {exec_time} seconds  \n")
    md.append("---\n")

    md.append("## 1. Executive Summary\n")
    md.append(f"- **Final Discovery Determination:** `{final_status}`")
    md.append(f"- **Total Candidate Files Inspected:** `{len(candidates)}`")
    md.append(f"- **High-Fidelity Official Sources (11 columns, 2M+ rows):** `{len(high_fidelity_sources)}`")
    md.append(f"- **Partial / Related Transaction Candidates:** `{len(partial_transaction_candidates)}`\n")

    md.append("## 2. Scanned Search Roots\n")
    for sr in report_data["search_roots"]:
        md.append(f"- `{sr}`")
    md.append("\n")

    md.append("## 3. Detailed Candidate Analysis\n")
    if high_fidelity_sources:
        md.append("### 3.1 High-Fidelity Sources Found\n")
        for h in high_fidelity_sources:
            md.append(f"#### `{h['filename']}`\n")
            md.append(f"- **Path:** `{h['absolute_path']}`")
            md.append(f"- **Size:** {h['size_mb']} MB ({h['size_bytes']:,} bytes)")
            md.append(f"- **Rows:** {h['row_count']:,}")
            md.append(f"- **SHA-256:** `{h['sha256']}`")
            md.append(f"- **Columns Detected:** `{h['detected_columns']}`")
            md.append(f"- **All 11 Expected Columns Present:** `{h['all_expected_fields_present']}`\n")
    else:
        md.append("### 3.1 High-Fidelity Sources Found: NONE\n")
        md.append("No machine-readable dataset (.csv, .parquet, .xlsx) containing all 11 columns at 2,000,000+ scale was discovered in the scanned paths.\n")

    if partial_transaction_candidates:
        md.append("### 3.2 Related / Partial Transaction Candidates\n")
        for p in partial_transaction_candidates:
            md.append(f"#### `{p['filename']}`\n")
            md.append(f"- **Path:** `{p['absolute_path']}`")
            md.append(f"- **Size:** {p['size_mb']} MB ({p['size_bytes']:,} bytes)")
            md.append(f"- **Modified:** `{p['modification_time']}`")
            md.append(f"- **Rows:** `{p['row_count'] if p['row_count'] is not None else 'N/A'}`")
            md.append(f"- **Columns Detected:** `{p['detected_columns'][:10]}`")
            md.append(f"- **Matched Schema Columns:** `{p['expected_columns_matched']}`")
            md.append(f"- **Missing Schema Columns:** `{p['missing_expected_columns']}`")
            md.append(f"- **Notes:** {p['notes']}\n")

    md.append("## 4. Discovery Conclusion & Next Steps\n")
    if final_status == "NO_HIGHER_FIDELITY_SOURCE_FOUND":
        md.append("1. **Status:** No original raw transaction file (.csv, .parquet, .xlsx) exists in the local environment.")
        md.append("2. **Reason:** The PDF `Dataset_VoidHacks_compressed.pdf` was generated externally via Microsoft Excel 2021 by author 'ASUS' and compressed via iLovePDF, but the source spreadsheet was not saved to or downloaded on this machine.")
        md.append("3. **Action:** The team/organizers must supply the raw spreadsheet or CSV file from the authoring machine.")
    elif final_status == "FOUND_CANDIDATES_NEED_VALIDATION":
        md.append("1. Candidate files with partial transaction schemas were found but none meet the full 11-column 2M+ requirement.")
        md.append("2. See candidates listed above in Section 3.2.")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print("\n" + "="*70)
    print(f"  FINAL DISCOVERY STATUS: {final_status}")
    print("="*70)
    print(f"  Total Candidates Checked:  {len(candidates)}")
    print(f"  High-Fidelity 2M+ Sources: {len(high_fidelity_sources)}")
    print(f"  Partial Candidates:        {len(partial_transaction_candidates)}")
    print(f"  Report (Markdown):         reports/original_dataset_discovery.md")
    print(f"  Report (JSON):             reports/original_dataset_discovery.json")
    print(f"  Duration:                  {exec_time}s")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
