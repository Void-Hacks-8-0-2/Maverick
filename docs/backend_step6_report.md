# Operation "Abhedya-Chakra" — Step 6 Forensic Engineering Report
## Blind Victim Investigation Engine & Investigation Workspace

**Author:** Antigravity Autonomous Cyber-Forensics Agent  
**Date:** October 2026  
**System:** Operation "Abhedya-Chakra" — Financial Cyber-Forensics & Money Mule Network Investigation Platform  
**Target Environment:** Offline / Local Air-Gapped Analytics (2,000,000 Financial Transactions, 15-day window)  
**Dataset Integrity:** SHA-256 `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101` (Verified Unmodified)

---

## 1. Executive Summary & Architecture

Step 6 implements the **Blind Victim Investigation Engine** and dedicated **Investigation Workspace** (`/victim`), delivering the core 40% judging workflow for Operation "Abhedya-Chakra". 

The blind victim investigation allows an investigator or competition evaluator to supply **any arbitrary victim account ID** present in the 2M-transaction production dataset and receive a complete, evidence-grounded, multi-hop forensic dossier within milliseconds.

### Core Architectural Principle
The Step 6 investigation engine operates strictly as an **orchestration layer** over locked deterministic forensic modules:
```
                               Victim Account Input
                                        │
                                        ▼
                         [ Account Existence & Validation ]
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
         [ Analytical DB ]       [ Step 3 Features ]    [ Step 5C FIFO Engine ]
       accounts_dimension,         fan-in/fan-out,        Temporal attribution
       transactions_2m table       ratios, devices        & 4-hop propagation
                 │                      │                      │
                 │              ┌───────┴───────┐              │
                 │              ▼               ▼              │
                 │       [ Step 4 Roles ] [ Step 5B Risk ]     │
                 │       L1/L2/L3 labels,   0-100 index,       │
                 │       reason codes     evidence breakdown   │
                 │                              │              │
                 │                      [ Step 5A Velocity ]   │
                 │                      3-15 min pass-through  │
                 │                      events & metrics       │
                 │                              │              │
                 └──────────────────────┬───────┴──────────────┘
                                        ▼
                         [ Forensic Synthesizer & Models ]
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
       [ Structured REST API ]                     [ Frontend Workspace ]
    GET /api/investigations/victim/{id}               /victim Investigation
```

### Forensic Safety & Invariant Guarantees
1. **Offline & Air-Gapped:** Zero external API or cloud calls; zero LLM hallucination of evidence.
2. **Integer-Paise Monetary Conservation:** Attributed amounts strictly respect fund availability; money is never created or inflated between hops.
3. **No Hardcoded Accounts:** The system functions universally for arbitrary account IDs across all 24,873 unique entities in the 2M dataset.
4. **Distinction of Edges:** `ROOT_SEED` edges (victim direct outflows) are structurally distinguished from `FIFO_ATTRIBUTION` edges (downstream mule hops).
5. **Path-Aware Cycle Detection:** Loops are tracked and flagged without dropping parallel/converging branches.
6. **Explicit Truncation Reporting:** Traversal caps set `truncated = true` and expose exact warning codes.
7. **Neutral Forensic Terminology:** Nodes are designated as "Investigative Candidate", "High-Risk Indicator", "Terminal Node", etc.

---

## 2. API Endpoint Specification

### Endpoint Route
```http
GET /api/investigations/victim/{account_id}
```

### Query Parameters
| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `max_hops` | `int` | `4` | Traversal hop depth (clamped between 1 and 4). |
| `horizon_seconds` | `int` (optional) | `None` | Optional per-hop FIFO attribution horizon in seconds (default covers full dataset window). |
| `max_branches_per_hop` | `int` | `50` | Maximum branch fanout per hop before truncation warning is raised. |

### HTTP Status Codes
- `200 OK`: Valid account located and complete multi-hop investigation dossier returned.
- `404 Not Found`: Account does not exist in the 2,000,000 transaction dataset.
- `422 Unprocessable Entity`: Invalid query parameters or malformed account ID.
- `500 Internal Server Error`: Unhandled server exception with structured forensic logging.

---

## 3. Strongly Typed Response Model

The response model is implemented in `backend/investigations/models.py` (`VictimInvestigationResponse`):

```python
class VictimInvestigationResponse(BaseModel):
    investigation_id: str                   # INV-<account>-<hash>
    account_number: str                     # Subject account identifier
    status: str                             # "COMPLETED", "TRUNCATED", "CYCLE_DETECTED", "NO_ATTRIBUTION"
    generated_at: str                       # ISO-8601 UTC timestamp
    data_provenance: DataProvenance         # SHA-256 seal, row counts, policy versions
    account_summary: VictimAccountSummary   # Net flow delta, counterparty counts, IPs, devices
    victim_transactions: List[VictimTransactionItem] # Source transactions with IFSC, mode, IP, device
    risk: MuleRiskScore                     # Step 5B 0-100 score, band, family breakdown, reasons
    roles: VictimRolesSummary               # Step 4 L1/L2/L3 classification & detailed signals
    velocity: VictimVelocitySummary         # Step 5A 3-15 min pass-through ratio & qualifying events
    trace: AttributionTraceResponse         # Step 5C 4-hop nodes, edges, hop summaries, cycle/truncation
    terminals: List[TerminalAccountEvidence]# Terminal/cash-out recipients with hop, risk, role
    warnings: List[str]                     # Warnings (TRUNCATION, CYCLES, LOW_OUTFLOW, etc.)
    evidence_summary: InvestigationEvidenceSummary # Deterministic narrative & key findings
    disclaimer: str                         # Mandatory forensic disclaimer
```

---

## 4. Frontend Workflow (`/victim`)

The frontend workspace is implemented in `frontend/src/pages/VictimInvestigation.tsx`, registered at `/victim` and `/victim/:id`, and integrated directly into the top navigation bar.

### User Flow & Capabilities
1. **Investigation Input:**
   - Prominent search input with auto-capitalization, validation, and submission on `Enter`.
   - Quick forensic sample chips for rapid evaluator testing.
2. **Deterministic Multi-Stage Loading:**
   - Structured milestone indicators (Account Evidence → Transactions Correlated → 4-Hop FIFO Attributed → Mule Role & Risk Diagnosed) without fake progress bars.
3. **Overview KPIs:**
   - Status badge, Observed Inflow, Observed Outflow, Observed Net Flow Delta (never mislabeled as bank balance), Risk Index pill (color-coded LOW/MODERATE/HIGH/VERY_HIGH), and Primary Role badge.
4. **Warnings & Alerts Banner:**
   - Prominently surfaces truncation warnings (`ROOT_OUTGOING_BRANCH_LIMIT`, `MAX_TRACE_EDGES`) and cycle detection warnings.
5. **Deterministic Narrative Summary:**
   - Human-readable forensic summary automatically synthesized from analytical findings.
6. **Five Specialized Forensic Tabs:**
   - **Network Trace Graph:** Interactive WebGL/Canvas visualization powered by Sigma.js, Graphology, and `@react-sigma/core`. Color-coded nodes (Victim, Intermediary Mule, Terminal Cash-Out) with directed attribution edges labeled by attributed amount and hop.
   - **Attribution Edges Table:** Complete chronological table of all fund movements, distinguishing `SEED` vs `FIFO` edges, source/destination transactions, attributed amounts, and transfer delays.
   - **Terminal Accounts Panel:** Grid of destination accounts where funds terminated, including hop distance, total received amount, risk score, and role signals.
   - **Transaction Evidence:** Searchable, horizontally scrollable raw transaction table with Transaction ID, Row ID, Timestamp, Counterparty, Amount, Payment Mode, IFSCs, IPs, Devices, and Narrations.
   - **Risk & Velocity Diagnostics:** Deep-dive panel displaying Step 5B risk family contributions (Velocity, Pass-Through, Structural, Device/Network, Value Distribution), risk reasons, and Step 5A 3–15 minute pass-through qualifying events.
7. **Evidence Integrity Panel:**
   - Persistent footer seal showing dataset name (`VoidHacks8_MuleAccount_2M_Transactions.csv`), 2,000,000 rows, verified SHA-256 seal, and policy versions.

---

## 5. Integration with Step 5A, 5B, 5C & Earlier Layers

The orchestration in `backend/investigations/orchestrator.py` cleanly integrates existing services:
- **Step 2 (Analytical Tier):** Directly queries `accounts_dimension` for first/last seen timestamps, unique counterparties, IP/device counts, and `transactions` table for root transactions.
- **Step 3 (Behavioral Features):** Calls `get_account_features(conn, account_id)` for fan-in, fan-out, turnover ratios, and device automation counts.
- **Step 4 (Role Classification):** Extracts `layer1_candidate`, `layer2_candidate`, `layer3_candidate` directly from materialized features, preserving original classification reasons and automation signals.
- **Step 5A (Velocity Engine):** Calls `get_velocity_events(conn, account_id)` and extracts `pass_through_candidate`, `pass_through_ratio`, `pass_through_event_count`, and median transfer delay.
- **Step 5B (Risk Scoring):** Calls `get_account_risk(account_id, conn)` returning the explainable 0–100 Mule Risk Index, risk band, family breakdown, and evidence reasons.
- **Step 5C (Temporal FIFO Attribution):** Invokes `trace_fifo_attribution_4hop(conn, account_id, max_hops=4, max_branches_per_hop=50)` ensuring exact integer-paise conservation, cycle detection, and explicit truncation propagation.
- **Terminal Node Enrichment:** Automatically analyzes all sink nodes in the trace graph, retrieving their risk, role, and velocity profiles to provide actionable downstream leads.

---

## 6. Provenance Model

Every investigation response explicitly maintains data provenance across all four tiers:
```
[ RAW TIER ]        Production CSV (2M rows, SHA-256 verified)
       │
       ▼
[ ANALYTICAL TIER ] DuckDB analytical tables, stable rowids, indexed accounts
       │
       ▼
[ DERIVED TIER ]    FIFO v1 attribution, Mule Risk v1, Velocity v1, Step 4 roles
       │
       ▼
[ UI / REPORT ]     VictimInvestigationResponse with full traceability & disclaimer
```
The system uses the factual statement: `"Dataset integrity verified by SHA-256."` and maintains strict disclaimers that results serve investigative prioritization, not judicial determinations.

---

## 7. Truncation and Cycle Handling

- **Branch Truncation:** When outgoing branches from any node exceed `max_branches_per_hop` (default 50), or total edges exceed 500, the Step 5C engine sets `truncated = true` with reason codes (e.g. `ACCOUNT_OUTGOING_BRANCH_LIMIT:<acc>`). The Step 6 orchestrator propagates this directly to `trace.truncated`, appends an explicit warning to `warnings`, and updates `status = "TRUNCATED"`.
- **Cycle Handling:** Path-aware cycle detection tracks the active branch ancestry (`visited_in_path`). When funds loop back to an account already in the current branch, traversal terminates to prevent infinite loops, and the cycle path is recorded in `cycles_detected`. The orchestrator appends this to `warnings` and surfaces it visually in the frontend.

---

## 8. Performance Verification & Benchmarks

Step 6 performance was benchmarked directly against the live HTTP server (`http://127.0.0.1:8000`) evaluating complete multi-hop investigations:

| Account ID | Classification / Role | Risk Score | Root Seeds | FIFO Edges | Max Hop | Nodes / Edges | HTTP Latency | Target |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `KKBK10000402` | L3 Terminal Candidate | 70.0 (HIGH) | 11 | 16 | 2 | 27 / 27 | **610.35 ms** | ≤ 2.0 s |
| `PYTM10001005` | Originating / Standard | 26.0 (MODERATE) | 2 | 0 | 1 | 3 / 2 | **219.68 ms** | ≤ 2.0 s |
| `AIRP10000595` | L3 Terminal Candidate | 34.0 (MODERATE) | 3 | 0 | 1 | 4 / 3 | **278.09 ms** | ≤ 2.0 s |

All benchmarks executed well under the 2-second interactive target.

---

## 9. Test Suite Results

### Full Backend Pytest Suite
```
tests/test_victim_investigation.py .................... [ 16%]
tests/test_attribution.py ............................. [ 41%]
tests/test_api.py ..................................... [ 72%]
tests/test_risk_scoring.py ............................ [ 88%]
tests/test_velocity.py ................................ [100%]

============================== 120 passed in 90.49s ==============================
```

### Dedicated Step 6 Test Coverage (`tests/test_victim_investigation.py` - 20 Tests)
1. `test_01_valid_arbitrary_account_investigation`
2. `test_02_account_not_found_returns_404`
3. `test_03_account_with_no_downstream_attribution`
4. `test_04_victim_transaction_retrieval_and_fields`
5. `test_05_risk_integration`
6. `test_06_role_integration`
7. `test_07_velocity_integration`
8. `test_08_fifo_trace_integration`
9. `test_09_four_hop_limit_enforced`
10. `test_10_propagation_amount_correctness_and_conservation`
11. `test_11_root_seed_distinction`
12. `test_12_fifo_edge_distinction`
13. `test_13_truncation_propagation_and_warning`
14. `test_14_cycle_propagation_and_warning`
15. `test_15_provenance_presence`
16. `test_16_no_fabricated_evidence`
17. `test_17_deterministic_investigation_structure`
18. `test_18_malformed_account_id_handled`
19. `test_19_backend_error_handling`
20. `test_20_not_dependent_on_hardcoded_accounts`

### Frontend Production Build
```
vite v6.4.1 building for production...
✓ 1836 modules transformed.
dist/index.html                   0.82 kB │ gzip:   0.44 kB
dist/assets/index-D7h5W5-v.css   40.23 kB │ gzip:   7.38 kB
dist/assets/index-15j55A6Z.js   894.46 kB │ gzip: 254.91 kB
✓ built in 1.66s
```

---

## 10. Live KKBK10000402 Verification

Detailed verification of subject account `KKBK10000402` against the live endpoint:
- **Investigation ID:** `INV-KKBK10000402-322DEE97`
- **Observed Inflow:** INR 991,142.92 across 3 incoming transactions.
- **Observed Outflow:** INR 971,320.06 across 11 outgoing transactions.
- **Observed Net Flow Delta:** INR +19,822.86.
- **Root Seed Edges:** Exactly 11 root seed outgoing transactions (`edge_type="ROOT_SEED"`).
- **Downstream FIFO Edges:** 16 downstream FIFO attribution links (`edge_type="FIFO_ATTRIBUTION"`).
- **Max Hop Reached:** 2 hops.
- **Graph Nodes & Edges:** 27 nodes, 27 directed edges.
- **Terminal Nodes Identified:** 15 recipient accounts.
- **Risk Score:** 70.0 / 100 (`HIGH`).
- **Role Classification:** `L3 Terminal Candidate` (triggered by high outbound disbursement and automation signals).
- **Velocity Metrics:** `pass_through_candidate = True`, ratio `0.98` (98% of volume transacted within 3–15 minutes).
- **Conservation Check:** Integer-paise amounts strictly conserved; no fund inflation between hops.
- **Warnings / Truncation / Cycles:** None.

---

## 11. Known Limitations & Future Refinements

1. **Pre-Materialized Ingestion Dependency:** The investigation orchestrator assumes the analytical DuckDB database and materialized behavioral features exist. In cold air-gapped deployments, Step 2 ingestion must precede investigations.
2. **Horizon Policy Customization:** While query parameters support `horizon_seconds`, the default trace evaluates the full 15-day dataset window to maximize attribution recall.
3. **Graph Layout Density:** Accounts with extremely large fanouts (e.g. >100 downstream connections) rely on branch truncation (`max_branches_per_hop=50`) to ensure graph rendering performance remains smooth.

---

## 12. Dataset Integrity Confirmation

```
Target File: data/VoidHacks8_MuleAccount_2M_Transactions.csv
Total Transactions: 2,000,000
Total Columns: 11
SHA-256 Checksum: 2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101
Status: VERIFIED UNMODIFIED
```
