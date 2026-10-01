"""
Deterministic Account Behavioral Feature Engine for Operation 'ABHEDYA-CHAKRA'
Computes reproducible behavioral metrics from actual production transactions.
Operates via vectorized DuckDB SQL transformations without row-by-row iteration.
"""

from typing import Optional, Dict, Any
import duckdb
from backend.features.models import AccountFeatures


def compute_account_features(con: duckdb.DuckDBPyConnection) -> int:
    """
    Computes deterministic behavioral features for every account entity in the dataset.
    Populates the 'account_features' table in DuckDB.
    Returns the total number of account feature records created (24,873).
    """
    # 1. Base Entity Transactions Union (captures all transactions for each entity)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE entity_tx AS
        SELECT 
            Sender_Account AS acc, 
            Receiver_Account AS cp, 
            Amount AS amt, 
            Timestamp AS ts, 
            Payment_Mode AS pm, 
            Narration AS narr, 
            IP_Address AS ip, 
            Device_Type AS dev, 
            1 AS is_out, 
            0 AS is_in 
        FROM transactions
        UNION ALL
        SELECT 
            Receiver_Account AS acc, 
            Sender_Account AS cp, 
            Amount AS amt, 
            Timestamp AS ts, 
            Payment_Mode AS pm, 
            Narration AS narr, 
            IP_Address AS ip, 
            Device_Type AS dev, 
            0 AS is_out, 
            1 AS is_in 
        FROM transactions;
    """)

    # 2. Entity-level Aggregations
    con.execute("""
        CREATE OR REPLACE TEMP TABLE entity_agg AS
        SELECT 
            acc AS account_number,
            COUNT(*) AS transaction_count,
            SUM(is_in) AS incoming_txn_count,
            SUM(is_out) AS outgoing_txn_count,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS incoming_volume,
            ROUND(COALESCE(SUM(CASE WHEN is_out = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS outgoing_volume,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE -amt END), 0.0), 2) AS net_flow_delta,
            COUNT(DISTINCT CASE WHEN is_in = 1 THEN cp END) AS fan_in,
            COUNT(DISTINCT CASE WHEN is_out = 1 THEN cp END) AS fan_out,
            COUNT(DISTINCT cp) AS unique_counterparties,
            MIN(ts) AS first_seen_timestamp,
            MAX(ts) AS last_seen_timestamp,
            COUNT(DISTINCT CAST(ts AS DATE)) AS active_day_count,
            COUNT(DISTINCT strftime(ts, '%Y-%m-%d %H')) AS active_hour_count,
            COUNT(DISTINCT dev) AS unique_device_count,
            COUNT(DISTINCT ip) AS unique_ip_count,
            COUNT(DISTINCT pm) AS unique_payment_mode_count,
            COUNT(DISTINCT narr) AS unique_narration_count,
            SUM(CASE WHEN narr IS NULL OR TRIM(narr) = '' THEN 1 ELSE 0 END) AS empty_narration_count,
            SUM(CASE WHEN dev = 'Android' THEN 1 ELSE 0 END) AS android_txn_count,
            SUM(CASE WHEN dev = 'iOS' THEN 1 ELSE 0 END) AS ios_txn_count,
            SUM(CASE WHEN dev = 'Windows_Browser' THEN 1 ELSE 0 END) AS windows_browser_txn_count,
            SUM(CASE WHEN dev = 'Web_Emulator' THEN 1 ELSE 0 END) AS web_emulator_txn_count,
            SUM(CASE WHEN dev = 'Linux_Script' THEN 1 ELSE 0 END) AS linux_script_txn_count,
            SUM(CASE WHEN pm = 'UPI' THEN 1 ELSE 0 END) AS upi_txn_count,
            SUM(CASE WHEN pm = 'IMPS' THEN 1 ELSE 0 END) AS imps_txn_count,
            SUM(CASE WHEN pm = 'NEFT' THEN 1 ELSE 0 END) AS neft_txn_count,
            SUM(CASE WHEN pm = 'RTGS' THEN 1 ELSE 0 END) AS rtgs_txn_count,
            COUNT(DISTINCT EXTRACT(HOUR FROM ts)) AS unique_active_hours,
            SUM(CASE WHEN EXTRACT(HOUR FROM ts) BETWEEN 0 AND 5 THEN 1 ELSE 0 END) AS night_transaction_count
        FROM entity_tx
        GROUP BY acc;
    """)

    # 3. Top IP Concentration per Account
    con.execute("""
        CREATE OR REPLACE TEMP TABLE top_ip_per_acc AS
        WITH ip_counts AS (
            SELECT acc, ip, COUNT(*) as ip_tx_cnt,
                   ROW_NUMBER() OVER (PARTITION BY acc ORDER BY COUNT(*) DESC, ip ASC) as rn
            FROM entity_tx
            GROUP BY acc, ip
        )
        SELECT acc, ip_tx_cnt AS top_ip_transaction_count
        FROM ip_counts
        WHERE rn = 1;
    """)

    # 4. Inbound Amount Statistics (from transactions where Receiver_Account = acc)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE in_amt_stats AS
        SELECT 
            Receiver_Account AS acc,
            ROUND(MIN(Amount), 2) AS incoming_amount_min,
            ROUND(MAX(Amount), 2) AS incoming_amount_max,
            ROUND(AVG(Amount), 2) AS incoming_amount_mean,
            ROUND(MEDIAN(Amount), 2) AS incoming_amount_median,
            ROUND(COALESCE(STDDEV_POP(Amount), 0.0), 2) AS incoming_amount_stddev
        FROM transactions
        GROUP BY Receiver_Account;
    """)

    # 5. Outbound Amount Statistics (from transactions where Sender_Account = acc)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE out_amt_stats AS
        SELECT 
            Sender_Account AS acc,
            ROUND(MIN(Amount), 2) AS outgoing_amount_min,
            ROUND(MAX(Amount), 2) AS outgoing_amount_max,
            ROUND(AVG(Amount), 2) AS outgoing_amount_mean,
            ROUND(MEDIAN(Amount), 2) AS outgoing_amount_median,
            ROUND(COALESCE(STDDEV_POP(Amount), 0.0), 2) AS outgoing_amount_stddev
        FROM transactions
        GROUP BY Sender_Account;
    """)

    # 6. Materialize account_features
    con.execute("""
        CREATE OR REPLACE TABLE account_features AS
        SELECT 
            e.account_number,
            -- Flow Features
            e.incoming_txn_count,
            e.outgoing_txn_count,
            e.incoming_volume,
            e.outgoing_volume,
            e.net_flow_delta,
            -- Fan-in & Fan-out
            e.fan_in,
            e.fan_out,
            e.unique_counterparties,
            -- Flow Ratios (Safe NULL on zero denominator)
            CASE WHEN e.incoming_volume > 0 THEN ROUND(e.outgoing_volume / e.incoming_volume, 4) ELSE NULL END AS outflow_to_inflow_ratio,
            CASE WHEN e.outgoing_volume > 0 THEN ROUND(e.incoming_volume / e.outgoing_volume, 4) ELSE NULL END AS inflow_to_outflow_ratio,
            -- Activity Span
            e.first_seen_timestamp,
            e.last_seen_timestamp,
            CAST(EXTRACT(EPOCH FROM e.last_seen_timestamp) - EXTRACT(EPOCH FROM e.first_seen_timestamp) AS BIGINT) AS activity_span_seconds,
            -- Frequency
            e.active_day_count,
            e.active_hour_count,
            CASE WHEN e.active_day_count > 0 THEN ROUND(e.transaction_count / e.active_day_count, 2) ELSE NULL END AS transactions_per_active_day,
            -- Inbound Amount Statistics (NULL if incoming_txn_count == 0)
            ias.incoming_amount_min,
            ias.incoming_amount_max,
            ias.incoming_amount_mean,
            ias.incoming_amount_median,
            ias.incoming_amount_stddev,
            -- Outbound Amount Statistics (NULL if outgoing_txn_count == 0)
            oas.outgoing_amount_min,
            oas.outgoing_amount_max,
            oas.outgoing_amount_mean,
            oas.outgoing_amount_median,
            oas.outgoing_amount_stddev,
            -- Device Profile
            e.unique_device_count,
            e.android_txn_count,
            e.ios_txn_count,
            e.windows_browser_txn_count,
            e.web_emulator_txn_count,
            e.linux_script_txn_count,
            ROUND(e.web_emulator_txn_count / e.transaction_count, 4) AS web_emulator_ratio,
            ROUND(e.linux_script_txn_count / e.transaction_count, 4) AS linux_script_ratio,
            -- IP Profile
            e.unique_ip_count,
            ROUND(e.transaction_count / e.unique_ip_count, 2) AS transactions_per_unique_ip,
            tip.top_ip_transaction_count,
            ROUND(tip.top_ip_transaction_count / e.transaction_count, 4) AS top_ip_transaction_ratio,
            -- Payment Mode Profile
            e.upi_txn_count,
            e.imps_txn_count,
            e.neft_txn_count,
            e.rtgs_txn_count,
            ROUND(e.upi_txn_count / e.transaction_count, 4) AS upi_ratio,
            ROUND(e.imps_txn_count / e.transaction_count, 4) AS imps_ratio,
            ROUND(e.neft_txn_count / e.transaction_count, 4) AS neft_ratio,
            ROUND(e.rtgs_txn_count / e.transaction_count, 4) AS rtgs_ratio,
            -- Narration Profile
            e.unique_narration_count,
            e.empty_narration_count,
            ROUND((e.transaction_count - e.unique_narration_count) / e.transaction_count, 4) AS narration_repeat_ratio,
            -- Temporal Profile
            e.active_day_count AS unique_active_dates,
            e.unique_active_hours,
            e.night_transaction_count,
            ROUND(e.night_transaction_count / e.transaction_count, 4) AS night_transaction_ratio,
            -- Step 4 Deterministic Role Candidate Classifications
            CAST(NULL AS BOOLEAN) AS layer1_candidate,
            CAST(NULL AS BOOLEAN) AS layer2_candidate,
            CAST(NULL AS BOOLEAN) AS layer3_candidate,
            CAST('[]' AS VARCHAR) AS layer1_reasons,
            CAST('[]' AS VARCHAR) AS layer2_reasons,
            CAST('[]' AS VARCHAR) AS layer3_reasons,
            CAST(0 AS BIGINT) AS layer1_signal_count,
            CAST(0 AS BIGINT) AS layer2_signal_count,
            CAST(0 AS BIGINT) AS layer3_signal_count,
            CAST('v1' AS VARCHAR) AS classification_version,
            CAST(NULL AS TIMESTAMP) AS classification_computed_at,
            CAST('CANDIDATE_CLASSIFICATION' AS VARCHAR) AS classification_provenance,
            -- Future Detection Placeholders (Prohibited in Step 4; reserved for later steps)
            CAST(NULL AS DOUBLE) AS mule_risk_index,
            CAST(NULL AS VARCHAR) AS risk_factors,
            CAST(NULL AS BOOLEAN) AS cycle_indicator,
            CAST(NULL AS DOUBLE) AS pass_through_ratio,
            CAST(NULL AS BIGINT) AS pass_through_event_count,
            CAST(NULL AS DOUBLE) AS median_incoming_to_outgoing_seconds,
            CAST(NULL AS BIGINT) AS rapid_outflow_count,
            -- Metadata & Provenance
            'v1' AS feature_version,
            CURRENT_TIMESTAMP::TIMESTAMP AS computed_at,
            'DERIVED' AS provenance
        FROM entity_agg e
        LEFT JOIN top_ip_per_acc tip ON e.account_number = tip.acc
        LEFT JOIN in_amt_stats ias ON e.account_number = ias.acc
        LEFT JOIN out_amt_stats oas ON e.account_number = oas.acc;
    """)

    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_feat_acc_number ON account_features(account_number);")
    
    # Clean up temp tables
    con.execute("DROP TABLE IF EXISTS entity_tx;")
    con.execute("DROP TABLE IF EXISTS entity_agg;")
    con.execute("DROP TABLE IF EXISTS top_ip_per_acc;")
    con.execute("DROP TABLE IF EXISTS in_amt_stats;")
    con.execute("DROP TABLE IF EXISTS out_amt_stats;")

    # Step 4: Run deterministic role classification across all entities
    from backend.detection.role_classifier import classify_account_roles
    classify_account_roles(con)

    return con.execute("SELECT count(*) FROM account_features").fetchone()[0]



def get_account_features(con: duckdb.DuckDBPyConnection, account_id: str) -> Optional[AccountFeatures]:
    """
    Retrieves typed behavioral features for a single account.
    Returns None if the account is not found in the feature store.
    """
    cols = [d[0] for d in con.execute("DESCRIBE account_features").fetchall()]
    row = con.execute("SELECT * FROM account_features WHERE account_number = ?", [account_id.strip()]).fetchone()
    if not row:
        return None
    data = dict(zip(cols, row))
    return AccountFeatures(**data)
