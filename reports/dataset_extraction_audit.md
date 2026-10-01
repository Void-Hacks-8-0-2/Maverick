# Operation 'ABHEDYA-CHAKRA' — PDF Extraction & Forensic Audit Report

**Audit Status:** `BLOCKED`

> **Final Gate Determination:** BLOCKED — extraction cannot be trusted; Phase 1 must not proceed

---

## 1. Source Document Information

- **Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\data\Dataset_VoidHacks_compressed.pdf`
- **File Size:** 23.7 MB (24,853,708 bytes)
- **SHA-256:** `b116a7df4355c9776259e4c95e80400139d74ce3ed87dffc09cd35e3eaafc860`
- **Page Count:** 3,186
- **Originating Software:** `Microsoft® Excel® 2021`
- **Producer / Compressor:** `iLovePDF`
- **Creation Date:** `D:20261001205305+05'30'`

## 2. Forensic Blocking Issues

### Issue 2.1: [CRITICAL] MISSING_COLUMN_DEVICE_TYPE

- **Description:** Column 'Device_Type' is completely absent from PDF header and all data rows. The Excel-to-PDF print clipped the 11th column off the right page margin.
- **Evidence:** `Header line text: 'Transaction_IDSender_AccountReceiver_AccountSender_IFSCReceiver_IFSCAmountTimestampPayment_ModeNarrationIP_Address'`

### Issue 2.2: [CRITICAL] CORRUPTED_TIMESTAMPS_EXCEL_OVERFLOW

- **Description:** Timestamps are unparseable literal '########' on 93/93 (100.0%) sampled rows. Excel exported narrow date column as overflow hash characters, permanently destroying temporal money trail causality.
- **Evidence:** `Observed in all sample rows: '... ######## IMPS ...'`

### Issue 2.3: [HIGH] INSUFFICIENT_DATASET_SCALE

- **Description:** Estimated total rows across 3,186 pages is ~148,149 rows. The official Problem Statement requires a scale of 2,000,000+ banking transaction records. The PDF contains only ~148,149 rows (~5% of required dataset).
- **Evidence:** `Total pages: 3186, Avg rows/page: 46.5`

## 3. Schema Audit (Expected vs Actual)

| Column Name | Expected (PDF Spec) | Actual (in Dataset PDF) | Status |
| :--- | :--- | :--- | :--- |
| `Transaction_ID` | Yes | Yes | `FOUND` |
| `Sender_Account` | Yes | Yes | `FOUND` |
| `Receiver_Account` | Yes | Yes | `FOUND` |
| `Sender_IFSC` | Yes | Yes | `FOUND` |
| `Receiver_IFSC` | Yes | Yes | `FOUND` |
| `Amount` | Yes | Yes | `FOUND` |
| `Timestamp` | Yes | Yes | `FOUND` |
| `Payment_Mode` | Yes | Yes | `FOUND` |
| `Narration` | Yes | Yes | `FOUND` |
| `IP_Address` | Yes | Yes | `FOUND` |
| `Device_Type` | Yes | NO | `CRITICALLY_MISSING` |


## 4. Data Integrity & Scale Audit

- **Sampled Pages:** 2
- **Sampled Rows:** 93
- **Rows with Corrupted '########' Timestamps:** 93 (100.0%)
- **Estimated Total PDF Rows:** ~148,149 rows
- **Problem Statement Scale Requirement:** 2,000,000+ rows
- **Scale Deficit:** ~1,851,851 missing rows (~95% deficit)

## 5. Recommended Actions for Hackathon Organizers / Team

1. Request the original raw uncorrupted dataset (.csv, .parquet, or .xlsx) from Void Hacks / Indore Police organizers.
1. Ensure the source export includes un-truncated column widths (preserving YYYY-MM-DD HH:MM:SS timestamps).
1. Ensure the source export includes the 11th column 'Device_Type'.
1. Ensure the source export contains the full 2,000,000+ transaction scale.


## 6. Audit Execution Performance

- **Wall-clock Duration:** 3.4 seconds
- **Peak Process RSS:** 166.93 MB (via `psutil`)
