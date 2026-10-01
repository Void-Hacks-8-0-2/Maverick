# Operation Abhedya-Chakra — Production Forensic Engine Audit
**Target Baseline Commit:** `5b24826`  
**Dataset Reference:** `data/VoidHacks8_MuleAccount_2M_Transactions.csv` (2,000,000 records, 273.5 MB, SHA-256: `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101`)  
**Audit Scope:** Backend, Storage / Data Access, API Routes, Graph Services, Test Suite, and Forensic Engine Architecture.

---

## 1. Executive Summary

This audit establishes the definitive engineering baseline of the Abhedya-Chakra backend prior to implementing the core forensic detection, risk scoring, temporal tracing, and legal report generation engines.

### Summary Status
- **Existing Backend Capabilities:** 7 of 18 capabilities implemented (Base v0.1 Data Access & Structural Traversal Tier).
- **Core Forensic Engine Status:** 11 of 18 capabilities MISSING (Mule Detection, 3–15m Velocity, 0–100 MRI, Temporal FIFO Attribution, Court Evidence Packages).
- **Performance Characteristics:** Raw analytical queries are sub-millisecond on indexed lookups (40–80 ms), but account search suffers from severe query degradation (9,965 ms) due to unindexed wildcard ILIKE scans and correlated subqueries across 2M rows.
- **Data Integrity & Non-Duplication:** Verified raw dataset contains 2,252 duplicate `Transaction_ID`s across distinct entities; `graph_service.py` currently exhibits an edge key collision defect when duplicate transaction IDs are encountered.

---

## 2. A. Current Architecture

The current backend is built as a lightweight FastAPI application directly over an in-memory DuckDB analytical engine:

```
[Raw Production CSV: 2,000,000 rows]
         ↓  (Direct vectorized CSV read on cold start ~965 ms)
[DuckDB In-Memory Table: 'transactions']
         ↓  (3 B-tree indexes: Sender_Account, Receiver_Account, Transaction_ID ~7.14 s)
[Ad-hoc SQL Queries & BFS Traversal Service: graph_service.py]
         ↓
[FastAPI REST API Routes: routes.py]
         ↓
[Frontend Client (React/Vite)]
```

### Key Architectural Characteristics
1. **Single-Table Schema (`transactions`):** All operations query a single flat table containing the 11 raw fields (`Transaction_ID`, `Sender_Account`, `Receiver_Account`, `Sender_IFSC`, `Receiver_IFSC`, `Amount`, `Timestamp`, `Payment_Mode`, `Narration`, `IP_Address`, `Device_Type`).
2. **Missing Tiered Storage Structure:**
   - **Lacks Tier 2 (Analytical Materialized Storage):** No dedicated entity dimension (`accounts` dimension table) or transaction pre-aggregations.
   - **Lacks Tier 3 (Derived Features & Risk State):** No materialized table or cache for account metrics (fan-in, fan-out, velocity, layer candidate flags, risk index).
3. **Connection Lifecycle:** Managed through a module-level singleton in `backend/db/connection.py`. Database is initialized as `:memory:` with cold reload when dataset path changes.
4. **Data Mutability:** Strict read-only query pattern across the API. Raw source order is preserved in-memory; 0 synthetic records or fabricated columns exist.

---

## 3. B. Existing Capabilities Audit

### Capability 1: Production Dataset Ingestion & In-Memory Storage
- **Status:** `COMPLETE`
- **Current Implementation:** Vectorized DuckDB table creation using `CREATE TABLE transactions AS SELECT * FROM read_csv('data/VoidHacks8_MuleAccount_2M_Transactions.csv', header=true)`.
- **Relevant Files:** `backend/db/connection.py`, `backend/main.py`
- **Relevant API:** N/A (Internal database access via `get_db()`)
- **Known Limitations:** Operates entirely in volatile RAM (`:memory:`). If server restarts, CSV is re-read and indexes re-built (takes ~8 seconds).

### Capability 2: Health & Production Dataset Metadata Summary
- **Status:** `COMPLETE`
- **Current Implementation:** `GET /api/health` returns service status; `GET /api/dataset/summary` executes dynamic queries for count, distinct accounts, distinct transaction IDs, total amount, and payment mode breakdowns.
- **Relevant Files:** `backend/api/routes.py`
- **Relevant API:** `GET /api/health`, `GET /api/dataset/summary`
- **Known Limitations:** Recalculates payment mode distribution dynamically on every request.

### Capability 3: Account Search
- **Status:** `PARTIAL`
- **Current Implementation:** Substring wildcard match using `ILIKE ?` over both `Sender_Account` and `Receiver_Account`, followed by correlated subqueries in a CTE to compute in/out counts and sums for each matched account.
- **Relevant Files:** `backend/api/routes.py` (lines 132–176)
- **Relevant API:** `GET /api/accounts/search?q={query}&limit={limit}`
- **Known Limitations:** **Severe Performance Bottleneck (9,965 ms).** `ILIKE` requires a full sequential scan of 2,000,000 strings twice, and correlated subqueries run unindexed counts. Requires a materialized `accounts` lookup table.

### Capability 4: Account Profile & Summary Statistics
- **Status:** `COMPLETE`
- **Current Implementation:** `GET /api/accounts/{account_id}` computes aggregate inbound/outbound counts, distinct senders/receivers, inflow/outflow, observed net movement, associated IFSCs, and associated IPs.
- **Relevant Files:** `backend/api/routes.py` (lines 178–248)
- **Relevant API:** `GET /api/accounts/{account_id}`
- **Known Limitations:** Computes metrics on-demand via 5 separate SQL queries. While fast (~80 ms) due to indexed lookups, it does not persist derived forensic features or risk profiles.

### Capability 5: Account Transaction Ledger (Pagination & Filtering)
- **Status:** `COMPLETE`
- **Current Implementation:** `GET /api/accounts/{account_id}/transactions` supports direction filtering (`in`, `out`, `all`) with `LIMIT` and `OFFSET` pagination, sorted by `Amount DESC`. All 11 columns (including exact `Timestamp` and `Device_Type`) are properly serialized.
- **Relevant Files:** `backend/api/routes.py` (lines 250–317)
- **Relevant API:** `GET /api/accounts/{account_id}/transactions?direction={in|out|all}&limit={limit}&offset={offset}`
- **Known Limitations:** Only sorts by `Amount DESC`. Does not yet provide chronological ordering (`ORDER BY Timestamp ASC`) or time-window range filtering (`start_date`, `end_date`).

### Capability 6: 1-Hop / Multi-Hop Ego Network Graph
- **Status:** `PARTIAL`
- **Current Implementation:** Breadth-first frontier expansion in Python (`get_account_graph`), querying transactions where sender or receiver is in the active frontier, up to `max_hops` (1–3) and `max_nodes`.
- **Relevant Files:** `backend/services/graph_service.py` (lines 10–86), `backend/api/routes.py` (lines 320–329)
- **Relevant API:** `GET /api/accounts/{account_id}/graph?max_hops=1&max_nodes=500`
- **Known Limitations:**
  1. **Edge Collision Defect:** Uses `tx_id` as the dictionary key (`edges_map[tx_id] = ...`). When duplicate `Transaction_ID`s exist in the dataset, edges between distinct accounts are inadvertently overwritten or dropped.
  2. Non-temporal: Ignores transaction sequencing; treats all historic edges simultaneously.

### Capability 7: 4-Hop Structural Reach Traversal
- **Status:** `PARTIAL`
- **Current Implementation:** Multi-level forward traversal (`get_account_trace`) tracking active path lists up to 4 hops deep, preventing immediate cyclic revisit within a path.
- **Relevant Files:** `backend/services/graph_service.py` (lines 88–206), `backend/api/routes.py` (lines 331–339)
- **Relevant API:** `GET /api/accounts/{account_id}/trace?max_nodes=1000`
- **Known Limitations:**
  1. **Structural Only:** Traverses topological graph links ordered by `Amount DESC`. It does NOT perform temporal FIFO flow tracking (does not verify that inflow preceded outflow or track partial balance dissipation).
  2. Edge collision defect also present in edge mapping.

---

## 4. C. Performance Baseline Measurements

Measured on production dataset (`VoidHacks8_MuleAccount_2M_Transactions.csv`, 2,000,000 rows) using Python's high-resolution timer (`time.perf_counter()`):

| Operation | Target / Scope | Measured Time (ms) | Measured Time (s) | Evaluation |
|:---|:---|:---:|:---:|:---|
| **Dataset 2M CSV Load** | Vectorized DuckDB read into memory | **964.69 ms** | 0.965 s | Excellent (sub-second) |
| **B-Tree Indexing** | 3 indexes (`Sender`, `Receiver`, `TxID`) | **7,140.90 ms** | 7.141 s | Acceptable for startup (~7s) |
| **Backend Lifespan Startup** | Pre-warmed DuckDB table check | **199.21 ms** | 0.199 s | Instantaneous |
| **Account Search** | `ILIKE '%SBIN10012624%'` + subqueries | **9,965.79 ms** | **9.966 s** | **CRITICAL BOTTLENECK** |
| **Account Detail Query** | Full account statistics & aggregations | **79.54 ms** | 0.080 s | Excellent (sub-100ms) |
| **Transaction Query** | Paginated ledger query (50 items) | **55.78 ms** | 0.056 s | Excellent (sub-60ms) |
| **Graph 1-Hop Query** | Ego-network extraction (50 nodes) | **40.31 ms** | 0.040 s | Excellent (sub-50ms) |
| **Graph 2-Hop Query** | 2-hop neighborhood (100 nodes) | **41.23 ms** | 0.041 s | Excellent (sub-50ms) |
| **4-Hop Structural Trace** | Forward reach traversal (500 nodes) | **239.39 ms** | 0.239 s | Fast structural traversal |

---

## 5. D. Current Test Coverage Analysis

### Active Test Files
1. [`tests/test_api.py`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_api.py) (8 tests)
2. [`tests/test_production_dataset.py`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_production_dataset.py) (8 tests)

### Test Verification Summary: 16 Passed / 16 Total (100%)

#### What Is Tested:
- Dataset existence and exact SHA-256 (`2c9f81fd34f7...`).
- Row count (`2,000,000`) and exact 11 columns in DuckDB schema.
- Zero null values for `Timestamp` and `Device_Type`.
- Strict absence of old recovered files from `data/` and verification of anti-fallback logic.
- HTTP status codes (200, 404) for all API endpoints.
- Basic JSON response structure validation for health, summary, search, account detail, transactions, graph, and trace.
- Non-null string values for transaction items.

#### What Is NOT Tested:
- **Duplicate Transaction_ID collision:** Tests do not verify whether duplicate transaction IDs produce colliding edge keys in the graph.
- **Temporal FIFO attribution:** No tests for causality, timing sequences, or balance tracking.
- **Concurrent requests:** No load/concurrency tests on DuckDB.
- **Boundary / parameter fuzzing:** Negative limits, offsets, or invalid characters.
- **Forensic detection logic:** No tests exist for mule classification, fan-in/fan-out, or velocity because the detection engine is not yet built.

---

## 6. E. Missing Forensic Capabilities Gap Analysis

To transform Base v0.1 into the full-scale Financial Cyber-Forensics & Money-Mule Network Investigation Platform, the following modular engines must be engineered:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MISSING FORENSIC ENGINE CAPABILITIES                 │
├─────────────────────┬────────────────────┬─────────────────────────────┤
│ 1. DETECTION        │ 2. RISK SCORING    │ 3. TRACING & EVIDENCE       │
│ • Fan-In / Fan-Out  │ • 0–100 Mule Risk  │ • Temporal FIFO Attribution │
│ • L1 Collector      │   Index (MRI)      │ • 3–15m Rapid Pass-Through  │
│ • L2 Distributor    │ • Explainable      │ • Dwell Time Analysis       │
│ • L3 Terminal       │   Score Breakdown  │ • Partial Consumption       │
│ • Device Anomaly    │ • Deterministic    │ • Sec 91 Freezing Notices   │
│ • IP Clusters       │   Heuristics       │ • Police Case Diary Dossier │
└─────────────────────┴────────────────────┴─────────────────────────────┘
```

### 1. Detection Engine
- **Fan-in / Fan-out Calculation:** Ratio of unique sender sources to receiver destinations.
- **Layer 1 Collector Identification:** Accounts exhibiting high fan-in from distributed sources, small average transaction amounts, and rapid aggregation.
- **Layer 2 Distributor Identification:** Accounts exhibiting high volume, balanced fan-in and fan-out, high velocity pass-through, and fragmentation into downstream accounts.
- **Layer 3 Terminal Identification:** Accounts with high fan-out into exit payment modes or merchants, ATM withdrawals, or dissipation to external networks.
- **Automation & Tooling Indicators:** Exploitation of `Web_Emulator` (1,327 txs) and `Linux_Script` (1,327 txs) device types.
- **IP Network Geolocation / Subnet Clustering:** Detecting mule clusters operating from identical IP subnets.

### 2. Risk Engine
- **0–100 Mule Risk Index (MRI):** Deterministic, explainable scoring model combining:
  1. Structural Layering Factor (fan-in/fan-out topology)
  2. Velocity / Dwell Time Factor (3–15 min pass-through)
  3. Device & Automation Factor (script/emulator usage)
  4. Volume Anomaly Factor (rapid surges vs baseline)
- **Explainability:** Detailed breakdown providing evidentiary justification for each contributing factor.

### 3. Tracing Engine (Temporal FIFO Attribution)
- **Temporal Causality:** Money cannot flow out before it flows in ($T_{\text{in}} < T_{\text{out}}$).
- **FIFO Rupee Tracking:** Attributing specific victim inflow funds to subsequent outbound transactions in chronological order.
- **Conservation of Funds:** Explicitly accounting for retained balances, partial consumption, and unallocated residues.
- **Strict 3–15 Minute Pass-Through Window:** Explicitly testing $3 \text{ min} \le \Delta t \le 15 \text{ min}$.

### 4. Legal & Evidentiary Reporting
- **Section 91 CrPC / BNSS Freezing Notice Generator:** Court-ready legal documents with exact account identifiers, IFSC, and proven transactional evidence.
- **Chronological Case Diary Dossier:** Complete investigative audit trail linking observed transactions, derived features, and timeline visualizers.

---

## 7. F. Forensic Rules Adherence Audit

| Rule | Requirement | Current Status | Audit Finding |
|:---|:---|:---:|:---|
| **Rule 1** | Never call an account a criminal; use candidate terminology | **PASS** | Existing endpoints use neutral forensic terms (`account`, `observed_inflow`, `observed_outflow`). |
| **Rule 2** | Do not claim bank balance; use `Observed Net Flow Delta` | **PASS** | `dataset_observed_net_movement` is strictly computed as `inflow - outflow`. |
| **Rule 3** | Risk score must not be treated as proof of crime | **PASS** | No risk scores currently generated; rule must be enforced in Phase 2. |
| **Rule 4** | AI must never be the source of factual forensic values | **PASS** | Zero generative AI models integrated into data retrieval path. |
| **Rule 5** | Never fabricate values (accounts, amounts, timestamps) | **PASS** | Direct raw CSV ingestion; 0 nulls, 0 fabricated records. |
| **Rule 6** | `Transaction_ID` is not globally unique; do not use as primary key | **DEFECT DETECTED** | `graph_service.py` uses `tx_id` as the unique dictionary key for edges (`edges_map[tx_id]`), causing edge overwrite collisions for the 2,252 duplicate transaction IDs. |
| **Rule 7** | Synthetic data must never replace production dataset | **PASS** | Production dataset is 100% active; test fixtures isolated to `tests/fixtures/`. |
| **Rule 8** | Pass-through rule strictly $3 \text{ min} \le \Delta t \le 15 \text{ min}$ | **NOT YET IMPLEMENTED** | Must be strictly implemented in velocity engine. |
| **Rule 9** | Distinguish OBSERVED, DERIVED, and AI-GENERATED | **PARTIAL** | Derived net movement is labeled, but formal schema classification is not yet standardized across responses. |

---

## 8. G. Recommendations for Step 2 Implementation

1. **Fix Edge Collision in Graph Service:** Replace single `tx_id` edge dictionary key with a composite surrogate key (e.g., `f"{sender}_{receiver}_{tx_id}_{timestamp}"`).
2. **Materialize Analytical Tier (Accounts Dimension Table):** Pre-aggregate the 24,873 unique accounts with their total in/out transactions and flows during startup to eliminate the 9.9-second `search_accounts` bottleneck.
3. **Build the Feature & Detection Engine (`engine/`):**
   - Create modular services for Fan-In/Fan-Out, Layer Identification, Device Anomalies, and Velocity.
   - Implement deterministic 0–100 Mule Risk Index.
4. **Implement Temporal FIFO Attribution Engine:**
   - Chronological fund tracing strictly observing $T_{\text{in}} < T_{\text{out}}$ and the $3 \le \Delta t \le 15$ minute rule.

---

## 9. H. Step 2 Completion & Resolution of Baseline Deficiencies

The critical defects and performance bottlenecks identified in this Step 1 audit have been resolved in **Backend Step 2**:

1. **Resolution of Rule 6 & Graph Edge Collision Defect:**
   - In `backend/services/graph_service.py`, single `tx_id` mapping has been replaced with deterministic composite surrogate key `make_edge_id(sender, receiver, tx_id, ts, row_id)` format `f"{sender}_{receiver}_{tx_id}_{ts_str}_{row_id}"`.
   - All duplicate `Transaction_ID` records (2,252 duplicate records) are now 100% preserved in graph extraction and multi-hop traversal without overwrite collisions.
   - Verified via regression test `tests/test_graph_integrity.py`.

2. **Resolution of Account Search Bottleneck (9,965 ms -> 17.99 ms):**
   - Implemented Tier 2 materialized analytical dimension table `accounts_dimension` in DuckDB during startup.
   - Represents the complete union of sender and receiver accounts (24,873 entities) with pre-aggregated `total_inflow`, `total_outflow`, `net_flow_delta`, transaction counts, counterparties, timestamps, IFSCs, IPs, and devices.
   - Querying `accounts_dimension` directly from `GET /api/accounts/search` achieved a **~147x to 550x speedup** (min 17.99 ms, avg 67.50 ms).
   - Verified via 7 correctness tests in `tests/test_accounts_dimension.py`.

3. **Establishment of Tier 3 Forensic Feature Store Foundation:**
   - Created `backend/features/models.py` (`AccountFeatures` Pydantic schema) and `backend/features/store.py` (`account_features` table in DuckDB).
   - Enforced strict provenance (`DERIVED`) and uncomputed fields remain `NULL` (no fake zeros).

