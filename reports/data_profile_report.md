# Operation 'ABHEDYA-CHAKRA' — Forensic Dataset Profile Report

**Generated:** 2026-10-01T17:34:40Z | **Profiler Version:** 2.0.0-forensic
**Platform:** Windows 11 (AMD64) | **DuckDB:** 1.5.6

---

## 1. Dataset Health & Integrity Summary

| Check | Status |
| :--- | :--- |
| **Schema Conformity** | `VALID` |
| **Row Integrity** | `VALID` |
| **Account Integrity** | `VALID` |
| **Transaction Id Integrity** | `VALID` |
| **Timestamp Integrity** | `VALID` |
| **Amount Integrity** | `VALID` |
| **Ifsc Integrity** | `VALID` |
| **Payment Mode Integrity** | `PASS` |
| **Device Integrity** | `PASS` |
| **Ip Integrity** | `VALID` |
| **Narration Integrity** | `VALID` |


## 2. File Information & Record Counts

- **Path:** `C:\Users\sdmgo\OneDrive\Desktop\Abhedya-Chakara\tests\fixtures\sample_schema_fixture.csv`
- **Size:** 0.0 MB (818 bytes)
- **SHA-256:** `aef80cbaf5452d7b5f21916d93abca550046aa9a5cef588cccc968903156100d`
- **Total Parsed Records:** **5** (Target Reference: 2,000,000)
- **Target Benchmark Status:** `MEASURED_BELOW_REFERENCE`
- **Malformed Records Quarantined:** `0`

## 3. Schema Conformance

- **Status:** `PASS`
- **Column Order Exact Match:** `True`
- **Missing Columns:** `None`
- **Unexpected Columns:** `None`

## 4. Account Distribution & Cardinality

- **Total Unique Accounts (Sender ∪ Receiver):** **6**
- **Unique Senders:** 3
- **Unique Receivers:** 5
- **Problem Statement Reference:** ~25,000 (1,500 mules + 23,500 regular)
- **Sender Non-Digit Accounts:** `0`
- **Receiver Non-Digit Accounts:** `0`

## 5. Financial Volume & Amount Statistics (INR ₹)

- **Total Observed Volume:** ₹145,000.00
- **Min Amount:** ₹10,000.00
- **Max Amount:** ₹50,000.00
- **Median Amount:** ₹25,000.00
- **Unparseable / Negative Amounts:** `0`

## 6. Temporal Analysis

- **Start Timestamp:** `2026-09-10 10:00:00`
- **End Timestamp:** `2026-09-10 10:16:00`
- **Observed Span:** 0 days (Reference: 15-day window)
- **Chronologically Sorted:** `True`
- **Out-of-Order Rows:** `0`

## 7. Categorical Channels & Client Profiles

### Payment Modes Observed

| Mode | Count | Percentage |
| :--- | :--- | :--- |
| **UPI** | 3 | 60.0% |
| **NEFT** | 1 | 20.0% |
| **IMPS** | 1 | 20.0% |

### Client Device Types Observed

| Device Type | Count | Percentage |
| :--- | :--- | :--- |
| **Linux_Script** | 3 | 60.0% |
| **Android** | 1 | 20.0% |
| **Web_Emulator** | 1 | 20.0% |


## 8. Forensic Signals & IP/Narration Observations

- **Unique IP Addresses:** 3
- **185.x.x.x Prefix Count:** `1`
- **194.x.x.x Prefix Count:** `3`
- **RFC1918 Private IP Count:** `0`
- **Unique Narrations:** 5
- **Exploratory Keyword Matches:**
  - `crypto`: 1
  - `usdt`: 1
  - `binance`: 0
  - `p2p`: 1
  - `paxful`: 0
  - `telegram`: 0
  - `wallet`: 1
  - `commission`: 1
  - `task`: 0
  - `refund`: 0


## 9. Profiler Execution Performance

- **Execution Duration:** 0.18 seconds
- **Peak Process RSS:** 76.4 MB (OS-level via psutil)
