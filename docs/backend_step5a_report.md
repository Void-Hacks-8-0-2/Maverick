# Backend Step 5A Report — Deterministic 3–15 Minute Pass-Through Velocity Detection
**Operation ABHEDYA-CHAKRA**

---

## Summary

| Metric | Value |
|---|---|
| Step | 5A |
| Baseline commit | `9071067` |
| Dataset | `data/VoidHacks8_MuleAccount_2M_Transactions.csv` |
| Transactions | 2,000,000 |
| Unique accounts | 24,873 |
| Duplicate Transaction_IDs | 2,252 (preserved) |
| Test baseline (pre-5A) | 47/47 passing |
| Test baseline (post-5A) | **64/64 passing** (+17 new tests) |
| Step 5A cold computation | ~24,400 ms on production dataset |
| Velocity candidates found | **171** accounts |
| Accounts with qualifying pairs | 24,573 |
| NULL `pass_through_candidate` values | **0** |

---

## Objective

Transform the deterministic behavioral feature layer (Step 3) and role
classification (Step 4) into a **temporal velocity signal**: identify accounts
where ≥90% of incoming funds are dispersed outward within a tight 3–15 minute
window across multiple (≥2) outgoing transfers.

This is an **investigative candidate indicator** only. It does not establish
criminality, fraud, or guilt. No ground-truth mule labels are present in the
production dataset.

---

## Qualifying Window (Inclusive Boundaries)

```
3 min 0 sec (180s)  <=  outgoing_timestamp - incoming_timestamp  <=  15 min 0 sec (900s)
```

| Delay | Classification |
|---|---|
| Exactly 180s (3:00 min) | ✅ INCLUDED — qualifying |
| Exactly 900s (15:00 min) | ✅ INCLUDED — qualifying |
| 179s (2:59 min) | ❌ NOT included — BEFORE_WINDOW |
| 901s (15:01 min) | ❌ NOT included — AFTER_WINDOW |

---

## Candidate Condition

```
pass_through_ratio = qualifying_attributed_volume / total_incoming_volume  >=  0.90
AND qualifying_outgoing_transaction_count  >=  2
```

Both conditions must hold simultaneously. No single condition alone is sufficient.

---

## Algorithm

### Phase 1 — Stable Row Identifier
A `row_number()` over `(Timestamp ASC, Transaction_ID ASC, Sender_Account ASC,
Receiver_Account ASC)` assigns each row a deterministic `rn` identifier. This
allows both rows of a duplicate Transaction_ID to be independently tracked.
The `transactions` source table is **never modified**.

### Phase 2 — Ledger Construction
- `vd_in`: all rows as incoming transactions (keyed by `Receiver_Account`)
- `vd_out`: all rows as outgoing transactions (keyed by `Sender_Account`)

### Phase 3 — Range Join (Qualifying Window)
```sql
JOIN vd_in i ON i.acc = o.acc
           AND i.in_ep BETWEEN (o.out_ep - 900) AND (o.out_ep - 180)
```
DuckDB optimises BETWEEN range joins on sorted epoch columns as a
**merge-join** — no quadratic cross-product. This is the performance-critical
phase: ~12s on 2M rows.

### Phase 4 — Attribution
```
attributed_per_out = min(out_amount, SUM(eligible_in_amounts))
```
Each outgoing transaction is capped at its own face value. No outgoing
transaction can claim more funds than actually arrived. Step 5C will implement
full chronological FIFO attribution.

### Phase 5 — Temporal Bucket Counts
- `under_3_minute_event_count`: bounded range join `[0s, 179s]`
- `over_15_minute_event_count`: bounded range join `[901s, 86400s]` (24h lookback)
Both use the same range-join pattern — no unbounded cross-joins.

### Phase 6 — Account Aggregation and Classification
Pass-through ratio computed per account. Candidate flag set to `TRUE` or
`FALSE` (never `NULL`). Sender-only accounts (no incoming volume) receive
`FALSE` with `NULL` ratio.

### Phase 7 — In-Place UPDATE
`account_features` updated atomically. All 14 Step 5A columns written
in a single `UPDATE ... FROM` statement.

---

## New Fields on `account_features`

| Column | Type | Provenance | Description |
|---|---|---|---|
| `pass_through_ratio` | DOUBLE | DERIVED | attributed_vol / total_incoming_vol |
| `pass_through_event_count` | BIGINT | DERIVED | Qualifying outgoing tx count |
| `median_incoming_to_outgoing_seconds` | DOUBLE | DERIVED | Median delay in qualifying window |
| `rapid_outflow_count` | BIGINT | DERIVED | Distinct outgoing txs with qualifying match |
| `pass_through_candidate` | BOOLEAN | DERIVED | TRUE iff ratio ≥ 0.90 AND out_txs ≥ 2 |
| `pass_through_incoming_volume` | DOUBLE | DERIVED | Total account incoming volume |
| `pass_through_attributed_volume` | DOUBLE | DERIVED | Volume attributed to qualifying events |
| `pass_through_outgoing_transaction_count` | BIGINT | DERIVED | Qualifying outgoing tx count |
| `pass_through_outgoing_volume` | DOUBLE | DERIVED | Sum of qualifying outgoing amounts |
| `under_3_minute_event_count` | BIGINT | DERIVED | Outgoing txs with delay < 3 min |
| `over_15_minute_event_count` | BIGINT | DERIVED | Outgoing txs with delay > 15 min |
| `velocity_classification_version` | VARCHAR | DERIVED | Schema version (`v1`) |
| `velocity_classification_computed_at` | TIMESTAMP | DERIVED | Computation timestamp |
| `velocity_classification_provenance` | VARCHAR | DERIVED | Always `DERIVED` |

---

## New API Endpoint

```
GET /api/accounts/{account_id}/velocity?limit=100
```

Returns event-level explainability for one account's qualifying pass-through events.

**Response schema:**
```json
{
  "account_id": "KKBK10000402",
  "event_count": 11,
  "qualifying_window": "3_TO_15_MINUTES",
  "window_min_seconds": 180,
  "window_max_seconds": 900,
  "provenance": "DERIVED",
  "events": [
    {
      "incoming_transaction_id": "TXN...",
      "outgoing_transaction_id": "TXN...",
      "incoming_timestamp": "2026-09-22 10:00:00",
      "outgoing_timestamp": "2026-09-22 10:07:34",
      "delay_seconds": 454,
      "incoming_amount": 100000.0,
      "outgoing_amount": 85000.0,
      "attributed_amount": 85000.0,
      "window": "3_TO_15_MINUTES",
      "provenance": "DERIVED"
    }
  ]
}
```

---

## Production Results

| Metric | Value |
|---|---|
| Velocity candidates | **171** |
| Max pass_through_ratio | 0.98 |
| Avg pass_through_ratio | 0.034 |
| Median pass_through_ratio | 0.017 |
| Total attributed volume | ₹9.04 Crore |
| Accounts with any qualifying pairs | 24,573 |
| Accounts with no qualifying pairs | 300 (sender-only) |

### Top 5 Velocity Candidates

| Account | Ratio | Qualifying Out Txs | Attributed Vol | Incoming Vol |
|---|---|---|---|---|
| `AXIS10000371` | 0.98 | 5 | ₹1.45L | ₹1.48L |
| `AXIS10000351` | 0.98 | 4 | ₹2.95L | ₹3.01L |
| `ICIC10000379` | 0.98 | 9 | ₹2.52L | ₹2.57L |
| `IPOS10000361` | 0.98 | 10 | ₹4.57L | ₹4.66L |
| `KKBK10000402` | 0.98 | 11 | ₹9.71L | ₹9.91L |

---

## Performance

| Phase | Timing |
|---|---|
| DB cold startup (Steps 1–4) | ~55s |
| Step 5A compute_velocity_features | **~24s** |
| Total startup with Step 5A | ~80s |
| Per-account query (`/velocity` endpoint) | <5ms |

The qualifying range join accounts for ~12s; the before/after bucket
bounded range joins add ~6s each. No unbounded cross-joins are used.

---

## Test Coverage (17 new tests)

| # | Test | Status |
|---|---|---|
| 1 | Exact 3-min boundary included | ✅ PASS |
| 2 | Exact 15-min boundary included | ✅ PASS |
| 3 | Below 3 min excluded (179s) | ✅ PASS |
| 4 | Above 15 min excluded (901s) | ✅ PASS |
| 5 | Exactly 90% ratio qualifies | ✅ PASS |
| 6 | 89.98% ratio does not qualify | ✅ PASS |
| 7 | Single outgoing tx does not qualify | ✅ PASS |
| 8 | Amount conservation per event | ✅ PASS |
| 9 | Partial allocation | ✅ PASS |
| 10 | Duplicate Transaction_ID distinct | ✅ PASS |
| 11 | Non-chronological source order determinism | ✅ PASS |
| 12 | Two consecutive runs identical | ✅ PASS |
| 13 | Zero incoming volume — no divide-by-zero | ✅ PASS |
| 14 | No eligible incoming — outgoing unmatched | ✅ PASS |
| 15 | Multiple eligible incoming — tie-break deterministic | ✅ PASS |
| 16 | Velocity candidate independent of L1/L2 role | ✅ PASS |
| 17 | Production dataset integrity post-5A | ✅ PASS |

---

## Constraints Honoured

- ✅ No Step 5B / 5C features implemented
- ✅ No frontend changes
- ✅ No Git push
- ✅ Production dataset 2,000,000 rows preserved
- ✅ 2,252 duplicate Transaction_IDs preserved
- ✅ 24,873 unique account entities preserved
- ✅ All 47 prior tests still passing
- ✅ Forensic language: Candidate / Indicator / Pattern — never Criminal / Mule / Guilty
- ✅ Amount conservation: attributed_per_out ≤ min(out_amount, in_amount)
- ✅ NULL safety: pass_through_candidate is never NULL for any account
- ✅ Explicit chronological ordering — never relies on CSV row order
