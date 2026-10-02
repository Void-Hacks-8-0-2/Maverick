# Step 10 — Timeline Investigation + Transaction Explorer
## Backend Report & Verification Summary

**Operation "ABHEDYA-CHAKRA" · Financial Cyber-Forensics & Money Mule Network Investigation Platform**

---

## Verified Baseline

| Metric | Value |
|--------|-------|
| **Total backend tests** | **261 / 261 PASSING** |
| Steps 4–7 | 151 tests |
| Step 8 (Case Diary + AI Narrative) | 55 tests |
| Step 9 (Legal Freeze + Bank Requisition) | 26 tests |
| **Step 10A – Timeline Investigation** | **15 tests** |
| **Step 10B – Transaction Explorer** | **14 tests** |
| Frontend production build | ✅ tsc -b + vite build · 0 errors |
| Dataset rows | 2,000,000 |
| Dataset SHA-256 | `2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101` |

> Dataset is **unchanged**. No locked step behavior was modified.

---

## Step 10A — Timeline Investigation

### Backend

**Route:** `GET /api/timeline`

| Parameter | Type | Description |
|-----------|------|-------------|
| `account_id` | optional str | Filter to a specific account (sender OR receiver). Omit for global window. |
| `start_time` | optional str | ISO-like datetime lower bound. Default `2026-09-15 00:00:00` |
| `end_time` | optional str | ISO-like datetime upper bound. Default `2026-09-29 23:59:58` |
| `direction` | `all`/`in`/`out` | Incoming, outgoing, or both |
| `payment_mode` | optional str | `UPI`, `IMPS`, `NEFT`, `RTGS` |
| `device_type` | optional str | `Android`, `iOS`, etc. |
| `event_type` | optional str | `TRANSACTION`, `VELOCITY`, `ATTRIBUTION`, `RISK_ROLE`, `TERMINAL` |
| `page` / `page_size` | int | Server-side pagination. Max page_size = 250 |

**Event Types Generated (per account):**

| Event Type | Source | Description |
|------------|--------|-------------|
| `TRANSACTION` | Steps 4–6 `transactions` table | Raw transaction record |
| `VELOCITY` | Step 5A `get_velocity_events()` | 3–15 min pass-through detection |
| `ATTRIBUTION` | Step 5C `compute_account_fifo_attribution()` | FIFO fund flow edges |
| `RISK_ROLE` | Step 5B `get_account_risk()` + new `get_account_role()` | Risk index + mule role anchor |
| `TERMINAL` | Role classifier L3-only flag | Terminal sink absorption point |

**New helper:** `get_account_role(con, account_id)` in `backend/detection/role_classifier.py`
- Reads pre-computed `layer1/2/3_candidate` flags from `account_features`
- Returns `AccountRoleResult(NamedTuple)` with `role: str`
- Does NOT re-run the bulk classifier

**Files:**
- `backend/timeline/__init__.py`
- `backend/timeline/models.py`
- `backend/timeline/service.py` — `build_timeline()`
- `backend/timeline/routes.py`
- `tests/test_timeline.py` — 15 tests

### Frontend

**Page:** `TimelineInvestigationView.tsx` → `/timeline`

- Visual chronological timeline with colour-coded event cards
- Account search bar (blank = global event stream)
- Event-type quick-filter pill bar
- Expandable filter panel: date range, direction, payment mode, event type
- Summary metrics bar (total events, inflow, outflow, velocity alerts, FIFO edges)
- Risk/Role banner for account-scoped investigations
- Server-side pagination

---

## Step 10B — Transaction Explorer

### Backend

**Routes:**
- `GET /api/transactions` — multi-filter paginated query
- `GET /api/transactions/{stable_id}` — full transaction detail with investigation links

| Parameter | Description |
|-----------|-------------|
| `transaction_id` | Exact (12-char TXN prefix) or ILIKE partial |
| `account_id` | Sender OR receiver match |
| `sender_account` / `receiver_account` | Directional filters |
| `min_amount` / `max_amount` | Amount bounds |
| `start_time` / `end_time` | Timestamp bounds |
| `payment_mode` / `device_type` | Categorical filters |
| `narration` | ILIKE contains |
| `sender_ifsc` / `receiver_ifsc` | Exact IFSC filters |
| `sort_by` | `timestamp`, `amount`, or `transaction_id` |
| `sort_order` | `asc` / `desc` |
| `page` / `page_size` | Max 250 per page |

**Stable ID scheme:** `row_{rowid}` — deterministic rowid-based identity.

**Detail enrichment (`/transactions/{stable_id}`):**
- Sender & receiver Mule Risk Index (Step 5B)
- Sender & receiver Mule Role (`get_account_role()`)
- Duplicate TX-ID count across dataset
- Deep links to `/timeline`, `/victim`, `/graph`

**Files:**
- `backend/transactions/__init__.py`
- `backend/transactions/models.py`
- `backend/transactions/service.py`
- `backend/transactions/routes.py`
- `tests/test_transactions.py` — 14 tests

### Frontend

**Page:** `TransactionExplorer.tsx` → `/transactions` (rewritten)

- Expandable filter panel (9 filter fields + sort controls)
- Active filter count badge
- Duplicate TX-ID warning icon per row
- Click-to-open side drawer with full detail + forensic context + investigation deep-links
- Server-side pagination over 2M-row dataset

---

## Architecture Notes

- Step 10 is a **pure read-only query layer** over Steps 4–9 outputs. Nothing upstream was modified.
- All 2M transactions remain in DuckDB. The browser receives ≤250 rows per request.
- `get_account_role()` is a lightweight single-row lookup against pre-computed `account_features`.
- A `Timestamp` index (`idx_timestamp`) was added at startup to accelerate time-range queries.
