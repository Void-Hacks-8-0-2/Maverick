# Operation Abhedya-Chakra — Backend Step 2 Report
**Milestone:** Materialized Analytical Tier + Graph Integrity  
**Baseline Commit:** `5b24826`  
**Dataset Reference:** `data/VoidHacks8_MuleAccount_2M_Transactions.csv` (2,000,000 records, SHA-256: `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101`)

---

## Step 2 completed

### 1. Graph collision fix

#### Implementation
- In [backend/services/graph_service.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/services/graph_service.py), the legacy single `tx_id` mapping (`edges_map[tx_id] = ...`) was replaced with a collision-safe deterministic composite identifier:
  ```python
  def make_edge_id(sender: str, receiver: str, tx_id: str, ts: Any, row_id: Any) -> str:
      ts_str = str(ts).replace(" ", "T") if ts is not None else "NA"
      return f"{sender}_{receiver}_{tx_id}_{ts_str}_{row_id}"
  ```
- **Surrogate Edge Identity:** `f"{sender}_{receiver}_{tx_id}_{ts_str}_{row_id}"` guarantees 100% uniqueness even in theoretical cases where sender, receiver, transaction ID, and timestamp are completely identical.
- **Authoritative Data Preservation:** The authoritative `Transaction_ID` is preserved unmodified in `edge["transaction_id"] = tx_id`, while `edge["id"]` provides the unique graph element identifier for Vis.js rendering and multi-hop path tracking.
- **Zero Deduplication:** No source transaction records are dropped or silently merged.

#### Duplicate-ID test result
- **Controlled Dataset Test:** Tested with duplicate `TX001` records across distinct accounts, timestamps, and an identical duplicate record.
- **Results:**
  - 3 source transactions entered -> exactly 3 graph edges generated (`len(edges) == 3`).
  - No edge overwritten (pre-fix code produced `len(edges) == 1`, dropping 2 transactions).
  - Traversal preserved all outbound paths and correctly associated transaction amounts (`₹1000.0`, `₹800.0`, `₹200.0`) and payment modes (`UPI`, `IMPS`, `NEFT`).
  - Regression test passing: `tests/test_graph_integrity.py::test_duplicate_transaction_id_preservation_in_graph PASSED`.

---

### 2. Accounts dimension (`accounts_dimension`)

#### Schema
Materialized in DuckDB as Tier 2 analytical storage representing the complete union of sender and receiver entities:
```sql
CREATE TABLE accounts_dimension (
    account_number VARCHAR PRIMARY KEY,
    total_inflow DOUBLE,
    total_outflow DOUBLE,
    net_flow_delta DOUBLE,
    incoming_txn_count BIGINT,
    outgoing_txn_count BIGINT,
    transaction_count BIGINT,
    unique_senders BIGINT,
    unique_receivers BIGINT,
    counterparty_count BIGINT,
    first_seen_timestamp TIMESTAMP,
    last_seen_timestamp TIMESTAMP,
    sender_ifsc_count BIGINT,
    receiver_ifsc_count BIGINT,
    unique_ip_count BIGINT,
    unique_device_count BIGINT,
    unique_payment_mode_count BIGINT,
    provenance VARCHAR DEFAULT 'DERIVED'
);
```
Indexes created:
- `idx_dim_acc_number` on `account_number` (UNIQUE)
- `idx_dim_tx_count` on `transaction_count`
- `idx_dim_inflow` on `total_inflow`
- `idx_dim_outflow` on `total_outflow`

#### Row count
- **24,873 rows** (Matches exact count of unique accounts in `Sender_Account ∪ Receiver_Account`).
  - Senders count: 24,488
  - Receivers count: 24,573
  - Sender-only accounts: 300
  - Receiver-only accounts: 385
  - Two-way active accounts: 24,188

#### Correctness checks
- **Test 1 (Completeness):** Exact match between distinct account union and dimension row count (24,873 == 24,873) -> `PASS`.
- **Test 2 & 3 (Direct Aggregation Reconciliation):** Tested known high-volume accounts (e.g. `SBIN10012624` with 208 transactions). Dimension metrics `total_inflow` (₹119,331.69), `total_outflow` (₹183,640.92), `net_flow_delta` (-₹64,309.23), and counts exactly match raw transaction sums -> `PASS`.
- **Test 4 (Receiver-Only Accounts):** 385 receiver-only accounts verified to have `outgoing_txn_count == 0`, `total_outflow == 0.0`, and 0 raw outbound rows -> `PASS`.
- **Test 5 (Sender-Only Accounts):** 300 sender-only accounts verified to have `incoming_txn_count == 0`, `total_inflow == 0.0`, and 0 raw inbound rows -> `PASS`.
- **Test 6 (Search API Schema & Contract):** Returns expected fields with `dataset_observed_net_movement` strictly matching `observed_inflow - observed_outflow` -> `PASS`.
- **Forensic Rule 2 Adherence:** Net flow is named `net_flow_delta` / `dataset_observed_net_movement` (Observed Net Flow Delta) and NEVER called `current_balance`.

#### Startup / materialization time
- Vectorized aggregation across 2M rows + 4 B-Tree indexes: **~3.73 s**
- Cold database initialization (Raw CSV Ingest + 3 Raw Indexes + Accounts Dimension + 4 Dimension Indexes + Feature Store Schema): **15.80 s**

---

### 3. Search performance

- **Before (Step 1 Baseline):**  
  `~9,965.79 ms` (Scanned 2,000,000 rows with 4 correlated subqueries on unindexed ILIKE)
- **After (Step 2 Materialized Dimension):**  
  `min = 17.99 ms` | `avg = 67.50 ms`  
  **Speedup:** **~147x to 550x improvement**
- **Generic Top-20 Search:**  
  `16.05 ms`

---

### 4. Other benchmarks (measured on 2M production records with `time.perf_counter()`)

| Operation | Step 1 Baseline | Step 2 Measured | Status |
|:---|:---:|:---:|:---:|
| **Cold Startup** (Raw Ingest + Dim Materialization + Indexes) | 8.30 s | **15.80 s** | Complete analytical tier initialized |
| **Account Search** (`/api/accounts/search?q=SBIN10012624`) | 9,965.79 ms | **17.99 ms** | **490x faster** |
| **Account Lookup** (`/api/accounts/SBIN10012624`) | 79.54 ms | **72.62 ms** | Pre-aggregated lookups |
| **Transaction Query** (50 items) | 55.78 ms | **66.11 ms** | Stable sub-100ms |
| **Graph 1-Hop Query** (50 nodes) | 40.31 ms | **50.33 ms** | Collision-free edge tracking |
| **Graph 2-Hop Query** (100 nodes) | 41.23 ms | **50.51 ms** | Collision-free edge tracking |
| **4-Hop Structural Traversal** (500 nodes) | 239.39 ms | **215.28 ms** | Cycle prevention intact |

---

### 5. Tests
**25 / 25 passed** (16 original + 9 new regression tests)
- `tests/test_api.py` (8/8 PASS)
- `tests/test_production_dataset.py` (8/8 PASS)
- `tests/test_graph_integrity.py` (2/2 PASS)
- `tests/test_accounts_dimension.py` (7/7 PASS)

---

### 6. Files changed

1. [backend/services/graph_service.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/services/graph_service.py):
   - Implemented `make_edge_id` composite key generator.
   - Updated `get_account_graph` and `get_account_trace` to select `rowid` and key edges by composite surrogate ID.
2. [backend/db/connection.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/db/connection.py):
   - Added `init_analytical_tier(con)` to materialize `accounts_dimension` and create indexes.
   - Integrated initialization of Tier 3 `account_features` schema.
3. [backend/api/routes.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/api/routes.py):
   - Refactored `search_accounts` to query `accounts_dimension`.
   - Refactored `get_account_detail` to use pre-aggregated metrics from `accounts_dimension`.
4. [backend/features/models.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/models.py):
   - Defined `AccountFeatures` Pydantic model with strict typed contracts and NULL defaults for uncomputed features.
5. [backend/features/store.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/store.py):
   - Defined `init_feature_store_schema` creating `account_features` table in DuckDB.
6. [backend/features/__init__.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/__init__.py):
   - Package initialization.
7. [tests/test_graph_integrity.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_graph_integrity.py):
   - New unit and integration tests for duplicate transaction ID edge preservation.
8. [tests/test_accounts_dimension.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_accounts_dimension.py):
   - New correctness and performance regression tests for `accounts_dimension`.
9. [pytest.ini](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/pytest.ini):
   - Configured `testpaths = tests` and `pythonpath = .`.
10. [docs/backend_audit.md](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/docs/backend_audit.md):
   - Appended Step 2 completion section.

---

### 7. Known limitations
1. **Volatile In-Memory Lifecycle:** Because DuckDB runs with `:memory:`, restarting the process re-materializes the `accounts_dimension` (taking ~3.7s during startup). An optional persistent file database (e.g. `data/abhedya.duckdb`) could eliminate startup materialization if required in future phases.
2. **Features Pending Computation:** The Tier 3 `account_features` table schema is instantiated and bound to typed contracts, but individual detection passes (Mule Risk Index, Fan-In/Fan-Out role classification, and 3-15 min velocity) are intentionally left uncomputed until Step 3.
3. **Graph Forward Tracing is Structural (Not Yet Temporal FIFO):** While graph edges now correctly preserve duplicate transaction IDs without collision, forward tracing in `get_account_trace` is still structural BFS ordered by amount; strict temporal fund tracking ($T_{\text{in}} < T_{\text{out}}$) will be introduced in the Tracing Engine step.
