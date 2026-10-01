# Operation Abhedya-Chakra — Backend Step 3 Report
**Milestone:** Deterministic Account Behavioral Feature Engine  
**Baseline Dataset:** `data/VoidHacks8_MuleAccount_2M_Transactions.csv` (2,000,000 records, SHA-256: `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101`)

---

## STEP 3 COMPLETE

### Feature records:
**24,873 accounts** (100% complete coverage matching `accounts_dimension`, including 24,188 two-way accounts, 385 receiver-only accounts, and 300 sender-only accounts).

---

### Feature groups implemented:

1. **Flow Features:**
   - `incoming_txn_count`: Total count of incoming transactions.
   - `outgoing_txn_count`: Total count of outgoing transactions.
   - `incoming_volume`: Monetary sum of inbound funds.
   - `outgoing_volume`: Monetary sum of outbound funds.
   - `net_flow_delta`: Observed Net Flow Delta (`incoming_volume - outgoing_volume`), reconciled with `accounts_dimension`.

2. **Fan-In / Fan-Out:**
   - `fan_in`: Count of unique sender accounts transferring into target account.
   - `fan_out`: Count of unique receiver accounts receiving from target account.

3. **Counterparties:**
   - `unique_counterparties`: Count of distinct counterparty entities across inbound and outbound transactions (`senders ∪ receivers`).

4. **Flow Ratios:**
   - `outflow_to_inflow_ratio`: Ratio of outflow to inflow (`NULL` on zero inflow).
   - `inflow_to_outflow_ratio`: Ratio of inflow to outflow (`NULL` on zero outflow).

5. **Activity Span:**
   - `first_seen_timestamp`: Earliest transaction timestamp involving account.
   - `last_seen_timestamp`: Latest transaction timestamp involving account.
   - `activity_span_seconds`: Elapsed time in seconds between first and last seen timestamps.

6. **Transaction Frequency:**
   - `active_day_count`: Number of distinct calendar dates with activity.
   - `active_hour_count`: Number of distinct calendar hours with activity.
   - `transactions_per_active_day`: Average transactions per active day.

7. **Amount Statistics:**
   - Inbound: `incoming_amount_min`, `incoming_amount_max`, `incoming_amount_mean`, `incoming_amount_median`, `incoming_amount_stddev` (`NULL` if `incoming_txn_count == 0`).
   - Outbound: `outgoing_amount_min`, `outgoing_amount_max`, `outgoing_amount_mean`, `outgoing_amount_median`, `outgoing_amount_stddev` (`NULL` if `outgoing_txn_count == 0`).

8. **Device Profile:**
   - `unique_device_count`: Distinct devices observed.
   - Counts: `android_txn_count`, `ios_txn_count`, `windows_browser_txn_count`, `web_emulator_txn_count`, `linux_script_txn_count`.
   - Behavioral ratios: `web_emulator_ratio`, `linux_script_ratio`.

9. **IP Profile:**
   - `unique_ip_count`: Count of distinct IP addresses used.
   - `transactions_per_unique_ip`: Average transactions per unique IP.
   - Concentration: `top_ip_transaction_count`, `top_ip_transaction_ratio`.

10. **Payment Mode Profile:**
    - Counts: `upi_txn_count`, `imps_txn_count`, `neft_txn_count`, `rtgs_txn_count`.
    - Proportions: `upi_ratio`, `imps_ratio`, `neft_ratio`, `rtgs_ratio`.

11. **Narration Profile:**
    - `unique_narration_count`: Distinct narrations.
    - `empty_narration_count`: Count of missing or empty narrations.
    - `narration_repeat_ratio`: Repetition proportion (`1 - unique/total`).

12. **Temporal Profile:**
    - `unique_active_dates`: Distinct active dates.
    - `unique_active_hours`: Distinct active hours of the day (0-23).
    - `night_transaction_count`: Transactions occurring between 00:00 and 05:59.
    - `night_transaction_ratio`: Proportion of transactions occurring at night.

13. **Detection Placeholders (Step 4 Candidates):**
    - `layer1_candidate`, `layer2_candidate`, `layer3_candidate`, `mule_risk_index`, `risk_factors`, `cycle_indicator`, `pass_through_ratio`, `pass_through_event_count`, `median_incoming_to_outgoing_seconds`, `rapid_outflow_count` — all strictly `NULL` until Step 4.

14. **Provenance & Versioning:**
    - `feature_version = "v1"`, `computed_at = timestamp`, `provenance = "DERIVED"`.

---

### Performance:

- **Isolated Feature Computation:** **8.98 s** (Vectorized DuckDB aggregation across 2,000,000 records).
- **Cold Startup:** **24.93 s** (CSV Ingestion [~1.5s] + 3 Raw Indexes [~7.1s] + Materialized Dimension [~3.7s] + Dimension Indexes [~0.2s] + Full Feature Computation [~8.9s] + Feature Unique Index [~0.1s] + Lifespan check).
- **Account Features API Lookup:** **min = 15.02 ms**, **avg = 37.64 ms** (`GET /api/accounts/{account_id}/features`).

---

### Correctness tests:
**38 / 38 passed** (100% test pass rate across the full test suite).
- `tests/test_behavioral_features.py`: 13/13 PASS
  - Account coverage (24,873/24,873)
  - Flow reconciliation against `accounts_dimension`
  - Fan-in direct SQL verification
  - Fan-out direct SQL verification
  - Counterparties union verification
  - Device counts verification
  - Payment mode counts verification
  - IP counts verification
  - Timestamp span verification
  - Sender-only zero/NULL semantics
  - Receiver-only zero/NULL semantics
  - Feature determinism (two full passes identical)
  - API endpoint contract (`GET /api/accounts/{id}/features`)
- `tests/test_accounts_dimension.py`: 7/7 PASS
- `tests/test_api.py`: 8/8 PASS
- `tests/test_graph_integrity.py`: 2/2 PASS
- `tests/test_production_dataset.py`: 8/8 PASS

---

### Determinism:
**PASS**
Running the feature computation pipeline twice produces identical snapshots across all 24,873 accounts and all feature dimensions (excluding dynamic `computed_at` timestamp).

---

### Production dataset integrity:
**PASS**
- Total rows: 2,000,000 (unchanged, unmutated)
- Total columns: 11 (unchanged)
- Total nulls: 0 (verified)
- Unique Transaction_IDs: 1,997,748
- Duplicate Transaction_ID records: 2,252 (all preserved)

---

### Known limitations:
1. **Volatile In-Memory Storage:** The features reside in DuckDB `:memory:`. On application restart, features are recomputed in ~8.98 s during cold startup (total cold startup is ~24.9s, well below the competition's ≤60s limit).
2. **Detection & Risk Fields Unpopulated:** As mandated by Step 3 constraints, role classifications (`layer1_candidate`, `layer2_candidate`, `layer3_candidate`), velocity metrics (`pass_through_ratio`, `3-15 min window`), and `mule_risk_index` remain `NULL`. They will be deterministically populated in Step 4.

---

### Files changed:
1. [backend/features/models.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/models.py): Typed `AccountFeatures` Pydantic model with 67 behavioral fields and clean NULL/None defaults.
2. [backend/features/behavioral.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/behavioral.py): Vectorized DuckDB calculation engine (`compute_account_features`) and typed fetcher (`get_account_features`).
3. [backend/features/store.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/store.py): Feature store initialization and lifecycle management.
4. [backend/features/__init__.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/features/__init__.py): Module exports.
5. [backend/db/connection.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/db/connection.py): Integrated feature store computation into analytical tier startup.
6. [backend/api/routes.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/api/routes.py): Added `GET /api/accounts/{account_id}/features` forensic inspection route.
7. [tests/test_behavioral_features.py](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_behavioral_features.py): New 13-test correctness and determinism suite.
8. [docs/backend_step3_report.md](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/docs/backend_step3_report.md): Step 3 documentation report.
