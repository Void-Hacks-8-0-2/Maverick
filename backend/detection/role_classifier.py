"""
Forensic Role Classifier Engine for Operation 'ABHEDYA-CHAKRA'
Step 4: Deterministic Layer 1 / Layer 2 / Layer 3 Mule Role Candidate Generation.

Transforms production-derived behavioral features into deterministic, explainable
candidate role classifications:
- Layer 1 — Collector Mule Candidate (inbound aggregation behavior)
- Layer 2 — Distributor Mule Candidate (outbound distribution behavior)
- Layer 3 — Terminal/Cash-Out Node Candidate (sink absorption or automated egress)

INVESTIGATIVE CANDIDATE CLASSIFICATION ONLY — NOT A DECLARATION OF CRIMINALITY.
Operates via vectorized DuckDB SQL transformations without row-by-row iteration.
"""

import time
from typing import Optional, Dict, Any
import duckdb

from backend.detection.thresholds import (
    RoleClassificationThresholds,
    DEFAULT_THRESHOLDS,
)


def classify_account_roles(
    con: duckdb.DuckDBPyConnection,
    thresholds: Optional[RoleClassificationThresholds] = None,
) -> Dict[str, Any]:
    """
    Computes deterministic candidate role classifications for all account entities.
    Updates the 'account_features' table in DuckDB in-place with true/false flags,
    structured explainable reasons, and classification metadata.
    
    Returns an analytical summary dictionary of candidate counts and overlaps.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    t1 = thresholds.layer1
    t2 = thresholds.layer2
    t3 = thresholds.layer3
    ver = thresholds.classification_version
    prov = thresholds.provenance

    t_start = time.perf_counter()

    # 1. Ensure classification columns exist in account_features
    existing_cols = {d[0] for d in con.execute("DESCRIBE account_features").fetchall()}
    
    col_definitions = [
        ("layer1_candidate", "BOOLEAN"),
        ("layer2_candidate", "BOOLEAN"),
        ("layer3_candidate", "BOOLEAN"),
        ("layer1_reasons", "VARCHAR"),
        ("layer2_reasons", "VARCHAR"),
        ("layer3_reasons", "VARCHAR"),
        ("layer1_signal_count", "BIGINT"),
        ("layer2_signal_count", "BIGINT"),
        ("layer3_signal_count", "BIGINT"),
        ("classification_version", "VARCHAR"),
        ("classification_computed_at", "TIMESTAMP"),
        ("classification_provenance", "VARCHAR"),
    ]
    for col_name, col_type in col_definitions:
        if col_name not in existing_cols:
            con.execute(f"ALTER TABLE account_features ADD COLUMN {col_name} {col_type};")

    # 2. Vectorized Classification & Structured Evidence Generation
    # Uses pure SQL with parameters to avoid f-string escaping conflicts with JSON/struct braces
    sql = """
        CREATE OR REPLACE TEMP TABLE role_classification_results AS
        WITH signals_eval AS (
            SELECT
                account_number,
                -- Layer 1 Signals (Collector Candidate)
                (fan_in >= __T1_MIN_FAN_IN__) AS l1_s1,
                (incoming_txn_count >= __T1_MIN_IN_TX__) AS l1_s2,
                (incoming_volume >= __T1_MIN_IN_VOL__) AS l1_s3,
                (net_flow_delta > 0 OR fan_in > fan_out OR COALESCE(inflow_to_outflow_ratio, 1.0) >= __T1_MIN_RATIO__) AS l1_s4,

                -- Layer 2 Signals (Distributor Candidate)
                (fan_out >= __T2_MIN_FAN_OUT__) AS l2_s1,
                (outgoing_txn_count >= __T2_MIN_OUT_TX__) AS l2_s2,
                (outgoing_volume >= __T2_MIN_OUT_VOL__) AS l2_s3,
                (net_flow_delta < 0 OR fan_out > fan_in OR COALESCE(outflow_to_inflow_ratio, 1.0) >= __T2_MIN_RATIO__) AS l2_s4,

                -- Layer 3 Signals (Terminal / Cash-Out Candidate)
                -- Mode A: Terminal Accumulation Sink
                (incoming_volume >= __T3_SINK_VOL__ AND incoming_txn_count >= __T3_SINK_TX__ AND outgoing_txn_count <= __T3_SINK_MAX_OUT_TX__) AS l3_mode_a,
                -- Mode B: Automated Outflow Drain
                ((web_emulator_txn_count > 0 OR linux_script_txn_count > 0) AND outgoing_volume >= __T3_AUTO_VOL__ AND outgoing_txn_count >= __T3_AUTO_TX__ AND (outgoing_volume >= incoming_volume OR outgoing_txn_count >= incoming_txn_count)) AS l3_mode_b,
                -- Mode C: Concentrated IP Sink Node
                (top_ip_transaction_ratio >= __T3_IP_RATIO__ AND incoming_volume >= __T3_IP_VOL__ AND outgoing_txn_count <= __T3_IP_MAX_OUT_TX__) AS l3_mode_c,

                -- Raw metrics for structured evidence
                fan_in,
                fan_out,
                incoming_txn_count,
                outgoing_txn_count,
                incoming_volume,
                outgoing_volume,
                net_flow_delta,
                inflow_to_outflow_ratio,
                outflow_to_inflow_ratio,
                web_emulator_txn_count,
                linux_script_txn_count,
                top_ip_transaction_ratio,
                top_ip_transaction_count
            FROM account_features
        ),
        candidates_classified AS (
            SELECT
                account_number,
                -- Layer 1 Candidate Decision (Requires core aggregation + minimum signal threshold)
                (l1_s1 AND l1_s2 AND l1_s3 AND (CASE WHEN l1_s1 THEN 1 ELSE 0 END + CASE WHEN l1_s2 THEN 1 ELSE 0 END + CASE WHEN l1_s3 THEN 1 ELSE 0 END + CASE WHEN l1_s4 THEN 1 ELSE 0 END) >= __T1_MIN_SIGNALS__) AS is_layer1,
                
                -- Layer 2 Candidate Decision (Requires core distribution + minimum signal threshold)
                (l2_s1 AND l2_s2 AND l2_s3 AND (CASE WHEN l2_s1 THEN 1 ELSE 0 END + CASE WHEN l2_s2 THEN 1 ELSE 0 END + CASE WHEN l2_s3 THEN 1 ELSE 0 END + CASE WHEN l2_s4 THEN 1 ELSE 0 END) >= __T2_MIN_SIGNALS__) AS is_layer2,
                
                -- Layer 3 Candidate Decision (Requires verified terminal structural pattern)
                (l3_mode_a OR l3_mode_b OR l3_mode_c) AS is_layer3,

                -- Signal flags & raw metrics
                l1_s1, l1_s2, l1_s3, l1_s4,
                l2_s1, l2_s2, l2_s3, l2_s4,
                l3_mode_a, l3_mode_b, l3_mode_c,
                fan_in, fan_out, incoming_txn_count, outgoing_txn_count,
                incoming_volume, outgoing_volume, net_flow_delta,
                inflow_to_outflow_ratio, outflow_to_inflow_ratio,
                web_emulator_txn_count, linux_script_txn_count,
                top_ip_transaction_ratio, top_ip_transaction_count
            FROM signals_eval
        )
        SELECT
            account_number,
            is_layer1 AS layer1_candidate,
            is_layer2 AS layer2_candidate,
            is_layer3 AS layer3_candidate,
            
            -- Structured Layer 1 Reasons
            CASE WHEN is_layer1 THEN
                to_json(list_filter([
                    CASE WHEN l1_s1 THEN {'code': 'HIGH_FAN_IN', 'observed_value': CAST(fan_in AS VARCHAR), 'threshold': '__T1_MIN_FAN_IN__', 'description': fan_in || ' unique sender accounts transferred funds into this account.'} ELSE NULL END,
                    CASE WHEN l1_s2 THEN {'code': 'HIGH_INBOUND_TRANSACTION_COUNT', 'observed_value': CAST(incoming_txn_count AS VARCHAR), 'threshold': '__T1_MIN_IN_TX__', 'description': incoming_txn_count || ' inbound transactions were observed.'} ELSE NULL END,
                    CASE WHEN l1_s3 THEN {'code': 'HIGH_INBOUND_VOLUME', 'observed_value': CAST(incoming_volume AS VARCHAR), 'threshold': '__T1_MIN_IN_VOL__', 'description': 'Observed inbound transaction volume of INR ' || CAST(incoming_volume AS VARCHAR) || ' exceeding threshold of INR __T1_MIN_IN_VOL__.'} ELSE NULL END,
                    CASE WHEN l1_s4 THEN {'code': 'INBOUND_FLOW_DOMINANCE', 'observed_value': CAST(ROUND(COALESCE(inflow_to_outflow_ratio, 1.0), 2) AS VARCHAR), 'threshold': '__T1_MIN_RATIO__', 'description': 'Inbound transaction volume (INR ' || CAST(incoming_volume AS VARCHAR) || ') or sender count (' || fan_in || ') exceeds outbound activity.'} ELSE NULL END
                ], x -> x IS NOT NULL))
            ELSE '[]' END AS layer1_reasons,
            
            CASE WHEN is_layer1 THEN
                (CASE WHEN l1_s1 THEN 1 ELSE 0 END + CASE WHEN l1_s2 THEN 1 ELSE 0 END + CASE WHEN l1_s3 THEN 1 ELSE 0 END + CASE WHEN l1_s4 THEN 1 ELSE 0 END)
            ELSE 0 END AS layer1_signal_count,

            -- Structured Layer 2 Reasons
            CASE WHEN is_layer2 THEN
                to_json(list_filter([
                    CASE WHEN l2_s1 THEN {'code': 'HIGH_FAN_OUT', 'observed_value': CAST(fan_out AS VARCHAR), 'threshold': '__T2_MIN_FAN_OUT__', 'description': fan_out || ' unique receiver accounts received funds from this account.'} ELSE NULL END,
                    CASE WHEN l2_s2 THEN {'code': 'HIGH_OUTBOUND_TRANSACTION_COUNT', 'observed_value': CAST(outgoing_txn_count AS VARCHAR), 'threshold': '__T2_MIN_OUT_TX__', 'description': outgoing_txn_count || ' outbound transactions were observed.'} ELSE NULL END,
                    CASE WHEN l2_s3 THEN {'code': 'HIGH_OUTBOUND_VOLUME', 'observed_value': CAST(outgoing_volume AS VARCHAR), 'threshold': '__T2_MIN_OUT_VOL__', 'description': 'Observed outbound transaction volume of INR ' || CAST(outgoing_volume AS VARCHAR) || ' exceeding threshold of INR __T2_MIN_OUT_VOL__.'} ELSE NULL END,
                    CASE WHEN l2_s4 THEN {'code': 'OUTBOUND_FLOW_DOMINANCE', 'observed_value': CAST(ROUND(COALESCE(outflow_to_inflow_ratio, 1.0), 2) AS VARCHAR), 'threshold': '__T2_MIN_RATIO__', 'description': 'Outbound transaction volume (INR ' || CAST(outgoing_volume AS VARCHAR) || ') or receiver count (' || fan_out || ') exceeds inbound activity.'} ELSE NULL END
                ], x -> x IS NOT NULL))
            ELSE '[]' END AS layer2_reasons,

            CASE WHEN is_layer2 THEN
                (CASE WHEN l2_s1 THEN 1 ELSE 0 END + CASE WHEN l2_s2 THEN 1 ELSE 0 END + CASE WHEN l2_s3 THEN 1 ELSE 0 END + CASE WHEN l2_s4 THEN 1 ELSE 0 END)
            ELSE 0 END AS layer2_signal_count,

            -- Structured Layer 3 Reasons
            CASE WHEN is_layer3 THEN
                to_json(list_filter([
                    CASE WHEN l3_mode_a THEN {'code': 'TERMINAL_FLOW_SINK', 'observed_value': CAST(incoming_volume AS VARCHAR), 'threshold': '__T3_SINK_VOL__', 'description': 'Account accumulated INR ' || CAST(incoming_volume AS VARCHAR) || ' across ' || incoming_txn_count || ' inbound transactions with zero observed outbound disbursement.'} ELSE NULL END,
                    CASE WHEN l3_mode_a THEN {'code': 'ZERO_OUTBOUND_DISBURSEMENT', 'observed_value': '0', 'threshold': '__T3_SINK_MAX_OUT_TX__', 'description': 'No outbound transactions were observed across the entire dataset.'} ELSE NULL END,
                    CASE WHEN l3_mode_b THEN {'code': 'AUTOMATION_DEVICE_ACTIVITY', 'observed_value': CAST((web_emulator_txn_count + linux_script_txn_count) AS VARCHAR), 'threshold': '1', 'description': 'Observed ' || (web_emulator_txn_count + linux_script_txn_count) || ' transactions originating from automated device environment.'} ELSE NULL END,
                    CASE WHEN l3_mode_b THEN {'code': 'HIGH_OUTBOUND_DISBURSEMENT', 'observed_value': CAST(outgoing_volume AS VARCHAR), 'threshold': '__T3_AUTO_VOL__', 'description': 'Outbound disbursement volume of INR ' || CAST(outgoing_volume AS VARCHAR) || ' executed under automated environment.'} ELSE NULL END,
                    CASE WHEN l3_mode_b THEN {'code': 'OUTBOUND_FLOW_DOMINANCE', 'observed_value': CAST(ROUND(COALESCE(outflow_to_inflow_ratio, 1.0), 2) AS VARCHAR), 'threshold': '1.0', 'description': 'Outbound funds movement dominates or equals inbound movement.'} ELSE NULL END,
                    CASE WHEN l3_mode_c THEN {'code': 'HIGH_IP_CONCENTRATION', 'observed_value': CAST(ROUND(top_ip_transaction_ratio * 100, 1) AS VARCHAR), 'threshold': '__T3_IP_RATIO_PCT__', 'description': ROUND(top_ip_transaction_ratio * 100, 1) || '% of transactions originated from a single IP address.'} ELSE NULL END,
                    CASE WHEN l3_mode_c AND NOT l3_mode_a THEN {'code': 'TERMINAL_FLOW_SINK', 'observed_value': CAST(incoming_volume AS VARCHAR), 'threshold': '__T3_IP_VOL__', 'description': 'Account accumulated INR ' || CAST(incoming_volume AS VARCHAR) || ' across ' || incoming_txn_count || ' inbound transactions with zero observed outbound disbursement.'} ELSE NULL END
                ], x -> x IS NOT NULL))
            ELSE '[]' END AS layer3_reasons,

            CASE WHEN is_layer3 THEN
                (CASE WHEN l3_mode_a THEN 2 ELSE 0 END + CASE WHEN l3_mode_b THEN 3 ELSE 0 END + CASE WHEN l3_mode_c AND NOT l3_mode_a THEN 2 ELSE 0 END)
            ELSE 0 END AS layer3_signal_count,

            '__VER__' AS classification_version,
            CURRENT_TIMESTAMP::TIMESTAMP AS classification_computed_at,
            '__PROV__' AS classification_provenance
        FROM candidates_classified;
    """

    replacements = {
        "__T1_MIN_FAN_IN__": str(t1.min_fan_in),
        "__T1_MIN_IN_TX__": str(t1.min_incoming_txn_count),
        "__T1_MIN_IN_VOL__": str(t1.min_incoming_volume),
        "__T1_MIN_RATIO__": str(t1.min_inflow_to_outflow_ratio),
        "__T1_MIN_SIGNALS__": str(t1.min_signals_required),
        "__T2_MIN_FAN_OUT__": str(t2.min_fan_out),
        "__T2_MIN_OUT_TX__": str(t2.min_outgoing_txn_count),
        "__T2_MIN_OUT_VOL__": str(t2.min_outgoing_volume),
        "__T2_MIN_RATIO__": str(t2.min_outflow_to_inflow_ratio),
        "__T2_MIN_SIGNALS__": str(t2.min_signals_required),
        "__T3_SINK_VOL__": str(t3.min_terminal_sink_incoming_volume),
        "__T3_SINK_TX__": str(t3.min_terminal_sink_incoming_tx),
        "__T3_SINK_MAX_OUT_TX__": str(t3.max_terminal_sink_outgoing_tx),
        "__T3_AUTO_VOL__": str(t3.min_automated_outgoing_volume),
        "__T3_AUTO_TX__": str(t3.min_automated_outgoing_tx),
        "__T3_IP_RATIO__": str(t3.min_top_ip_ratio),
        "__T3_IP_RATIO_PCT__": str(round(t3.min_top_ip_ratio * 100, 1)),
        "__T3_IP_VOL__": str(t3.min_ip_sink_incoming_volume),
        "__T3_IP_MAX_OUT_TX__": str(t3.max_ip_sink_outgoing_tx),
        "__VER__": ver,
        "__PROV__": prov,
    }

    for k, v in replacements.items():
        sql = sql.replace(k, v)

    con.execute(sql)

    # 3. Update account_features in-place
    con.execute("""
        UPDATE account_features
        SET
            layer1_candidate = r.layer1_candidate,
            layer2_candidate = r.layer2_candidate,
            layer3_candidate = r.layer3_candidate,
            layer1_reasons = r.layer1_reasons,
            layer2_reasons = r.layer2_reasons,
            layer3_reasons = r.layer3_reasons,
            layer1_signal_count = r.layer1_signal_count,
            layer2_signal_count = r.layer2_signal_count,
            layer3_signal_count = r.layer3_signal_count,
            classification_version = r.classification_version,
            classification_computed_at = r.classification_computed_at,
            classification_provenance = r.classification_provenance
        FROM role_classification_results r
        WHERE account_features.account_number = r.account_number;
    """)

    # Clean up temp table
    con.execute("DROP TABLE IF EXISTS role_classification_results;")

    t_end = time.perf_counter()
    duration_ms = round((t_end - t_start) * 1000, 2)

    # 4. Compute aggregate metrics
    counts = con.execute("""
        SELECT
            COUNT(*) AS total_accounts,
            SUM(CASE WHEN layer1_candidate THEN 1 ELSE 0 END) AS layer1_candidates,
            SUM(CASE WHEN layer2_candidate THEN 1 ELSE 0 END) AS layer2_candidates,
            SUM(CASE WHEN layer3_candidate THEN 1 ELSE 0 END) AS layer3_candidates,
            SUM(CASE WHEN layer1_candidate AND layer2_candidate THEN 1 ELSE 0 END) AS layer1_layer2_overlap,
            SUM(CASE WHEN layer1_candidate AND layer3_candidate THEN 1 ELSE 0 END) AS layer1_layer3_overlap,
            SUM(CASE WHEN layer2_candidate AND layer3_candidate THEN 1 ELSE 0 END) AS layer2_layer3_overlap,
            SUM(CASE WHEN layer1_candidate AND layer2_candidate AND layer3_candidate THEN 1 ELSE 0 END) AS all_three_overlap,
            SUM(CASE WHEN NOT layer1_candidate AND NOT layer2_candidate AND NOT layer3_candidate THEN 1 ELSE 0 END) AS no_role_accounts
        FROM account_features;
    """).fetchone()

    return {
        "total_accounts": counts[0],
        "layer1_candidates": counts[1],
        "layer2_candidates": counts[2],
        "layer3_candidates": counts[3],
        "layer1_layer2_overlap": counts[4],
        "layer1_layer3_overlap": counts[5],
        "layer2_layer3_overlap": counts[6],
        "all_three_overlap": counts[7],
        "no_role_accounts": counts[8],
        "classification_version": ver,
        "classification_provenance": prov,
        "duration_ms": duration_ms,
    }
