"""
Operation 'ABHEDYA-CHAKRA'
Automated Test Suite for P0 Step 1C: Recoverable PDF Dataset Export
Authoritative Reference: Void Hacks() 8.0 Problem Statement
"""

import json
import hashlib
from pathlib import Path
import duckdb
import pytest

DATA_DIR = Path("data/extracted")
CSV_PATH = DATA_DIR / "transactions_recovered.csv"
PARQUET_PATH = DATA_DIR / "transactions_recovered.parquet"
PROV_PATH = DATA_DIR / "transactions_recovered_provenance.parquet"
MANIFEST_PATH = DATA_DIR / "transactions_recovered_manifest.json"
AUDIT_JSON_PATH = Path("reports/recovered_dataset_export_audit.json")
AUDIT_MD_PATH = Path("reports/recovered_dataset_export_audit.md")
SAMPLE_JSON_PATH = Path("reports/recovered_dataset_sample.json")

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

EXPECTED_PDF_SHA256 = "b116a7df4355c9776259e4c95e80400139d74ce3ed87dffc09cd35e3eaafc860"


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.exists(), f"Manifest file missing at {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def db_conn():
    con = duckdb.connect(database=":memory:")
    yield con
    con.close()


def test_artifacts_exist():
    assert CSV_PATH.exists(), "transactions_recovered.csv is missing"
    assert PARQUET_PATH.exists(), "transactions_recovered.parquet is missing"
    assert PROV_PATH.exists(), "transactions_recovered_provenance.parquet is missing"
    assert MANIFEST_PATH.exists(), "transactions_recovered_manifest.json is missing"
    assert AUDIT_JSON_PATH.exists(), "recovered_dataset_export_audit.json is missing"
    assert AUDIT_MD_PATH.exists(), "recovered_dataset_export_audit.md is missing"
    assert SAMPLE_JSON_PATH.exists(), "recovered_dataset_sample.json is missing"


def test_schema_exact_11_columns(db_conn):
    pq_cols = [c[0] for c in db_conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{PARQUET_PATH}') LIMIT 1").fetchall()]
    assert pq_cols == EXPECTED_SCHEMA, f"Parquet columns {pq_cols} do not match {EXPECTED_SCHEMA}"

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        header_line = f.readline().strip()
        csv_cols = header_line.split(",")
    assert csv_cols == EXPECTED_SCHEMA, f"CSV columns {csv_cols} do not match {EXPECTED_SCHEMA}"


def test_timestamp_and_device_always_null(db_conn, manifest):
    total_rows = manifest["row_count"]
    assert total_rows > 0

    null_ts = db_conn.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE Timestamp IS NULL").fetchone()[0]
    assert null_ts == total_rows, f"Expected all {total_rows} Timestamps to be NULL, found {null_ts}"

    null_dev = db_conn.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE Device_Type IS NULL").fetchone()[0]
    assert null_dev == total_rows, f"Expected all {total_rows} Device_Types to be NULL, found {null_dev}"

    csv_non_null_ts = db_conn.execute(f"SELECT COUNT(*) FROM read_csv('{CSV_PATH}', header=true) WHERE Timestamp IS NOT NULL AND Timestamp != ''").fetchone()[0]
    assert csv_non_null_ts == 0, f"Found {csv_non_null_ts} non-empty timestamps in CSV"

    csv_non_null_dev = db_conn.execute(f"SELECT COUNT(*) FROM read_csv('{CSV_PATH}', header=true) WHERE Device_Type IS NOT NULL AND Device_Type != ''").fetchone()[0]
    assert csv_non_null_dev == 0, f"Found {csv_non_null_dev} non-empty device types in CSV"


def test_no_synthetic_values(manifest):
    assert manifest["synthetic_rows_added"] == 0, "Synthetic rows were added!"
    assert manifest["fabricated_values_added"] == 0, "Fabricated values were added!"
    assert manifest["timestamp_status"] == "UNAVAILABLE_IN_SOURCE_PDF"
    assert manifest["device_type_status"] == "ABSENT_FROM_SOURCE_PDF"


def test_row_count_reconciliation(db_conn, manifest):
    expected_rows = manifest["row_count"]
    assert expected_rows > 0

    pq_rows = db_conn.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    csv_rows = db_conn.execute(f"SELECT COUNT(*) FROM read_csv('{CSV_PATH}', header=true)").fetchone()[0]
    prov_rows = db_conn.execute(f"SELECT COUNT(*) FROM read_parquet('{PROV_PATH}')").fetchone()[0]

    assert pq_rows == expected_rows, f"Parquet row count {pq_rows} != manifest {expected_rows}"
    assert csv_rows == expected_rows, f"CSV row count {csv_rows} != manifest {expected_rows}"
    assert prov_rows == expected_rows, f"Provenance row count {prov_rows} != manifest {expected_rows}"


def test_transaction_id_preservation(db_conn, manifest):
    pq_tx_count = db_conn.execute(f"SELECT COUNT(DISTINCT Transaction_ID) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    csv_tx_count = db_conn.execute(f"SELECT COUNT(DISTINCT Transaction_ID) FROM read_csv('{CSV_PATH}', header=true)").fetchone()[0]
    assert pq_tx_count == csv_tx_count

    malformed = db_conn.execute(f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE NOT regexp_matches(Transaction_ID, '^TXN[A-Za-z0-9_]+$')").fetchone()[0]
    assert malformed == 0, f"Found {malformed} malformed Transaction_IDs"


def test_amount_reconciliation(db_conn, manifest):
    expected_sum = manifest["amount_statistics"]["sum"]
    pq_sum = db_conn.execute(f"SELECT SUM(Amount) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    csv_sum = db_conn.execute(f"SELECT SUM(TRY_CAST(Amount AS DOUBLE)) FROM read_csv('{CSV_PATH}', header=true)").fetchone()[0]

    assert abs(expected_sum - pq_sum) < 0.05, f"Parquet sum {pq_sum} != expected {expected_sum}"
    assert abs(expected_sum - csv_sum) < 0.05, f"CSV sum {csv_sum} != expected {expected_sum}"

    min_amt = db_conn.execute(f"SELECT MIN(Amount) FROM read_parquet('{PARQUET_PATH}')").fetchone()[0]
    assert min_amt > 0, f"Found non-positive amount {min_amt}"


def test_payment_modes(db_conn, manifest):
    modes = [r[0] for r in db_conn.execute(f"SELECT DISTINCT Payment_Mode FROM read_parquet('{PARQUET_PATH}')").fetchall()]
    allowed = {"UPI", "IMPS", "NEFT", "RTGS"}
    for m in modes:
        assert m in allowed, f"Unexpected payment mode: {m}"


def test_ip_validation(db_conn):
    invalid_ips = db_conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE NOT regexp_matches(IP_Address, '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){{3}}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')"
    ).fetchone()[0]
    assert invalid_ips == 0, f"Found {invalid_ips} invalid IP addresses"


def test_account_and_ifsc_lengths(db_conn):
    invalid_accs = db_conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE length(Sender_Account) != 12 OR length(Receiver_Account) != 12"
    ).fetchone()[0]
    assert invalid_accs == 0, f"Found {invalid_accs} invalid account numbers"

    invalid_ifscs = db_conn.execute(
        f"SELECT COUNT(*) FROM read_parquet('{PARQUET_PATH}') WHERE length(Sender_IFSC) != 11 OR length(Receiver_IFSC) != 11"
    ).fetchone()[0]
    assert invalid_ifscs == 0, f"Found {invalid_ifscs} invalid IFSC codes"


def test_provenance_integrity(db_conn, manifest):
    total_rows = manifest["row_count"]
    min_seq, max_seq = db_conn.execute(f"SELECT MIN(source_sequence_number), MAX(source_sequence_number) FROM read_parquet('{PROV_PATH}')").fetchone()
    assert min_seq == 1
    assert max_seq == total_rows

    distinct_seq = db_conn.execute(f"SELECT COUNT(DISTINCT source_sequence_number) FROM read_parquet('{PROV_PATH}')").fetchone()[0]
    assert distinct_seq == total_rows


def test_pdf_sha256_consistency(manifest):
    assert manifest["source_pdf_sha256"] == EXPECTED_PDF_SHA256


def test_audit_json_structure():
    with open(AUDIT_JSON_PATH, "r", encoding="utf-8") as f:
        a = json.load(f)

    required_keys = [
        "source", "schema", "counts", "validation", "reconciliation",
        "null_counts", "payment_modes", "amount_statistics",
        "provenance", "hashes", "limitations", "final_status"
    ]
    for k in required_keys:
        assert k in a, f"Key '{k}' missing from recovered_dataset_export_audit.json"
    assert a["final_status"] == "PASS_RECOVERED_DATASET_CREATED"


def test_audit_md_18_sections():
    with open(AUDIT_MD_PATH, "r", encoding="utf-8") as f:
        md = f.read()

    assert "This dataset is derived from the supplied PDF" in md
    assert "Timestamp and Device_Type are unavailable" in md

    for i in range(1, 19):
        assert f"## {i}." in md, f"Section {i} missing from markdown audit"


def test_sample_json_records():
    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)

    assert len(samples) > 0
    pages_sampled = {s["source_page"] for s in samples}
    assert len(pages_sampled) >= 3, "Expected samples across multiple pages"
    for s in samples:
        assert s["Timestamp"] is None
        assert s["Device_Type"] is None
        assert s["Transaction_ID"].startswith("TXN")
