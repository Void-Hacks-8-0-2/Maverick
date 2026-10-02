# OPERATION “ABHEDYA-CHAKRA” — STEP 7 FORENSIC ENGINEERING REPORT

**Module:** Evidence Package + Case File Engine  
**Dataset:** `data/VoidHacks8_MuleAccount_2M_Transactions.csv` (2,000,000 transactions, 24,873 accounts)  
**Dataset SHA-256:** `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101` (Verified / Untouched)  
**Status:** COMPLETE & VERIFIED — 144/144 Backend Tests Passing, Production Build Passing  

---

## 1. Executive Summary & Objective

Step 7 delivers the forensic conclusion of Operation “Abhedya-Chakra”: transforming live multi-hop victim investigations into structured, reproducible, tamper-sealed forensic case files and compiled evidence artifacts.

The engine produces:
1. **Canonical JSON Evidence Package (`application/json`)**: A strongly typed, deterministic data snapshot capturing all observed account facts, transaction records, Step 5C attribution paths, Step 5B official risk family points, Step 5A velocity diagnostics, Step 4 mule role indicators, and explicit analytical limitations.
2. **Deterministic Multi-Page PDF Forensic Report (`application/pdf`)**: A courtroom-ready, neutrally phrased technical report detailing all 12 required investigative sections with embedded cryptographic SHA-256 seals.
3. **RESTful Case File API**: Endpoints for synchronous generation and cached retrieval of metadata, PDF artifacts, and raw JSON packages.
4. **Investigation Workspace Integration**: One-click case file dossier creation within the frontend investigation interface.

---

## 2. Architecture & Component Structure

```
backend/case_files/
├── __init__.py            # Package exports
├── models.py              # Strongly typed Pydantic contracts & schemas
├── store.py               # In-memory thread-safe CaseFileStore singleton
├── pdf_generator.py       # ReportLab 5.0.1 multi-page document layout & styling
└── generator.py           # Investigation snapshot reconstruction, canonical hashing & orchestration
```

### Component Details
- **`backend.case_files.models`**: Pydantic schemas enforcing strict types, explicit descriptions, field provenance, and zero-fabrication guarantees.
- **`backend.case_files.store`**: Thread-safe memory store caching `CaseFileResponse`, PDF binary streams, and JSON payloads indexed by `case_file_id`. Zero raw filesystem exposure.
- **`backend.case_files.pdf_generator`**: Pure Python PDF compilation utilizing ReportLab 5.0.1. Renders a consistent two-column metadata header, forensic summary cards, structured data tables, visual callouts, and page numbering (`Page X of Y`).
- **`backend.case_files.generator`**: Orchestrates DuckDB investigation reconstruction, computes canonical JSON serialization, calculates SHA-256 checksums, and compiles artifacts.

---

## 3. Schema Contracts & Data Models

### CaseFileRequest & CaseFileResponse
```python
class CaseFileRequest(BaseModel):
    account_number: str
    max_hops: int = 4
    horizon_seconds: Optional[int] = None
    max_branches_per_hop: int = 50
    investigator_notes: Optional[str] = None

class CaseFileResponse(BaseModel):
    metadata: CaseFileMetadata
    evidence_snapshot: EvidenceSnapshot
    trace: AttributionTraceResponse
    warnings: List[str]
    evidence_narrative: str
```

### CaseFileMetadata
```python
class CaseFileMetadata(BaseModel):
    case_file_id: str                   # e.g. CASE-KKBK10000402-D5DB33F5
    investigation_id: str              # e.g. INV-KKBK10000402-95FCF1FE
    subject_account: str               # Evaluated entity
    status: str                        # COMPLETED / TRUNCATED
    created_at: str                    # ISO-8601 UTC
    source_dataset: str                # VoidHacks8_MuleAccount_2M_Transactions.csv
    dataset_rows: int                  # Exactly 2,000,000
    dataset_sha256: str                # 2c9f81fd34f7...
    evidence_snapshot_sha256: str      # Canonical JSON SHA-256 seal
    pdf_sha256: Optional[str]          # SHA-256 seal over generated PDF document
    json_sha256: Optional[str]         # SHA-256 seal over generated JSON package
    pdf_download_url: str              # /api/case-files/{id}/pdf
    json_download_url: str             # /api/case-files/{id}/json
    disclaimer: str                    # Standard forensic notice
```

### EvidenceSnapshot Sub-Models
- **`ObservedFacts`**: Pure factual accounting of observed volumes, net flow delta, transaction counts, counterparties, unique IPs, and devices.
- **`OfficialRiskBreakdown`**: Step 5B 0–100 Mule Risk Index, risk band, and the exact 6 official risk families:
  1. `FLOW_STRUCTURE`
  2. `VELOCITY`
  3. `AUTOMATION`
  4. `NETWORK_STRUCTURE`
  5. `TRANSACTION_BEHAVIOR`
  6. `ROLE_SUPPORT`
- **`AttributionSummary`**: Distinguishes `root_seed_outflow` from `downstream_cumulative_attribution` and explicitly documents money conservation.
- **`InvestigationLimitations`**: Closed observation window, heuristic status, lack of external labels, branch limits, truncation indicators, and detected cycle loops.

---

## 4. Cryptographic Hashing & Evidence Integrity

1. **Canonical JSON Serialization**:
   - Fields sorted alphabetically (`sort_keys=True`).
   - Compact whitespace delimiters (`separators=(',', ':')`).
   - UTF-8 byte encoding.
2. **Evidence Snapshot SHA-256**:
   ```python
   canonical_json = json.dumps(snapshot.model_dump(), sort_keys=True, separators=(',', ':')).encode('utf-8')
   snapshot_sha256 = hashlib.sha256(canonical_json).hexdigest()
   ```
3. **Artifact Seals**:
   - `pdf_sha256`: SHA-256 computed directly over compiled ReportLab PDF bytes.
   - `json_sha256`: Matches `snapshot_sha256`.
4. **Forensic Integrity Notice**:
   > **Integrity Seal Disclaimer:** SHA-256 provides an algorithmic integrity seal verifying that the generated document and evidence payload have not been altered post-generation. It does not by itself establish legal chain of custody.

---

## 5. ReportLab PDF Generation (All 12 Sections)

The PDF generator implements a clean, high-density layout using `SimpleDocTemplate` and custom `NumberedCanvas` tracking total page count.

| Section # | Section Title | Contents |
|---|---|---|
| **1** | Forensic Case Metadata & Evidence Seals | Case File ID, Investigation ID, Subject Account, Generation Time, Dataset Name, Rows (2,000,000), Dataset SHA-256, Snapshot SHA-256, PDF SHA-256. |
| **2** | Investigative Scope & Subject Mandate | Context of investigation, observation window, analytical scope. |
| **3** | Subject Account Activity & Observed Facts | Total incoming/outgoing volumes, net delta, counts, unique counterparties, IP count, device types. |
| **4** | Root Subject Transactions Under Review | Tabular listing of up to 10 subject transactions with row_id, timestamp, direction, counterparty, amount, and payment mode. |
| **5** | Attribution Conservation & Traversal Integrity | Clear separation of Root Outflow from Downstream Attribution; explicit conservation note; edge counts. |
| **6** | Multi-Hop Fund Attribution Trace Breakdown | Tabular trace displaying Hop Number, Edge Type (ROOT_SEED vs FIFO_ATTRIBUTION), Source, Intermediary, Destination, Attributed Amount, and Delay. |
| **7** | Terminal Recipient Accounts Identified | Final downstream absorption accounts, received amounts, and terminal hop index. |
| **8** | Official Step 5B Mule Risk Score Breakdown | 0–100 Mule Risk Index, Risk Band, and table of all 6 official risk families with point contributions. |
| **9** | Step 5A Velocity & Pass-Through Diagnostics | 3–15 minute pass-through status, ratio, qualifying event count, attributed volume, median delay. |
| **10** | Step 4 Mule Role Classification Indicators | L1/L2/L3 candidate flags, fan-in, fan-out, and specific classification reason codes. |
| **11** | Factual Investigative Summary | Neutral factual summary synthesizing flow, velocity, attribution, and risk without legal certainty. |
| **12** | Limitations & Forensic Disclaimers | Observation window, absence of ground-truth labels, branch limits, truncation/cycle warnings, and integrity seal notice. |

---

## 6. Neutral Forensic Language Compliance

In accordance with strict forensic guidelines, all generated strings, summaries, labels, and disclaimers adhere to objective analytical standards:
- **Forbidden words**: "guilty", "criminal", "fraudster", "illicit", "illegal", "money launderer".
- **Standard terminology**: "Subject account under review", "L3 Terminal Candidate", "Pass-through candidate", "Mule Risk Index", "Candidate indicators", "Investigative attribution".

---

## 7. API Endpoints

| Method | Path | Description | Response Type |
|---|---|---|---|
| `POST` | `/api/case-files` | Generate new forensic case file | `application/json` (`CaseFileResponse`) |
| `GET` | `/api/case-files/{id}` | Retrieve case file dossier | `application/json` (`CaseFileResponse`) |
| `GET` | `/api/case-files/{id}/pdf` | Download compiled PDF report | `application/pdf` (Attachment) |
| `GET` | `/api/case-files/{id}/json` | Download raw JSON evidence package | `application/json` (Attachment) |

---

## 8. Frontend Integration (`/victim` Workspace)

- **Action Button**: "Create Case File" / "Generating Evidence Dossier..." added to the investigation header.
- **Evidence Dossier Panel**: Renders immediately upon generation:
  - Header with Case File ID, status badge, and generation timestamp.
  - Cryptographic Verification Card displaying Snapshot SHA-256 and PDF SHA-256.
  - Financial Attribution Integrity Card contrasting Root Outflow vs Downstream Cumulative Attribution with money conservation explanation.
  - Official Step 5B 6-Family Risk Breakdown Cards.
  - Download Buttons: Direct links to `/api/case-files/{id}/pdf` and `/api/case-files/{id}/json`.

---

## 9. Verification & Test Suite Results

The comprehensive test suite (`tests/test_case_files.py`) validates 24 distinct scenarios:

1. `test_case_file_valid_investigation`: Full pipeline returns 200 with valid metadata.
2. `test_case_file_invalid_account_404`: Non-existent account returns 404.
3. `test_case_file_snapshot_contains_tx_ids`: Observed transactions retain exact `Transaction_ID`.
4. `test_case_file_snapshot_contains_row_ids`: Transactions retain database `rowid`.
5. `test_case_file_dataset_sha_preserved`: Correct production dataset SHA-256 embedded.
6. `test_case_file_evidence_sha_deterministic`: Two snapshots with identical data yield identical SHA-256.
7. `test_case_file_pdf_generated`: Valid PDF bytes returned (starts with `%PDF-`).
8. `test_case_file_document_hash_generated`: Metadata includes valid 64-char hex SHA-256.
9. `test_case_file_json_package_generated`: Complete JSON evidence snapshot downloadable.
10. `test_case_file_root_seed_preserved`: Hop 1 edges marked `ROOT_SEED`.
11. `test_case_file_fifo_edges_preserved`: Downstream edges marked `FIFO_ATTRIBUTION` with correct intermediaries.
12. `test_case_file_risk_score_matches`: Risk Index exactly matches Step 5B.
13. `test_case_file_official_risk_family_scores_preserved`: All 6 official family points present.
14. `test_case_file_velocity_matches`: Velocity metrics match Step 5A.
15. `test_case_file_roles_match`: Role classifications match Step 4.
16. `test_case_file_truncation_warning_preserved`: Branch truncation sets `is_truncated=True`.
17. `test_case_file_cycle_warning_preserved`: Fund flow loops captured in `cycles_detected`.
18. `test_case_file_limitations_included`: Observation window and ground-truth disclaimers present.
19. `test_case_file_no_fabricated_evidence`: Only observed transactions appear in snapshot.
20. `test_case_file_no_legal_certainty_language`: Narrative free of prohibited guilt terms.
21. `test_case_file_arbitrary_account`: Supports any arbitrary account.
22. `test_case_file_does_not_modify_production_csv`: Dataset integrity verified.
23. `test_case_file_repeated_generation_analytically_identical`: Deterministic repeated runs.
24. `test_case_file_pdf_sections_verified`: All 12 forensic sections extracted and confirmed via `pypdf`.

### Test Execution Summary
```
============================= test session starts =============================
collected 144 items

144 passed in 75.49s (0:01:15)
- Step 1–5C baseline: 100 passed
- Step 6 victim investigations: 20 passed
- Step 7 forensic case files: 24 passed
============================== 144 passed ==============================
```

---

## 10. Production Benchmark & Verification Data

Empirical benchmark execution over the live 2,000,000-row production dataset:

### Subject Account: KKBK10000402
- **Case File ID**: `CASE-KKBK10000402-D5DB33F5`
- **End-to-End Generation Time**: **560.88 ms** (Target: < 3,000 ms)
- **Evidence Snapshot SHA-256**: `dd01ffbe16e397c86382e26e6cb6993024957a5b793c88962188803e2e835e42`
- **PDF Size**: 11,470 bytes
- **PDF SHA-256**: `bd233dd700f260dafdec105ec7728f3ea6ebee3a161c73f36d78fee758b2c07e`
- **JSON Package Size**: 26,672 bytes
- **Mule Risk Index**: **70.0 / 100** (`HIGH`)
- **Official Risk Family Breakdown**:
  - `FLOW_STRUCTURE`: 20.0 pts
  - `VELOCITY`: 25.0 pts
  - `AUTOMATION`: 14.0 pts
  - `NETWORK_STRUCTURE`: 2.0 pts
  - `TRANSACTION_BEHAVIOR`: 5.0 pts
  - `ROLE_SUPPORT`: 4.0 pts
  - **Total**: 70.0 pts
- **Root Outflow Under Review**: INR 971,320.06
- **Downstream Cumulative Attribution**: INR 952,468.40 (across 2 downstream hops)
- **Terminal Absorption Accounts**: 15

### Arbitrary Account 1: AIRP10000595
- **Case File ID**: `CASE-AIRP10000595-FB033D3A`
- **End-to-End Generation Time**: **236.12 ms**
- **Evidence Snapshot SHA-256**: `8a2a17a55a36dbca67a8f7c895dfc02b73dbca38250a3b2dae5b8ab8fd36414e`
- **PDF Size**: 9,071 bytes
- **JSON Package Size**: 10,070 bytes
- **Mule Risk Index**: **34.0 / 100** (`MODERATE`)
- **Official Risk Family Breakdown**:
  - `FLOW_STRUCTURE`: 14.0 pts
  - `VELOCITY`: 0.0 pts
  - `AUTOMATION`: 14.0 pts
  - `NETWORK_STRUCTURE`: 0.0 pts
  - `TRANSACTION_BEHAVIOR`: 2.0 pts
  - `ROLE_SUPPORT`: 4.0 pts
  - **Total**: 34.0 pts
- **Root Outflow**: INR 214,372.32
- **Downstream Attribution**: INR 0.00
- **Terminal Accounts**: 3

### Arbitrary Account 2: PYTM10001005
- **Case File ID**: `CASE-PYTM10001005-98D812F2`
- **End-to-End Generation Time**: **223.15 ms**
- **Evidence Snapshot SHA-256**: `dcf160d466793b7a90431d13c4bb0e24d2751e891473cbf1fc0a583ea79b68a1`
- **PDF Size**: 8,649 bytes
- **JSON Package Size**: 7,094 bytes
- **Mule Risk Index**: **26.0 / 100** (`MODERATE`)
- **Official Risk Family Breakdown**:
  - `FLOW_STRUCTURE`: 12.0 pts
  - `VELOCITY`: 0.0 pts
  - `AUTOMATION`: 14.0 pts
  - `NETWORK_STRUCTURE`: 0.0 pts
  - `TRANSACTION_BEHAVIOR`: 0.0 pts
  - `ROLE_SUPPORT`: 0.0 pts
  - **Total**: 26.0 pts
- **Root Outflow**: INR 53,819.33
- **Downstream Attribution**: INR 0.00
- **Terminal Accounts**: 2
