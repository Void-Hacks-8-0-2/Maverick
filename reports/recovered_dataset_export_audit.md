# Operation 'ABHEDYA-CHAKRA' — Recovered PDF Dataset Export Audit (P0 Step 1C)

> This dataset is derived from the supplied PDF and contains only fields recoverable from that PDF. Timestamp and Device_Type are unavailable. It is not equivalent to the official 2,000,000+ transaction dataset described in the problem statement.

## 1. Executive Summary

- **Task Outcome:** `PASS_RECOVERED_DATASET_CREATED`
- **Valid Recovered Transactions:** **`149,741`**
- **Execution Duration:** `43.55s` | **Peak RSS:** `636.49 MB`
- **Reconciliation Status:** All 6 independent mathematical and schema gates passed successfully.
- **Intended Use:** Non-temporal integration testing, schema alignment, and graph engine skeleton development.

## 2. Source PDF Identity

- **File Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\Dataset_VoidHacks_compressed.pdf`
- **SHA-256:** `b116a7df4355c9776259e4c95e80400139d74ce3ed87dffc09cd35e3eaafc860`
- **Total Pages:** `3,186`
- **Official Dataset Status:** `INCOMPLETE_SOURCE`

## 3. Recovery Method

- Utilized high-performance Google PDFium text-stream extraction via `pypdfium2`.
- Extracted lines and applied precise regular expression boundary matching matching exact fixed-width column cells.
- Recovered 9 available fields directly from raw character sequences.
- Preserved raw physical PDF page traversal order (no artificial sorting or reordering).

## 4. Recovered Schema

| Column Name | Analytical Type | Recovery Status | Null Count |
| :--- | :--- | :--- | :--- |
| `Transaction_ID` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Sender_Account` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Receiver_Account` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Sender_IFSC` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Receiver_IFSC` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Amount` | `DOUBLE` | `RECOVERED (100%)` | `0` |
| `Timestamp` | `TIMESTAMP NULL` | `UNAVAILABLE (All NULL)` | `149,741` |
| `Payment_Mode` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Narration` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `IP_Address` | `VARCHAR` | `RECOVERED (100%)` | `0` |
| `Device_Type` | `VARCHAR NULL` | `UNAVAILABLE (All NULL)` | `149,741` |


## 5. Missing Fields

- **Timestamp:** Rendered as literal `########` across all 3,186 pages due to Excel column width truncation prior to PDF export. Represented strictly as `NULL` / empty string. Zero values fabricated or interpolated.
- **Device_Type:** Completely absent from the PDF page layout and margins. Represented strictly as `NULL` / empty string. Zero values inferred or guessed.

## 6. Row Counts

- **Candidate Rows:** `149,741`
- **Valid Recovered Rows:** `149,741`
- **Invalid Rows:** `0`
- **Header Rows Filtered:** `1`
- **Previous Step 1A Estimated Rows:** `149,678`
- **Difference from Estimate:** `63` rows (previous estimate was based on 47.0 lines/page sample)

## 7. Validation Results

- **Duplicate Transaction IDs:** `16`
- **Invalid IP Formats:** `0`
- **Invalid Account Lengths:** `0`
- **Invalid IFSC Lengths:** `0`
- **Synthetic Rows Added:** `0`
- **Fabricated Values Added:** `0`

## 8. Amount Reconciliation

- **Valid Amount Count:** `149,741`
- **Source Recovered Sum:** `₹468,161,474.43`
- **Parquet Readback Sum:** `₹468,161,474.43`
- **CSV Readback Sum:** `₹468,161,474.43`
- **Min / Max / Mean:** `₹1.13` / `₹499,824.00` / `₹3,126.47`
- **Amount Sum Reconciliation Gate:** `PASS`

## 9. Payment Mode Distribution

| Payment Mode | Count | Proportion |
| :--- | :--- | :--- |
| **IMPS** | `33,740` | `22.53%` |
| **UPI** | `97,047` | `64.81%` |
| **RTGS** | `4,417` | `2.95%` |
| **NEFT** | `14,537` | `9.71%` |


## 10. IP Validation

- **Valid IPv4 Addresses:** `149,741` (100.0%)
- **Invalid IP Addresses:** `0`

## 11. Account/IFSC Validation

- **Valid 12-char Sender Accounts:** `149,741` (100.0%)
- **Valid 12-char Receiver Accounts:** `149,741` (100.0%)
- **Valid 11-char Sender IFSCs:** `149,741` (100.0%)
- **Valid 11-char Receiver IFSCs:** `149,741` (100.0%)

## 12. Provenance

- **Sidecar Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered_provenance.parquet`
- **Sidecar SHA-256:** `106e65728b2a570ee09b19c02c9c2b37025f9e73db9f48611ddd2108d31ea0e1`
- **Total Provenance Records:** `149,741`
- **Sequence Range:** `1` to `149741` (continuous 1-to-N preservation of source traversal order)
- **Provenance Validation Gate:** `PASS`

## 13. CSV Validation

- **File Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered.csv`
- **SHA-256:** `2000786ebf61e9537c3994ea0f8a954c112bbcd8b8d324a5e00fa04079510755`
- **Readback Rows:** `149,741`
- **Columns:** Exactly 11 columns with UTF-8 encoding and empty string representation for NULLs.
- **Verification:** Successfully parsed with DuckDB `read_csv`.

## 14. Parquet Validation

- **File Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered.parquet`
- **SHA-256:** `50c49e275adca66c46381e1073ecedd096240b4628ed4ab254a23d175bd2c848`
- **Readback Rows:** `149,741`
- **Columns:** Exactly 11 columns with strongly-typed PyArrow schema (`TIMESTAMP(ms)` nulls and `VARCHAR` nulls).
- **Verification:** Successfully parsed with DuckDB `read_parquet`.

## 15. SHA-256 Integrity

| Artifact | File Path | SHA-256 Checksum |
| :--- | :--- | :--- |
| **Source PDF** | `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\Dataset_VoidHacks_compressed.pdf` | `b116a7df4355c9776259e4c95e80400139d74ce3ed87dffc09cd35e3eaafc860` |
| **Recovered CSV** | `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered.csv` | `2000786ebf61e9537c3994ea0f8a954c112bbcd8b8d324a5e00fa04079510755` |
| **Recovered Parquet** | `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered.parquet` | `50c49e275adca66c46381e1073ecedd096240b4628ed4ab254a23d175bd2c848` |
| **Provenance Sidecar** | `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\extracted\transactions_recovered_provenance.parquet` | `106e65728b2a570ee09b19c02c9c2b37025f9e73db9f48611ddd2108d31ea0e1` |


## 16. Limitations

- Timestamp is completely unavailable (rendered as '########' in source PDF due to Excel column width clipping before print). Set to NULL.
- Device_Type was omitted from print margins in the source PDF. Set to NULL.
- Recovered row count (~149k) is far below the official 2M+ production requirement.
- Velocity pass-through heuristics (3-15 min) and temporal sorting cannot be evaluated on this dataset.
- This dataset is strictly an interim development/integration artifact.


## 17. Development Usage Rules

1. **Do NOT run temporal / velocity window analysis:** Timestamps are strictly `NULL`. Velocity pass-through (e.g. 3-15 min windowing) cannot be calculated on this recovered artifact.
2. **Do NOT run device anomaly heuristics:** `Device_Type` is strictly `NULL`. Heuristics like `Web_Emulator` or `Linux_Script` are not applicable.
3. **Permitted Workloads:** Graph topology construction, account in/out-degree calculation, cycle detection, IFSC branch mapping, bank concentration, and UI dashboard visualization of accounts/transactions.
4. **Do NOT sort or reorder:** Source order is preserved in `source_sequence_number`. Do not attempt to sort by Timestamp.

## 18. Final Status

### `PASS_RECOVERED_DATASET_CREATED`

The recoverable PDF transaction data has been extracted, validated, and reconciled with 100% mathematical fidelity. The dataset is ready for interim development use.
