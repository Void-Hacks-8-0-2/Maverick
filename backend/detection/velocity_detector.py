"""
Step 5A -- Deterministic 3-15 Minute Pass-Through Velocity Detector
Operation 'ABHEDYA-CHAKRA'

QUALIFYING WINDOW (INCLUSIVE on both boundaries):
    3 min 0 sec  (180s)  <=  outgoing_ts - incoming_ts  <=  15 min 0 sec (900s)

BOUNDARY BEHAVIOR:
    exactly 3:00 minutes  (180s) -> INCLUDED
    exactly 15:00 minutes (900s) -> INCLUDED
    2:59 min (179s)              -> NOT included
    15:01 min (901s)             -> NOT included

TEMPORAL MATCHING POLICY:
    Per-account, all (incoming, outgoing) pairs within the qualifying window are
    identified using a RANGE JOIN on EPOCH values. DuckDB optimises range joins on
    sorted inputs as a merge-join -- no quadratic cross-product.

    Attribution policy (Step 5A simplified greedy):
        attributed_per_out = min(out_amount, sum of eligible in_amounts)
    This caps each outgoing at its face value. Step 5C will refine with full FIFO.

CANDIDATE CONDITION:
    pass_through_ratio = sum(attributed_per_out) / total_incoming_volume >= 0.90
    AND qualifying_outgoing_tx_count >= 2

PERFORMANCE:
    No unbounded cross-joins. Only the qualifying [180s, 900s] range join is executed.
    under_3_minute_event_count and over_15_minute_event_count are approximated from
    a window-function analysis on sorted per-account incoming/outgoing lists --
    no cross-join required.

INVESTIGATIVE ONLY -- does not establish criminality or fraud.
"""

import time
from typing import Optional, Dict, Any, List
import duckdb

from backend.detection.thresholds import VelocityThresholds, DEFAULT_VELOCITY_THRESHOLDS


_VELOCITY_COLUMNS: List[tuple] = [
    ("pass_through_ratio",                      "DOUBLE"),
    ("pass_through_event_count",                "BIGINT"),
    ("median_incoming_to_outgoing_seconds",     "DOUBLE"),
    ("rapid_outflow_count",                     "BIGINT"),
    ("pass_through_candidate",                  "BOOLEAN"),
    ("pass_through_incoming_volume",            "DOUBLE"),
    ("pass_through_attributed_volume",          "DOUBLE"),
    ("pass_through_outgoing_transaction_count", "BIGINT"),
    ("pass_through_outgoing_volume",            "DOUBLE"),
    ("under_3_minute_event_count",              "BIGINT"),
    ("over_15_minute_event_count",              "BIGINT"),
    ("velocity_classification_version",         "VARCHAR"),
    ("velocity_classification_computed_at",     "TIMESTAMP"),
    ("velocity_classification_provenance",      "VARCHAR"),
]


def _ensure_velocity_columns(con: duckdb.DuckDBPyConnection) -> None:
    existing = {d[0] for d in con.execute("DESCRIBE account_features").fetchall()}
    for col_name, col_type in _VELOCITY_COLUMNS:
        if col_name not in existing:
            con.execute("ALTER TABLE account_features ADD COLUMN " + col_name + " " + col_type + ";")


def compute_velocity_features(
    con: duckdb.DuckDBPyConnection,
    thresholds: Optional[VelocityThresholds] = None,
) -> Dict[str, Any]:
    """
    Computes Step 5A pass-through velocity features for all account entities.

    Uses DuckDB range-join optimisation for the [180s, 900s] qualifying window.
    No unbounded cross-joins. Updates account_features in-place.
    Returns aggregate summary dict.

    Performance note:
        The qualifying range join (in_epoch BETWEEN out_epoch-900 AND out_epoch-180)
        is processed by DuckDB as a merge-join on sorted epoch columns.
        Timing target: < 120s on the 2M production dataset.
    """
    if thresholds is None:
        thresholds = DEFAULT_VELOCITY_THRESHOLDS

    min_s   = int(thresholds.min_delay_seconds)         # 180
    max_s   = int(thresholds.max_delay_seconds)         # 900
    min_r   = float(thresholds.min_pass_through_ratio)  # 0.90
    min_tx  = int(thresholds.min_pass_through_outgoing_tx)  # 2
    ver     = str(thresholds.velocity_version)
    prov    = str(thresholds.provenance)

    t_start = time.perf_counter()
    _ensure_velocity_columns(con)

    # -----------------------------------------------------------------------
    # Phase 1: Enumerate transactions with stable row_id (duplicate-TxID safe)
    # Source transactions table is NOT modified.
    # -----------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE vd_tx AS
        SELECT
            row_number() OVER (
                ORDER BY Timestamp ASC, Transaction_ID ASC,
                         Sender_Account ASC, Receiver_Account ASC
            )                        AS rn,
            Sender_Account           AS sender,
            Receiver_Account         AS receiver,
            Amount,
            EPOCH(Timestamp)::BIGINT AS ep
        FROM transactions;
    """)

    # -----------------------------------------------------------------------
    # Phase 2: Per-account incoming / outgoing flat ledgers
    # -----------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE vd_in AS
        SELECT receiver AS acc, rn, Amount AS in_amt, ep AS in_ep
        FROM vd_tx;
    """)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE vd_out AS
        SELECT sender AS acc, rn, Amount AS out_amt, ep AS out_ep
        FROM vd_tx;
    """)

    # -----------------------------------------------------------------------
    # Phase 3: Qualifying pairs via RANGE JOIN [min_s, max_s] (INCLUSIVE)
    #
    # Condition:  out_ep - in_ep  BETWEEN  min_s  AND  max_s
    # Equivalent: in_ep BETWEEN (out_ep - max_s) AND (out_ep - min_s)
    #
    # DuckDB recognises this BETWEEN clause on indexed/sorted columns as a
    # range-join (merge-join), avoiding a full N*M cross product.
    # -----------------------------------------------------------------------
    con.execute(
        "CREATE OR REPLACE TEMP TABLE vd_pairs AS "
        "SELECT "
        "  o.acc, "
        "  i.rn AS in_rn, o.rn AS out_rn, "
        "  i.in_amt, o.out_amt, "
        "  (o.out_ep - i.in_ep) AS delay_s, "
        "  o.out_ep, i.in_ep "
        "FROM vd_out o "
        "JOIN vd_in i "
        "  ON i.acc = o.acc "
        " AND i.in_ep BETWEEN (o.out_ep - " + str(max_s) + ") "
        "                  AND (o.out_ep - " + str(min_s) + ");"
    )

    # -----------------------------------------------------------------------
    # Phase 4: Per-outgoing attribution
    #   attributed = min(out_amount, sum_of_eligible_in_amounts)
    # -----------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE vd_out_attr AS
        SELECT
            acc,
            out_rn,
            out_amt,
            LEAST(out_amt, SUM(in_amt)) AS attr_amt,
            COUNT(DISTINCT in_rn)       AS elig_in_cnt,
            MEDIAN(delay_s)             AS med_delay_s
        FROM vd_pairs
        GROUP BY acc, out_rn, out_amt;
    """)

    # -----------------------------------------------------------------------
    # Phase 5: Per-account total incoming volume
    # -----------------------------------------------------------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE vd_total_in AS
        SELECT acc, SUM(in_amt) AS total_in_vol
        FROM vd_in
        GROUP BY acc;
    """)

    # -----------------------------------------------------------------------
    # Phase 6: Account-level velocity aggregation
    #
    # under_3_minute_event_count: for each outgoing tx, count distinct outgoing txs
    #   that have at least one incoming tx with delay 0 <= delay < min_s.
    #   We derive this from a SEPARATE (lighter) range join with the 0..min_s-1 window.
    #
    # over_15_minute_event_count: similarly for delay > max_s.
    #
    # Both are per-outgoing-tx flags, NOT per-(in,out) pair.
    # We only need to know IF an outgoing tx has any near-window incoming.
    # -----------------------------------------------------------------------
    # Before-window count: outgoing txs with any incoming in [0s, min_s-1s]
    con.execute(
        "CREATE OR REPLACE TEMP TABLE vd_before AS "
        "SELECT o.acc, COUNT(DISTINCT o.rn) AS before_cnt "
        "FROM vd_out o "
        "JOIN vd_in i "
        "  ON i.acc = o.acc "
        " AND i.in_ep BETWEEN (o.out_ep - " + str(min_s - 1) + ") "
        "                  AND o.out_ep "
        "GROUP BY o.acc;"
    )

    # After-window count: outgoing txs with any incoming strictly before (out_ep - max_s)
    # i.e. delay > max_s means in_ep < out_ep - max_s
    # Use a bounded lookback of max 24h (86400s) to avoid full scan
    _LOOKBACK = 86400  # 24 hours -- sensible upper bound for after-window detection
    con.execute(
        "CREATE OR REPLACE TEMP TABLE vd_after AS "
        "SELECT o.acc, COUNT(DISTINCT o.rn) AS after_cnt "
        "FROM vd_out o "
        "JOIN vd_in i "
        "  ON i.acc = o.acc "
        " AND i.in_ep BETWEEN (o.out_ep - " + str(_LOOKBACK) + ") "
        "                  AND (o.out_ep - " + str(max_s + 1) + ") "
        "GROUP BY o.acc;"
    )

    # -----------------------------------------------------------------------
    # Phase 7: Final aggregation -> velocity_agg
    # -----------------------------------------------------------------------
    con.execute(
        "CREATE OR REPLACE TEMP TABLE vd_agg AS "
        "WITH q AS ( "
        "  SELECT acc, "
        "    SUM(attr_amt)   AS attr_vol, "
        "    SUM(out_amt)    AS out_vol, "
        "    COUNT(*)        AS out_tx_cnt, "
        "    MEDIAN(med_delay_s) AS med_delay, "
        "    COUNT(DISTINCT out_rn) AS rapid_out_cnt "
        "  FROM vd_out_attr GROUP BY acc "
        ") "
        "SELECT "
        "  ti.acc, "
        "  ti.total_in_vol, "
        "  COALESCE(q.attr_vol, 0.0)       AS attr_vol, "
        "  COALESCE(q.out_vol, 0.0)        AS out_vol, "
        "  COALESCE(q.out_tx_cnt, 0)       AS out_tx_cnt, "
        "  q.med_delay                     AS med_delay, "
        "  COALESCE(q.rapid_out_cnt, 0)    AS rapid_out_cnt, "
        "  CASE WHEN ti.total_in_vol > 0 "
        "    THEN ROUND(COALESCE(q.attr_vol, 0.0) / ti.total_in_vol, 6) "
        "    ELSE NULL END                 AS pt_ratio, "
        "  CASE WHEN ti.total_in_vol > 0 "
        "    AND COALESCE(q.attr_vol, 0.0) / ti.total_in_vol >= " + str(min_r) + " "
        "    AND COALESCE(q.out_tx_cnt, 0) >= " + str(min_tx) + " "
        "    THEN TRUE ELSE FALSE END      AS pt_candidate, "
        "  COALESCE(bw.before_cnt, 0)      AS before_cnt, "
        "  COALESCE(aw.after_cnt, 0)       AS after_cnt "
        "FROM vd_total_in ti "
        "LEFT JOIN q  ON ti.acc = q.acc "
        "LEFT JOIN vd_before bw ON ti.acc = bw.acc "
        "LEFT JOIN vd_after  aw ON ti.acc = aw.acc;"
    )

    # -----------------------------------------------------------------------
    # Phase 8: UPDATE account_features
    # -----------------------------------------------------------------------
    con.execute(
        "UPDATE account_features af "
        "SET "
        "  pass_through_ratio                      = v.pt_ratio, "
        "  pass_through_event_count                = v.out_tx_cnt, "
        "  median_incoming_to_outgoing_seconds     = v.med_delay, "
        "  rapid_outflow_count                     = v.rapid_out_cnt, "
        "  pass_through_candidate                  = v.pt_candidate, "
        "  pass_through_incoming_volume            = v.total_in_vol, "
        "  pass_through_attributed_volume          = v.attr_vol, "
        "  pass_through_outgoing_transaction_count = v.out_tx_cnt, "
        "  pass_through_outgoing_volume            = v.out_vol, "
        "  under_3_minute_event_count              = v.before_cnt, "
        "  over_15_minute_event_count              = v.after_cnt, "
        "  velocity_classification_version         = '" + ver + "', "
        "  velocity_classification_computed_at     = CURRENT_TIMESTAMP::TIMESTAMP, "
        "  velocity_classification_provenance      = '" + prov + "' "
        "FROM vd_agg v "
        "WHERE af.account_number = v.acc;"
    )

    # Sender-only accounts (no incoming) -> FALSE, not NULL
    con.execute(
        "UPDATE account_features "
        "SET pass_through_candidate = FALSE "
        "WHERE pass_through_candidate IS NULL;"
    )

    # -----------------------------------------------------------------------
    # Cleanup temp tables
    # -----------------------------------------------------------------------
    for tbl in ["vd_tx", "vd_in", "vd_out", "vd_pairs",
                "vd_out_attr", "vd_total_in", "vd_before", "vd_after", "vd_agg"]:
        con.execute("DROP TABLE IF EXISTS " + tbl + ";")

    t_end = time.perf_counter()
    duration_ms = round((t_end - t_start) * 1000, 2)

    s = con.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN pass_through_candidate THEN 1 ELSE 0 END),
            SUM(CASE WHEN pass_through_ratio IS NOT NULL THEN 1 ELSE 0 END),
            ROUND(AVG(CASE WHEN pass_through_ratio IS NOT NULL THEN pass_through_ratio END), 6),
            ROUND(MEDIAN(CASE WHEN pass_through_ratio IS NOT NULL THEN pass_through_ratio END), 6),
            ROUND(MAX(CASE WHEN pass_through_ratio IS NOT NULL THEN pass_through_ratio END), 6),
            COALESCE(SUM(CASE WHEN pass_through_candidate THEN pass_through_attributed_volume ELSE 0 END), 0.0),
            SUM(CASE WHEN pass_through_candidate IS NULL THEN 1 ELSE 0 END)
        FROM account_features;
    """).fetchone()

    return {
        "total_accounts":            s[0],
        "velocity_candidates":       s[1],
        "accounts_with_ratio":       s[2],
        "avg_pass_through_ratio":    s[3],
        "median_pass_through_ratio": s[4],
        "max_pass_through_ratio":    s[5],
        "total_attributed_volume":   round(s[6] or 0.0, 2),
        "null_candidate_count":      s[7],
        "velocity_version":          ver,
        "velocity_provenance":       prov,
        "duration_ms":               duration_ms,
        "min_delay_seconds":         min_s,
        "max_delay_seconds":         max_s,
        "min_pass_through_ratio":    min_r,
        "min_pass_through_outgoing_tx": min_tx,
    }


def get_velocity_events(
    con: duckdb.DuckDBPyConnection,
    account_id: str,
    thresholds: Optional[VelocityThresholds] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Returns structured event-level explainability records for a single account's
    qualifying pass-through velocity events.

    All transaction fields (Transaction_ID, Timestamp, Amount) are OBSERVED.
    attributed_amount, delay_seconds, and window label are DERIVED.
    Returns an empty list if no qualifying events exist.
    """
    if thresholds is None:
        thresholds = DEFAULT_VELOCITY_THRESHOLDS

    min_s = int(thresholds.min_delay_seconds)
    max_s = int(thresholds.max_delay_seconds)

    rows = con.execute(
        "WITH "
        "inc AS ( "
        "  SELECT Transaction_ID AS in_tx_id, Amount AS in_amt, "
        "    Timestamp AS in_ts, EPOCH(Timestamp)::BIGINT AS in_ep "
        "  FROM transactions WHERE Receiver_Account = ? "
        "), "
        "out AS ( "
        "  SELECT Transaction_ID AS out_tx_id, Amount AS out_amt, "
        "    Timestamp AS out_ts, EPOCH(Timestamp)::BIGINT AS out_ep "
        "  FROM transactions WHERE Sender_Account = ? "
        "), "
        "pairs AS ( "
        "  SELECT i.in_tx_id, o.out_tx_id, "
        "    CAST(i.in_ts AS VARCHAR) AS in_ts_str, "
        "    CAST(o.out_ts AS VARCHAR) AS out_ts_str, "
        "    (o.out_ep - i.in_ep) AS delay_s, "
        "    i.in_amt, o.out_amt, "
        "    LEAST(o.out_amt, i.in_amt) AS attr_amt "
        "  FROM out o JOIN inc i "
        "    ON i.in_ep BETWEEN (o.out_ep - " + str(max_s) + ") "
        "                   AND (o.out_ep - " + str(min_s) + ") "
        ") "
        "SELECT * FROM pairs "
        "ORDER BY out_ts_str ASC, out_tx_id ASC, in_ts_str ASC, in_tx_id ASC "
        "LIMIT " + str(limit) + ";",
        [account_id, account_id],
    ).fetchall()

    return [
        {
            "incoming_transaction_id": r[0],
            "outgoing_transaction_id": r[1],
            "incoming_timestamp":      r[2],
            "outgoing_timestamp":      r[3],
            "delay_seconds":           int(r[4]),
            "incoming_amount":         float(r[5]),
            "outgoing_amount":         float(r[6]),
            "attributed_amount":       float(r[7]),
            "window":                  "3_TO_15_MINUTES",
            "provenance":              "DERIVED",
        }
        for r in rows
    ]
