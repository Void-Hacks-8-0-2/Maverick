import pytest
from pathlib import Path
from backend.scripts.extract_dataset_pdf import EXPECTED_SCHEMA, PDFDatasetExtractor

def test_expected_schema_definition():
    """Verify expected 11 columns from the Problem Statement PDF."""
    assert len(EXPECTED_SCHEMA) == 11
    assert "Transaction_ID" in EXPECTED_SCHEMA
    assert "Sender_Account" in EXPECTED_SCHEMA
    assert "Receiver_Account" in EXPECTED_SCHEMA
    assert "Sender_IFSC" in EXPECTED_SCHEMA
    assert "Receiver_IFSC" in EXPECTED_SCHEMA
    assert "Amount" in EXPECTED_SCHEMA
    assert "Timestamp" in EXPECTED_SCHEMA
    assert "Payment_Mode" in EXPECTED_SCHEMA
    assert "Narration" in EXPECTED_SCHEMA
    assert "IP_Address" in EXPECTED_SCHEMA
    assert "Device_Type" in EXPECTED_SCHEMA

def test_missing_column_and_timestamp_gate_blocking():
    """Verify that an extraction gate BLOCKS if Device_Type is absent or timestamps are corrupted."""
    pdf_path = Path("data/Dataset_VoidHacks_compressed.pdf")
    if not pdf_path.exists():
        pytest.skip("Dataset PDF not present in environment")

    extractor = PDFDatasetExtractor(str(pdf_path))
    audit_result, sample_records = extractor.run_forensic_audit(sample_pages_count=5)

    # Must BLOCK per failure policy
    assert audit_result["final_gate"] == "BLOCKED"
    blocking_codes = [b["code"] for b in audit_result["blocking_issues"]]
    assert "MISSING_COLUMN_DEVICE_TYPE" in blocking_codes
    assert "CORRUPTED_TIMESTAMPS_EXCEL_OVERFLOW" in blocking_codes

def test_report_generation():
    """Verify audit and sample JSON reports are generated."""
    pdf_path = Path("data/Dataset_VoidHacks_compressed.pdf")
    if not pdf_path.exists():
        pytest.skip("Dataset PDF not present in environment")

    extractor = PDFDatasetExtractor(str(pdf_path))
    audit_result, sample_records = extractor.run_forensic_audit(sample_pages_count=2)
    extractor.save_reports(audit_result, sample_records)

    assert Path("reports/dataset_extraction_audit.json").exists()
    assert Path("reports/dataset_extraction_sample.json").exists()
    assert Path("reports/dataset_extraction_audit.md").exists()
