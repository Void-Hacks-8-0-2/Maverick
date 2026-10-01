# Operation "ABHEDYA-CHAKRA" (अभैद्य चक्र)
## Financial Cyber-Forensics & Money-Mule Network Investigation Platform

**Event:** Void Hacks() 8.0  
**Theme:** Abhedya – Cyber Security & Digital Forensics  
**Association:** Indore Police Commissionerate  
**Dataset Scale:** 2,000,000+ Banking Transaction Records  

---

### Overview

Operation **ABHEDYA-CHAKRA** is a locally deployable, high-throughput cyber-forensics platform engineered to ingest, normalize, and analyze 2,000,000+ banking transaction records. It enables law enforcement officers to track multi-tier money mule syndicates, trace victim funds across 4 downstream hops, calculate an explainable 0–100 Mule Risk Index, and instantly generate court-ready Section 91 CrPC / BNSS Bank Freezing Notices and chronological Police Case Diaries.

---

### Project Architecture & Tiers

The system follows a strict three-tier data separation model:
1. **RAW Transaction Preservation Tier:** Pristine, immutable raw transaction storage with zero in-place mutations to protect judicial chain-of-custody.
2. **ANALYTICAL Storage Tier:** High-throughput DuckDB embedded columnar engine with vectorized scans and compound causal filters.
3. **DERIVED / Feature Tier:** Deterministic account-level metrics (fan-in/fan-out, pass-through velocity, and anomaly indicators).

---

### P0 Step 1: Forensic Dataset Profiler

Before running ingestion, the forensic profiler tool inspects candidate transaction datasets and validates schema compliance, account cardinality, financial volumes, temporal spans, and structural metrics:

```bash
# Set up virtual environment
python -m venv backend/.venv
.\backend\.venv\Scripts\pip install -r backend/requirements.txt

# Run profiler against dataset
.\backend\.venv\Scripts\python backend/scripts/inspect_dataset.py --input "<PATH_TO_TRANSACTIONS_CSV>"
```

Outputs:
- `reports/data_profile_report.md` (Human-readable forensic audit)
- `reports/data_profile.json` (Machine-readable profile metrics)

---

### Production Dataset Configuration

The platform operates on the full-scale 2,000,000-row transaction dataset:
- **Required Path:** `data/VoidHacks8_MuleAccount_2M_Transactions.csv`
- **Format:** CSV (273.5 MB, 11 standard columns, RFC 4180)
- **SHA-256:** `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101`
- **Scale:** Exactly 2,000,000 rows, 24,873 unique accounts, ₹3.52B total transacted volume
- **Git Policy:** Due to GitHub's file size limits, the bulk CSV file is excluded from Git tracking via `.gitignore` and must be placed in `data/` locally. If the dataset is absent, the backend fails with an explicit `FileNotFoundError`.
