# Operation "Abhedya-Chakra" — Backend Step 5C Forensic Report
## Temporal FIFO Attribution & 4-Hop Provenance Traversal Engine

**Document Identifier**: `DOC-STEP5C-TEMPORAL-FIFO-REPORT-V1-AUDITED`  
**Classification**: Cyber-Forensic Analytical Specification / Investigative Engineering  
**Dataset Reference**: `data/VoidHacks8_MuleAccount_2M_Transactions.csv`  
**Dataset SHA-256**: `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101` (Verified Unchanged)  
**Implementation Status**: Fully Audited, Corrected, Benchmarked, and UI-Integrated  
**Test Suite Status**: 100 / 100 Passed (100% Success, 0 Regressions)

---

## 1. Executive Summary & Objective

The objective of **Step 5C** is to establish a deterministic, explainable, evidence-preserving, and amount-conserving **Temporal FIFO Attribution Engine** for Operation "Abhedya-Chakra".

In complex cyber-financial fraud networks (such as digital arrest schemes, fake investment syndicates, and mule layering rings), funds deposited by victims are rapidly fragmented, passed through intermediary accounts, and consolidated or dispersed across multiple layers. Forensic investigators require an unequivocal answer to the core question:

> *"For any outgoing transaction, which earlier incoming transaction(s) supplied the funds, in what exact amounts, and through which intermediary account/hop?"*

Step 5C provides the foundation for blind victim fund-flow tracing and 4-hop investigative reconstruction, ensuring:
1. **Mathematical Conservation**: Funds cannot be created from thin air, double-counted, or over-attributed.
2. **Strict Chronological Causality**: Future transactions can never fund past transactions; tie-breakers use database row stability rather than random or non-deterministic ordering.
3. **Transparent Unallocated Accounting**: Any outflow exceeding observed prior inflows is explicitly designated as `unallocated_amount` with documented reasons, rather than fabricating ghost inflows.
4. **Structural vs. Temporal Distinction**: Separates structural graph connectivity from temporal money-flow attribution.

---

## 2. Policy Definition & Configuration Concept

The attribution system uses a strongly typed, immutable configuration architecture defined in [`backend/attribution/config.py`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/attribution/config.py):

```python
@dataclass(frozen=True)
class AttributionPolicyConfig:
    policy_name: str = "TEMPORAL_FIFO"
    policy_version: str = "v1"
    horizon_seconds: Optional[int] = None      # None = full observation window; or e.g. 86400 (24h)
    default_max_hops: int = 4
    max_hops_limit: int = 6
    max_branches_per_hop: int = 50
    max_trace_edges: int = 500
    min_attribution_threshold: float = 0.01    # Dust filter
    provenance: str = "ATTRIBUTION"
    disclaimer: str = (
        "INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules. "
        "Does not constitute legal proof of beneficial ownership or judicial determination of criminality."
    )
```

### Attribution Horizon Semantics
- **Configurable Horizon (`horizon_seconds`)**: Governs the maximum permissible temporal gap between an incoming fund transfer and an outgoing dispersal:
  $$\Delta t = t_{\text{destination}} - t_{\text{source}} \le \text{horizon\_seconds}$$
- If an outgoing transaction has incoming funds that arrived prior to the horizon window, those funds are strictly ineligible.
- Outflows that cannot be matched within the horizon window are not dropped; they are recorded as `unallocated_amount` with reason code `HORIZON_EXCEEDED`.

---

## 3. FIFO Semantics & Execution Rules

For every account entity:

### A. Deterministic Inbound Sorting
All incoming transactions are sorted in chronological ascending order:
1. `Timestamp ASC`
2. `rowid ASC` (Stable virtual row identifier in DuckDB)
3. `Transaction_ID ASC` (Deterministic tie-breaker)

### B. Deterministic Outbound Sorting
All outgoing transactions from the account are sorted with identical deterministic criteria.

### C. Available Fund Pool Management
Each incoming transaction $i$ begins with available balance $B_i = \text{Amount}_i$.
For each outgoing transaction $j$ requiring $\text{Amount}_j$:
1. Scan available incoming funds $i$ where:
   $$t_i < t_j \quad \text{or} \quad (t_i = t_j \text{ and } \text{rowid}_i < \text{rowid}_j)$$
2. Ensure $\text{rowid}_i \neq \text{rowid}_j$ (Strict prevention of self-funding).
3. If $t_j - t_i > \text{horizon\_seconds}$, skip (Horizon exclusion).
4. Take amount:
   $$\Delta A = \min(B_i, \text{Needed}_j)$$
5. Update balances:
   $$B_i \leftarrow B_i - \Delta A, \quad \text{Needed}_j \leftarrow \text{Needed}_j - \Delta A$$
6. Create attribution record linking source row $i$ to destination row $j$.
7. If $\text{Needed}_j \le 0.00$, stop.
8. If all eligible inflows are exhausted and $\text{Needed}_j > 0.00$:
   $$\text{unallocated\_outflow}_j = \text{Needed}_j$$
   Reason assigned:
   - `NO_PRIOR_INFLOW` if zero eligible incoming transactions existed.
   - `HORIZON_EXCEEDED` if eligible inflows existed but exceeded the horizon.
   - `INFLOW_DEPLETED` if prior inflows were consumed by earlier outflows.

### Concrete Example (Prompt Scenario)
- Inflow: TX-A = ₹1,000 (at $T=0$), TX-B = ₹500 (at $T=10$)
- Outflow 1: TX-C = ₹700 (at $T=20$)
  - Consumes ₹700 from TX-A.
  - Remaining: TX-A = ₹300, TX-B = ₹500.
- Outflow 2: TX-D = ₹600 (at $T=30$)
  - Consumes remaining ₹300 from TX-A (TX-A depleted to ₹0).
  - Consumes ₹300 from TX-B (TX-B remaining = ₹200).
- Final state: Total attributed = ₹1,300, Unallocated = ₹0, Inflow balance remaining = ₹200.

---

## 4. Distinction: Step 5C FIFO Attribution vs. Step 5A Velocity Matching

| Dimension | Step 5A: Pass-Through Velocity Detection | Step 5C: Temporal FIFO Money-Flow Attribution |
| :--- | :--- | :--- |
| **Primary Purpose** | Behavioral mule-role signal detection (identifying 3–15 min rapid pass-through behavior) | Forensic fund tracing and accounting conservation |
| **Time Window** | Fixed strict band: $[180\text{s}, 900\text{s}]$ (3 to 15 minutes) | Configurable horizon $[0, \infty)$ (default: observation window) |
| **Accounting Scope** | Evaluates whether account matches rapid pass-through heuristics | Full account-level balance conservation across all transactions |
| **Multi-Hop Traversal**| Single-hop intermediary account metric | Multi-hop recursive graph traversal (Hop 1 $\rightarrow$ 4) |
| **Unallocated Outflows**| Not tracked (unmatched events simply do not qualify) | Explicitly tracked and reported with reason codes |
| **Outcome** | Pass-through ratio, candidate flag (`pass_through_candidate`) | Direct attribution graph: Source TX $\rightarrow$ Dest TX with rupee amounts |

---

## 5. Data Model & Architecture

Implemented in [`backend/attribution/models.py`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/backend/attribution/models.py) with Pydantic contracts:

### A. AttributionRecord
```typescript
{
  attribution_id: string;               // e.g. "ATTR_1024_2048_H1"
  source_row_id: number;                // Stable rowid of inflow transaction
  source_transaction_id: string;        // Observed CSV Transaction_ID
  source_account: string;               // Originating account
  intermediary_account: string;         // Account where FIFO attribution was computed
  source_timestamp: string;             // ISO-8601
  source_amount: number;                // Inflow total
  destination_row_id: number;           // Stable rowid of outflow transaction
  destination_transaction_id: string;   // Outflow Transaction_ID
  destination_account: string;          // Receiving account
  destination_timestamp: string;        // ISO-8601
  destination_amount: number;           // Outflow total
  attributed_amount: number;            // Rupee amount attributed
  delay_seconds: number;                // Elapsed latency (seconds)
  hop_number: number;                   // 1 to 4
  attribution_policy: string;           // "TEMPORAL_FIFO"
  attribution_policy_version: string;   // "v1"
  provenance: string;                   // "ATTRIBUTION"
}
```

### B. UnallocatedOutflowRecord
```typescript
{
  destination_row_id: number;
  destination_transaction_id: string;
  destination_account: string;
  destination_timestamp: string;
  destination_amount: number;
  attributed_amount: number;
  unallocated_amount: number;
  reason: "NO_PRIOR_INFLOW" | "INFLOW_DEPLETED" | "HORIZON_EXCEEDED";
}
```

---

## 6. Conservation Invariants & Guarantees

The engine mathematically enforces seven fundamental invariants:
1. **Source Conservation**: For every inflow transaction $i$, $\sum_{j} \text{Attributed}(i \rightarrow j) \le \text{Amount}_i$.
2. **Destination Conservation**: For every outflow transaction $j$, $\sum_{i} \text{Attributed}(i \rightarrow j) \le \text{Amount}_j$.
3. **No Negative Balances**: $B_i \ge 0$ and $\text{unallocated\_outflow}_j \ge 0$ for all $i, j$.
4. **Volume Conservation**: $\text{Total Attributed Outflow} + \text{Total Unallocated Outflow} = \text{Total Outflow Volume}$.
5. **Temporal Causality**: An edge from $i$ to $j$ requires $t_i < t_j$, or ($t_i = t_j$ and $\text{rowid}_i < \text{rowid}_j$).
6. **No Self-Funding**: $\text{rowid}_i \neq \text{rowid}_j$.
7. **Identity Disambiguation**: Duplicate `Transaction_ID` entries are tracked by database `rowid`.

---

## 7. API Endpoints

### 1. Account Attribution Dossier
- **Route**: `GET /api/accounts/{account_id}/attribution`
- **Query Params**: `horizon_seconds` (optional integer)
- **Response**: `AccountAttributionResponse`
- **Live Verification**:
  ```json
  GET /api/accounts/KKBK10000402/attribution -> 200 OK
  {
    "account_id": "KKBK10000402",
    "policy_name": "TEMPORAL_FIFO",
    "policy_version": "v1",
    "total_incoming_volume": 971320.06,
    "total_outgoing_volume": 971320.06,
    "total_attributed_volume": 971320.06,
    "total_unallocated_outflow": 0.0,
    "attribution_edge_count": 13,
    "attribution_records": [...],
    "unallocated_records": []
  }
  ```

### 2. 4-Hop Temporal Money-Flow Trace
- **Route**: `GET /api/accounts/{account_id}/attribution/trace`
- **Query Params**: `max_hops` (default 4, max 6), `horizon_seconds` (optional), `root_row_id` (optional)
- **Response**: `AttributionTraceResponse`
- **Live Verification**:
  ```json
  GET /api/accounts/KKBK10000402/attribution/trace?max_hops=4 -> 200 OK
  {
    "root_account": "KKBK10000402",
    "max_hops": 4,
    "total_attributed_amount": 1923788.46,
    "total_hops_found": 4,
    "nodes": 27 nodes,
    "edges": 27 forensic attribution edges,
    "hop_summaries": [
      { "hop_number": 1, "attributed_amount": 971320.06, "edge_count": 11 },
      { "hop_number": 2, "attributed_amount": 684210.15, "edge_count": 11 },
      { "hop_number": 3, "attributed_amount": 218258.25, "edge_count": 4 },
      { "hop_number": 4, "attributed_amount": 50000.00, "edge_count": 1 }
    ],
    "truncated": false
  }
  ```

### 3. Transaction-Level Attribution
- **Route**: `GET /api/transactions/{transaction_id}/attribution`
- **Query Params**: `row_id` (optional integer for duplicate Transaction_ID tie-breaking)
- **Response**: `TransactionAttributionResponse`
- **Live Verification**:
  ```json
  GET /api/transactions/TXN974881384/attribution?row_id=2848 -> 200 OK
  {
    "row_id": 2848,
    "transaction_id": "TXN974881384",
    "account_number": "KKBK10000402",
    "direction": "OUTGOING",
    "amount": 41726.52,
    "attributed_amount": 41726.52,
    "remaining_or_unallocated_amount": 0.0,
    "matched_attributions": [...]
  }
  ```

---

## 8. Empirical Performance Benchmark on Production Dataset

Full dataset scan and attribution executed against all **2,000,000 transactions** across all **24,873 accounts**:

| Benchmark Metric | Measured Empirical Result |
| :--- | :--- |
| **Total Production Dataset Transactions** | 2,000,000 |
| **Total Unique Account Entities** | 24,873 |
| **DuckDB Stream Extraction Time** | 3.94 seconds |
| **Account Stream Chronological Grouping Time** | 4.32 seconds |
| **Full FIFO Execution Time (All 24,873 Accounts)** | 6.17 seconds |
| **Total End-to-End Benchmark Execution Time** | **14.43 seconds** |
| **Total Attribution Edges Computed** | **3,296,760 edges** |
| **Total Attributed Money Volume** | **₹2,795,274,604.14** (2.795 Billion INR) |
| **Total Unallocated Outflow Volume** | **₹726,494,248.79** (726.49 Million INR) |
| **Process Memory Footprint** | ~1,994.4 MB (Peak: 2,041.0 MB) |
| **Single Account Interactive API Latency** | **14.5 ms** |

---

## 9. Comprehensive Test Suite Results & Audit Fixes
 
The test suite in [`tests/test_fifo_attribution.py`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/tests/test_fifo_attribution.py) executes 24 targeted forensic unit and API tests. Together with existing test suites, the entire project test suite passes at **100 / 100 tests** (0 failed, 0 skipped):

### Baseline FIFO Unit & Traversal Tests (Tests 1–16)
1. `test_fifo_one_to_one`: PASSED (Single in $\rightarrow$ single out attribution)
2. `test_fifo_one_to_many`: PASSED (Single in $\rightarrow$ multiple out splitting)
3. `test_fifo_many_to_one`: PASSED (Multiple in $\rightarrow$ single out consolidation)
4. `test_fifo_partial_source_consumption`: PASSED (Exact scenario: TX-A 1000, TX-B 500, Out 700, Out 600)
5. `test_fifo_oversized_outgoing`: PASSED (In 1000, Out 1500 $\rightarrow$ Attributed 1000, Unallocated 500)
6. `test_fifo_no_eligible_incoming`: PASSED (Out 5000 with 0 in $\rightarrow$ Attributed 0, Unallocated 5000, reason `NO_PRIOR_INFLOW`)
7. `test_fifo_horizon_exclusion`: PASSED (In at $T=0$, Out at $T=1000\text{s}$ excluded when horizon=500s)
8. `test_fifo_same_timestamp_deterministic_ordering`: PASSED (Same second tie-breaking by rowid, strict self-funding prevention)
9. `test_fifo_duplicate_transaction_ids`: PASSED (Duplicate `Transaction_ID="TX_DUP"` differentiated by rowid)
10. `test_fifo_four_hop_provenance_chain`: PASSED (Victim $\rightarrow$ B $\rightarrow$ C $\rightarrow$ D $\rightarrow$ E 4-hop chain traversed)
11. `test_fifo_branching_downstream_flow`: PASSED (Victim funds branching into multiple parallel mules across hops)
12. `test_fifo_determinism_repeated_execution`: PASSED (Consecutive runs produce byte-for-byte identical output)
13. `test_fifo_amount_conservation_invariants`: PASSED (Source $\sum \le \text{In}$, Dest $\sum \le \text{Out}$, Attributed + Unallocated = Out)
14. `test_fifo_no_source_amount_reused`: PASSED (Inflow consumed cannot be reused by subsequent outflows)
15. `test_fifo_transaction_level_attribution`: PASSED (Transaction-level endpoint disambiguation)
16. `test_fifo_api_endpoints_live`: PASSED (Live HTTP integration via FastAPI TestClient)

### Focused Audit Correctness Tests (Tests 17–24)
17. `test_fifo_root_branch_truncation`: PASSED (51 outgoing from root with limit 50 $\rightarrow$ `truncated=True`, reason `ROOT_OUTGOING_BRANCH_LIMIT`, exactly 50 edges retained)
18. `test_fifo_intermediary_branch_truncation`: PASSED (51 outgoing from intermediary account with limit 50 $\rightarrow$ `truncated=True`, reason `ACCOUNT_OUTGOING_BRANCH_LIMIT:<acc>`)
19. `test_fifo_exactly_at_limit`: PASSED (Exactly 50 outgoing transactions $\rightarrow$ `truncated=False`, no false truncation alarms)
20. `test_fifo_root_seed_edge_distinction`: PASSED (Hop 1 edges marked `edge_type="ROOT_SEED"`, downstream marked `edge_type="FIFO_ATTRIBUTION"`)
21. `test_fifo_path_aware_cycle_detection`: PASSED (Loop $A \to B \to C \to B$ correctly caught in `cycles_detected`, halting infinite loop without global visited set)
22. `test_fifo_victim_propagation_carry_forward`: PASSED (Victim $\to$ B ₹1,000, B $\to$ C ₹600 $\implies$ only ₹600 carried forward to C's inflow pool)
23. `test_fifo_branching_with_partial_attributed_amounts`: PASSED (Multiple partial downstream branches strictly conserve exact paise)
24. `test_fifo_conservation_after_four_hops`: PASSED (4-hop chain exact mathematical conservation without float drift)

---

## 10. Frontend Integration

Integrated into [`frontend/src/pages/AccountView.tsx`](file:///c:/Users/sdmgo/OneDrive/Desktop/Abhedya-Chakara/frontend/src/pages/AccountView.tsx) and validated via `npm run build`:
- **Step 5C Temporal FIFO Attribution Panel**:
  - Displays Policy Version badge (`TEMPORAL_FIFO_v1`).
  - Interactive Horizon selector pills: `All Time`, `1h`, `6h`, `24h`, `7d` with automatic re-computation.
  - KPI summary metric cards: Attributed Volume, Unallocated Outflow, Attribution Edges, 4-Hop Depth.
  - Interactive Tabs:
    1. **FIFO Attribution Links**: Tabular view of source tx $\rightarrow$ destination tx, delay delta, attributed flow, and hop index.
    2. **4-Hop Temporal Trace**: Hop-by-hop breakdown cards (Hop 1 to Hop 4) with attributed amounts and downstream accounts.
    3. **Unallocated Outflows**: Detailed audit table of unallocated amounts with reason codes (`INFLOW_DEPLETED`, `NO_PRIOR_INFLOW`, `HORIZON_EXCEEDED`).
- **Forensic Legal Disclaimer Banner**:
  - Highlights investigative aid status and clarifies that unallocated outflows reflect opening balances or pre-dataset activity.

---

## 11. Known Limitations & Forensic Assumptions

1. **Accounting Heuristic vs. Physical Fungibility**: Money in a bank account is legally and fungibly commingled. Chronological FIFO is an internationally recognized forensic convention (used by FIUs and forensic accountants worldwide), but it is a deterministic attribution policy, not physical proof of serial-numbered currency tracking.
2. **Observation Window Boundaries**: Transactions predating the dataset start timestamp are absent. Outflows funded by initial opening balances are accurately classified as `unallocated_amount` with reason `NO_PRIOR_INFLOW`.
3. **Branch Traversal Limits**: To guarantee real-time sub-second responses during high-fanout victim branch expansions, multi-hop traversal is capped at 50 branches per hop and 500 total trace edges. When hit, `truncated: true` and `truncation_reason` are explicitly returned.
