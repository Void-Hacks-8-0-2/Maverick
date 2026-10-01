"""
Automated Validation Tests for Operation Abhedya-Chakra Updated Dataset.
Ensures that:
1. The newly received dataset VoidHacks8_MuleAccount_2M_Transactions.csv meets all specifications.
2. The original dataset and interim recovered dataset remain intact and untouched.
3. The 11 expected fields are 100% complete with 0 fabricated values.
4. Scale satisfies 2,000,000+ transactions.
5. Generated audit reports are verified.
"""

import hashlib
import json
import os
from pathlib import Path
import duckdb
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CSV_PATH = DATA_DIR / "VoidHacks8_MuleAccount_2M_Transactions.csv"
INTERIM_PARQUET_PATH = DATA_DIR / "extracted" / "transactions_recovered.parquet"
ORIGINAL_PDF_PATH = DATA_DIR / "Dataset_VoidHacks_compressed.pdf"

EXPECTED_FIELDS = [
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

EXPECTED_SHA256 = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
EXPECTED_ROWS = 2000000


def test_updated_dataset_file_integrity():
    """Verify that the updated CSV file exists, is unmodified, and has the correct SHA-256."""
    assert CSV_PATH.exists(), f"Updated dataset not found at {CSV_PATH}"
    file_size = CSV_PATH.stat().st_size
    assert file_size == 286788986, f"Unexpected file size: {file_size}"
    
    # Verify SHA-256
    hasher = hashlib.sha256()
    with open(CSV_PATH, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    assert hasher.hexdigest() == EXPECTED_SHA256


def test_interim_and_pdf_datasets_preserved():
    """Verify that the interim recovered parquet and original PDF datasets are NOT overwritten."""
    assert ORIGINAL_PDF_PATH.exists(), "Original PDF dataset must not be removed"
    assert INTERIM_PARQUET_PATH.exists(), "Interim recovered parquet must not be replaced"
    
    con = duckdb.connect()
    interim_count = con.execute(f"SELECT count(*) FROM read_parquet('{str(INTERIM_PARQUET_PATH).replace('\\', '/')}')").fetchone()[0]
    assert interim_count == 149741, f"Interim recovered parquet row count must remain 149,741, got {interim_count}"
    con.close()


def test_schema_conformance():
    """Verify exact 11 columns in the correct schema."""
    con = duckdb.connect()
    escaped_csv = str(CSV_PATH).replace('\\', '/')
    columns = [col[0] for col in con.execute(f"DESCRIBE SELECT * FROM read_csv('{escaped_csv}', header=true, sample_size=1000)").fetchall()]
    con.close()
    
    assert columns == EXPECTED_FIELDS, f"Columns do not match expected schema. Got: {columns}"


def test_scale_and_completeness():
    """Verify row count == 2,000,000 and 0 null values across all 11 columns."""
    con = duckdb.connect()
    escaped_csv = str(CSV_PATH).replace('\\', '/')
    
    # Row count
    total_rows = con.execute(f"SELECT count(*) FROM read_csv('{escaped_csv}', header=true)").fetchone()[0]
    assert total_rows == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS} rows, got {total_rows}"
    
    # Null counts
    null_exprs = ", ".join([f"sum(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS {col}_nulls" for col in EXPECTED_FIELDS])
    null_counts = con.execute(f"SELECT {null_exprs} FROM read_csv('{escaped_csv}', header=true)").fetchone()
    con.close()
    
    for col_name, null_val in zip(EXPECTED_FIELDS, null_counts):
        assert null_val == 0, f"Column {col_name} has {null_val} null values, expected 0"


def test_timestamp_and_device_type_restored():
    """Verify Timestamp and Device_Type are fully present and populated."""
    con = duckdb.connect()
    escaped_csv = str(CSV_PATH).replace('\\', '/')
    
    ts_res = con.execute(f"""
        SELECT 
            min(Timestamp) as min_ts, 
            max(Timestamp) as max_ts,
            count(distinct Device_Type) as unique_devices
        FROM read_csv('{escaped_csv}', header=true)
    """).fetchone()
    
    min_ts, max_ts, unique_devices = ts_res
    assert str(min_ts).startswith("2026-09-15"), f"Unexpected min timestamp: {min_ts}"
    assert str(max_ts).startswith("2026-09-29"), f"Unexpected max timestamp: {max_ts}"
    assert unique_devices == 5, f"Expected 5 device types, got {unique_devices}"
    
    # Check device types
    device_types = [row[0] for row in con.execute(f"SELECT DISTINCT Device_Type FROM read_csv('{escaped_csv}', header=true)").fetchall()]
    con.close()
    
    assert set(device_types) == {"Windows_Browser", "iOS", "Android", "Web_Emulator", "Linux_Script"}


def test_validation_reports_generated():
    """Verify that reports/updated_dataset_validation.md and .json exist and report Category A."""
    json_path = REPORTS_DIR / "updated_dataset_validation.json"
    md_path = REPORTS_DIR / "updated_dataset_validation.md"
    
    assert json_path.exists(), "Validation JSON report missing"
    assert md_path.exists(), "Validation Markdown report missing"
    assert md_path.stat().st_size > 1000, "Markdown report appears incomplete"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["source_file"]["name"] == "VoidHacks8_MuleAccount_2M_Transactions.csv"
    assert data["row_and_entity_metrics"]["total_rows"] == 2000000
    assert data["row_and_entity_metrics"]["satisfies_2m_scale"] is True
    assert data["determination"]["category"] == "A. EXPECTED_HIGHER_FIDELITY_COMPETITION_DATASET"
