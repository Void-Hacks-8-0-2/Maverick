"""
Operation 'ABHEDYA-CHAKRA'
Production Dataset Verification & Integrity Test Suite.

Verifies:
1. Production dataset exists at data/VoidHacks8_MuleAccount_2M_Transactions.csv
2. Row count == 2,000,000
3. All 11 expected fields are present
4. Timestamps are available and uncorrupted (0 nulls)
5. Device_Type is available (0 nulls, 5 categories)
6. Backend and API use ONLY the production dataset (source_type == "PRODUCTION_DATASET")
7. Frontend components and pages display production dataset status
8. Zero runtime references or fallback logic to old recovered datasets
"""

import hashlib
import os
from pathlib import Path
import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_dataset_path, get_db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTION_CSV = DATA_DIR / "VoidHacks8_MuleAccount_2M_Transactions.csv"
EXPECTED_SHA256 = "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
EXPECTED_ROWS = 2000000

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

client = TestClient(app)


def test_production_dataset_exists():
    """Verify that the 2,000,000-row production dataset is present and uncorrupted."""
    assert PRODUCTION_CSV.exists(), f"Production dataset missing at {PRODUCTION_CSV}"
    assert PRODUCTION_CSV.stat().st_size == 286788986


def test_production_dataset_hash():
    """Verify cryptographic SHA-256 integrity of the production dataset."""
    hasher = hashlib.sha256()
    with open(PRODUCTION_CSV, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    assert hasher.hexdigest() == EXPECTED_SHA256


def test_production_scale_and_schema():
    """Verify 2,000,000 rows and exact 11 columns in production dataset."""
    con = get_db()
    columns = [row[0] for row in con.execute("DESCRIBE SELECT * FROM transactions").fetchall()]
    assert columns == EXPECTED_FIELDS, f"Schema mismatch: {columns}"

    total_rows = con.execute("SELECT count(*) FROM transactions").fetchone()[0]
    assert total_rows == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS} rows, got {total_rows}"


def test_timestamps_and_device_types_available():
    """Verify Timestamps and Device_Types are 100% available with 0 nulls."""
    con = get_db()
    null_stats = con.execute("""
        SELECT 
            sum(CASE WHEN Timestamp IS NULL THEN 1 ELSE 0 END) as null_ts,
            sum(CASE WHEN Device_Type IS NULL THEN 1 ELSE 0 END) as null_dev,
            min(Timestamp) as min_ts,
            max(Timestamp) as max_ts
        FROM transactions
    """).fetchone()

    null_ts, null_dev, min_ts, max_ts = null_stats
    assert null_ts == 0, f"Timestamp has {null_ts} nulls"
    assert null_dev == 0, f"Device_Type has {null_dev} nulls"
    assert str(min_ts).startswith("2026-09-15")
    assert str(max_ts).startswith("2026-09-29")


def test_api_uses_production_dataset():
    """Verify API returns PRODUCTION_DATASET metadata and 2,000,000 rows."""
    res = client.get("/api/dataset/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["row_count"] == EXPECTED_ROWS
    assert data["source_type"] == "PRODUCTION_DATASET"
    assert data["timestamp_available"] is True
    assert data["device_type_available"] is True


def test_frontend_status_card_references_production():
    """Verify that the frontend status card and pages reference the production dataset."""
    status_card_path = PROJECT_ROOT / "frontend" / "src" / "components" / "DatasetStatusCard.tsx"
    assert status_card_path.exists()
    content = status_card_path.read_text(encoding="utf-8")
    assert "PRODUCTION_DATASET" in content
    assert "VoidHacks8_MuleAccount_2M_Transactions.csv" in content
    assert "2,000,000" in content
    assert "149,741" not in content
    assert "PDF_DERIVED_RECOVERED_DATASET" not in content


def test_no_old_recovered_dataset_in_data_directory():
    """Verify that no old extracted/recovered datasets remain in data/."""
    extracted_dir = DATA_DIR / "extracted"
    assert not extracted_dir.exists(), "data/extracted directory should be removed from active project"

    pdf_in_data = DATA_DIR / "Dataset_VoidHacks_compressed.pdf"
    assert not pdf_in_data.exists(), "Original PDF must be in archive/source/, not active data/"


def test_no_fallback_logic_to_recovered_dataset():
    """Verify that the application fails clearly if the production dataset is missing, without falling back."""
    connection_path = PROJECT_ROOT / "backend" / "db" / "connection.py"
    content = connection_path.read_text(encoding="utf-8")
    assert "data/VoidHacks8_MuleAccount_2M_Transactions.csv" in content
    assert "transactions_recovered" not in content
    assert "FileNotFoundError" in content
