"""
Deterministic Forensic Mule Risk Scoring Engine for Operation 'ABHEDYA-CHAKRA'
Candidate B: Two-Axis Decoupled Forensic Risk Architecture.

Decouples risk evaluation into two independent dimensions:
  - Axis 1: Behavioral / Velocity Risk (0-100 pts)
      * Velocity / 3-15 Min Pass-Through (Max 40 pts)
      * Automation / Device & IP Profile (Max 30 pts)
      * Flow Parity / Transit Retention (Max 20 pts)
      * Burst & Temporal Anomaly (Max 10 pts)
  - Axis 2: Structural / Network Footprint Risk (0-100 pts)
      * Max Counterparty Degree Breadth (Max 35 pts)
      * Intermediary Conduit & Directional Asymmetry (Max 25 pts)
      * Monetary Volume Scale (Max 20 pts)
      * Forensic Role Candidate Evidence Support (Max 20 pts)

Composite Index:
  base_composite = 0.5 * behavioral_risk + 0.5 * structural_risk
  bonus = 10.0 if (behavioral_risk >= 50.0 AND structural_risk >= 50.0) else 0.0
  composite = min(100.0, base_composite + bonus)

Four Composite Risk Bands:
  0-24.99:   LOW
  25-49.99:  MODERATE
  50-74.99:  HIGH
  75-100.0:  VERY_HIGH

INVESTIGATIVE CANDIDATE INDICATORS ONLY -- NOT A STATEMENT OF CRIMINALITY OR LEGAL DETERMINATION.
"""

import json
import time
from typing import Optional, Dict, Any, List
import duckdb

from backend.detection.risk_thresholds import (
    MuleRiskModelConfig,
    DEFAULT_RISK_CONFIG,
)
from backend.detection.risk_models import (
    MuleRiskScore,
    RiskReason,
)


def compute_mule_risk_index(
    con: duckdb.DuckDBPyConnection,
    config: MuleRiskModelConfig = DEFAULT_RISK_CONFIG
) -> int:
    """
    Computes deterministic Two-Axis Forensic Risk scores for all accounts in account_features.
    Executes vectorized SQL across all 24,873 account records in milliseconds.
    Updates account_features in-place with structural risk, behavioral risk, composite index,
    risk band, investigative signals, reasons, and family breakdowns.
    Returns the total number of accounts scored.
    """
    t_start = time.perf_counter()

    # 1. Ensure required schema columns exist in account_features
    existing_cols = {d[0] for d in con.execute("DESCRIBE account_features").fetchall()}
    col_definitions = [
        ("mule_risk_index", "DOUBLE"),
        ("structural_risk_index", "DOUBLE"),
        ("behavioral_risk_index", "DOUBLE"),
        ("risk_band", "VARCHAR"),
        ("investigative_signal", "VARCHAR"),
        ("investigative_summary", "VARCHAR"),
        ("multi_modal_confirmation", "BOOLEAN"),
        ("risk_reasons", "VARCHAR"),
        ("risk_family_scores", "VARCHAR"),
        ("risk_model_version", "VARCHAR"),
        ("risk_computed_at", "TIMESTAMP"),
        ("risk_provenance", "VARCHAR"),
    ]
    for col_name, col_type in col_definitions:
        if col_name not in existing_cols:
            con.execute(f"ALTER TABLE account_features ADD COLUMN {col_name} {col_type};")

    ver = "v2_two_axis"
    prov = "DERIVED"

    # 2. Vectorized Two-Axis SQL Calculation
    sql = f"""
        CREATE OR REPLACE TEMP TABLE risk_score_results AS
        WITH base_eval AS (
            SELECT
                account_number,
                COALESCE(incoming_volume, 0.0) AS in_vol,
                COALESCE(outgoing_volume, 0.0) AS out_vol,
                COALESCE(incoming_txn_count, 0) AS in_tx,
                COALESCE(outgoing_txn_count, 0) AS out_tx,
                COALESCE(fan_in, 0) AS f_in,
                COALESCE(fan_out, 0) AS f_out,
                COALESCE(pass_through_ratio, 0.0) AS pt_ratio,
                COALESCE(pass_through_event_count, 0) AS pt_events,
                COALESCE(pass_through_outgoing_transaction_count, 0) AS pt_out_tx,
                COALESCE(web_emulator_txn_count, 0) AS emu_tx,
                COALESCE(linux_script_txn_count, 0) AS scr_tx,
                COALESCE(top_ip_transaction_ratio, 0.0) AS top_ip_r,
                COALESCE(night_transaction_count, 0) AS night_tx,
                COALESCE(transactions_per_active_day, 0.0) AS burst_rate,
                COALESCE(layer1_candidate, false) AS l1,
                COALESCE(layer2_candidate, false) AS l2,
                COALESCE(layer3_candidate, false) AS l3
            FROM account_features
        ),
        axis_eval AS (
            SELECT
                account_number,
                
                -- =================================================================
                -- AXIS 1: BEHAVIORAL RISK (Max 100)
                -- =================================================================
                -- 1. Velocity / 3-15 Minute Pass-Through (Max 40)
                CASE 
                    WHEN pt_events >= 1 AND pt_out_tx >= 2 THEN
                        CASE
                            WHEN pt_ratio >= 0.90 THEN 40.0
                            WHEN pt_ratio >= 0.70 THEN 30.0
                            WHEN pt_ratio >= 0.40 THEN 20.0
                            WHEN pt_ratio >= 0.20 THEN 10.0
                            ELSE 5.0
                        END
                    WHEN pt_events >= 1 AND pt_out_tx = 1 THEN
                        CASE
                            WHEN pt_ratio >= 0.80 THEN 15.0
                            WHEN pt_ratio >= 0.40 THEN 8.0
                            ELSE 0.0
                        END
                    ELSE 0.0
                END AS b_vel,

                -- 2. Automation / Device Environment & IP (Max 30)
                LEAST(30.0,
                    CASE 
                        WHEN (emu_tx + scr_tx) >= 2 OR ((in_tx + out_tx) > 0 AND ((emu_tx + scr_tx)::DOUBLE / (in_tx + out_tx)) >= 0.5) THEN 22.0
                        WHEN (emu_tx + scr_tx) >= 1 THEN 12.0
                        ELSE 0.0
                    END +
                    CASE 
                        WHEN (in_tx + out_tx) >= 5 AND top_ip_r >= 0.90 THEN 8.0
                        WHEN (in_tx + out_tx) >= 3 AND top_ip_r >= 0.75 THEN 4.0
                        ELSE 0.0
                    END
                ) AS b_auto,

                -- 3. Flow Parity / In-Out Balance (Max 20)
                CASE 
                    WHEN in_vol > 0 AND out_vol > 0 THEN
                        CASE
                            WHEN (LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol)) >= 0.85 THEN 20.0
                            WHEN (LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol)) >= 0.65 THEN 14.0
                            WHEN (LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol)) >= 0.45 THEN 8.0
                            ELSE 0.0
                        END
                    WHEN out_tx = 0 AND in_vol >= 150000.0 THEN 14.0
                    ELSE 0.0
                END AS b_parity,

                -- 4. Burst Rate & Off-Hours Anomaly (Max 10)
                LEAST(10.0,
                    CASE 
                        WHEN burst_rate >= 10.0 THEN 5.0
                        WHEN burst_rate >= 5.0 THEN 3.0
                        ELSE 0.0
                    END +
                    CASE 
                        WHEN (in_tx + out_tx) >= 5 AND (night_tx::DOUBLE / (in_tx + out_tx)) >= 0.30 THEN 5.0
                        WHEN night_tx >= 2 THEN 2.0
                        ELSE 0.0
                    END
                ) AS b_burst,

                -- =================================================================
                -- AXIS 2: STRUCTURAL RISK (Max 100)
                -- =================================================================
                -- 1. Max Degree Breadth (Max 35)
                CASE 
                    WHEN GREATEST(f_in, f_out) >= 100 THEN 35.0
                    WHEN GREATEST(f_in, f_out) >= 95 THEN 25.0
                    WHEN GREATEST(f_in, f_out) >= 75 THEN 15.0
                    WHEN GREATEST(f_in, f_out) >= 50 THEN 8.0
                    WHEN GREATEST(f_in, f_out) >= 20 THEN 4.0
                    ELSE 0.0
                END AS s_degree,

                -- 2. Intermediary Conduit & Directional Asymmetry (Max 25)
                CASE 
                    WHEN f_in >= 95 AND f_out >= 95 THEN 25.0
                    WHEN (f_in >= 50 AND f_out <= 5) OR (f_out >= 50 AND f_in <= 5) THEN 20.0
                    WHEN f_in >= 50 AND f_out >= 50 THEN 12.0
                    WHEN (f_in >= 20 AND f_out <= 3) OR (f_out >= 20 AND f_in <= 3) THEN 10.0
                    WHEN f_in >= 20 AND f_out >= 20 THEN 6.0
                    ELSE 0.0
                END AS s_intermediary,

                -- 3. Monetary Volume Scale (Max 20)
                CASE 
                    WHEN (in_vol + out_vol) >= 1000000.0 THEN 20.0
                    WHEN (in_vol + out_vol) >= 500000.0 THEN 14.0
                    WHEN (in_vol + out_vol) >= 250000.0 THEN 8.0
                    WHEN (in_vol + out_vol) >= 100000.0 THEN 4.0
                    ELSE 0.0
                END AS s_volume,

                -- 4. Role Evidence Support (Max 20)
                LEAST(20.0,
                    (CASE WHEN l1 THEN 10.0 ELSE 0.0 END) +
                    (CASE WHEN l2 THEN 10.0 ELSE 0.0 END) +
                    (CASE WHEN l3 THEN 10.0 ELSE 0.0 END)
                ) AS s_role,

                in_vol, out_vol, in_tx, out_tx, f_in, f_out, pt_ratio, pt_events, pt_out_tx,
                emu_tx, scr_tx, top_ip_r, night_tx, burst_rate, l1, l2, l3
            FROM base_eval
        ),
        composite_eval AS (
            SELECT
                account_number,
                ROUND(LEAST(100.0, b_vel + b_auto + b_parity + b_burst), 1) AS behavioral_risk_index,
                ROUND(LEAST(100.0, s_degree + s_intermediary + s_volume + s_role), 1) AS structural_risk_index,
                b_vel, b_auto, b_parity, b_burst,
                s_degree, s_intermediary, s_volume, s_role,
                in_vol, out_vol, in_tx, out_tx, f_in, f_out, pt_ratio, pt_events, pt_out_tx,
                emu_tx, scr_tx, top_ip_r, night_tx, burst_rate, l1, l2, l3
            FROM axis_eval
        ),
        final_scores AS (
            SELECT
                account_number,
                behavioral_risk_index,
                structural_risk_index,
                
                -- Multi-Modal Confirmation & Composite Bounded Formula
                (behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0) AS multi_modal_confirmation,
                ROUND(LEAST(100.0, 
                    0.5 * behavioral_risk_index + 0.5 * structural_risk_index + 
                    CASE WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 10.0 ELSE 0.0 END
                ), 1) AS mule_risk_index,

                -- Investigative Classification Signals
                CASE
                    WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 'MULTI-MODAL EVIDENCE'
                    WHEN structural_risk_index >= 50.0 AND behavioral_risk_index < 50.0 THEN 'ELEVATED STRUCTURAL INDICATORS'
                    WHEN behavioral_risk_index >= 50.0 AND structural_risk_index < 50.0 THEN 'ELEVATED BEHAVIORAL INDICATORS'
                    WHEN (0.5 * behavioral_risk_index + 0.5 * structural_risk_index) >= 35.0 THEN 'REVIEW REQUIRED'
                    ELSE 'LOW CURRENT INDICATOR'
                END AS investigative_signal,

                CASE
                    WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 'Independent structural and behavioral indicators are both elevated.'
                    WHEN structural_risk_index >= 50.0 AND behavioral_risk_index < 50.0 THEN 'Structural indicators elevated; behavioral indicators limited.'
                    WHEN behavioral_risk_index >= 50.0 AND structural_risk_index < 50.0 THEN 'Behavioral indicators elevated; structural footprint limited.'
                    ELSE 'Both indicators currently limited.'
                END AS investigative_summary,

                -- Composite Risk Band
                CASE
                    WHEN ROUND(LEAST(100.0, 
                        0.5 * behavioral_risk_index + 0.5 * structural_risk_index + 
                        CASE WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 10.0 ELSE 0.0 END
                    ), 1) >= 75.0 THEN 'VERY_HIGH'
                    WHEN ROUND(LEAST(100.0, 
                        0.5 * behavioral_risk_index + 0.5 * structural_risk_index + 
                        CASE WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 10.0 ELSE 0.0 END
                    ), 1) >= 50.0 THEN 'HIGH'
                    WHEN ROUND(LEAST(100.0, 
                        0.5 * behavioral_risk_index + 0.5 * structural_risk_index + 
                        CASE WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 10.0 ELSE 0.0 END
                    ), 1) >= 25.0 THEN 'MODERATE'
                    ELSE 'LOW'
                END AS risk_band,

                -- Sub-Component Evidence Breakdown JSON
                to_json({{
                    'VELOCITY': b_vel,
                    'AUTOMATION': b_auto,
                    'FLOW_PARITY': b_parity,
                    'BURST_TEMPORAL': b_burst,
                    'DEGREE': s_degree,
                    'INTERMEDIARY': s_intermediary,
                    'VOLUME_SCALE': s_volume,
                    'ROLE_EVIDENCE': s_role,
                    'BEHAVIORAL_TOTAL': behavioral_risk_index,
                    'STRUCTURAL_TOTAL': structural_risk_index,
                    'COMPOSITE_TOTAL': ROUND(LEAST(100.0, 
                        0.5 * behavioral_risk_index + 0.5 * structural_risk_index + 
                        CASE WHEN behavioral_risk_index >= 50.0 AND structural_risk_index >= 50.0 THEN 10.0 ELSE 0.0 END
                    ), 1)
                }}) AS risk_family_scores,

                -- Structured Explainable Reasons JSON
                to_json(list_filter([
                    -- Velocity Evidence
                    CASE 
                        WHEN b_vel >= 30.0 THEN 
                            {{'code': 'CRITICAL_PASS_THROUGH_VELOCITY', 'family': 'VELOCITY', 'points': b_vel, 'observed_value': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR), 'threshold': '70.0', 'description': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR) || '% of incoming funds drained within 3-15 minute window across ' || pt_out_tx || ' outgoing transactions.'}}
                        WHEN b_vel >= 10.0 THEN 
                            {{'code': 'ELEVATED_PASS_THROUGH_VELOCITY', 'family': 'VELOCITY', 'points': b_vel, 'observed_value': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR), 'threshold': '20.0', 'description': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR) || '% of incoming funds drained within 3-15 minute qualifying window.'}}
                        ELSE NULL 
                    END,

                    -- Automation Evidence
                    CASE 
                        WHEN b_auto >= 18.0 THEN 
                            {{'code': 'HEAVY_AUTOMATED_DEVICE_USAGE', 'family': 'AUTOMATION', 'points': b_auto, 'observed_value': CAST((emu_tx + scr_tx) AS VARCHAR), 'threshold': '2', 'description': CAST((emu_tx + scr_tx) AS VARCHAR) || ' transactions conducted via automated environments (Web_Emulator / Linux_Script).'}}
                        WHEN b_auto >= 10.0 THEN 
                            {{'code': 'AUTOMATED_DEVICE_DETECTED', 'family': 'AUTOMATION', 'points': b_auto, 'observed_value': CAST((emu_tx + scr_tx) AS VARCHAR), 'threshold': '1', 'description': 'Observed transactions originating from automated device environment.'}}
                        ELSE NULL 
                    END,

                    -- Flow Parity Evidence
                    CASE 
                        WHEN b_parity >= 14.0 AND in_vol > 0 AND out_vol > 0 THEN 
                            {{'code': 'BALANCED_TRANSIT_FLOW', 'family': 'FLOW_STRUCTURE', 'points': b_parity, 'observed_value': CAST(ROUND(LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol), 2) AS VARCHAR), 'threshold': '0.65', 'description': 'Observed balanced inflow-to-outflow transit parity (ratio ' || CAST(ROUND(LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol), 2) AS VARCHAR) || ').'}}
                        WHEN b_parity >= 14.0 AND out_tx = 0 THEN
                            {{'code': 'TERMINAL_ACCUMULATION_SINK', 'family': 'FLOW_STRUCTURE', 'points': b_parity, 'observed_value': CAST(ROUND(in_vol, 2) AS VARCHAR), 'threshold': '150000', 'description': 'Inflow absorption with zero observed outbound disbursement.'}}
                        ELSE NULL 
                    END,

                    -- Burst & Anomaly Evidence
                    CASE 
                        WHEN b_burst >= 5.0 THEN 
                            {{'code': 'HIGH_BURST_FREQUENCY', 'family': 'TRANSACTION_BEHAVIOR', 'points': b_burst, 'observed_value': CAST(ROUND(burst_rate, 1) AS VARCHAR), 'threshold': '5.0', 'description': 'High burst rate averaging ' || CAST(ROUND(burst_rate, 1) AS VARCHAR) || ' transactions per active day.'}}
                        ELSE NULL 
                    END,

                    -- Degree Breadth Evidence
                    CASE 
                        WHEN s_degree >= 25.0 THEN 
                            {{'code': 'EXTREME_COUNTERPARTY_DEGREE', 'family': 'NETWORK_STRUCTURE', 'points': s_degree, 'observed_value': CAST(GREATEST(f_in, f_out) AS VARCHAR), 'threshold': '95', 'description': 'Extensive counterparty reach with ' || GREATEST(f_in, f_out) || ' unique counterparty accounts.'}}
                        WHEN s_degree >= 8.0 THEN 
                            {{'code': 'ELEVATED_COUNTERPARTY_DEGREE', 'family': 'NETWORK_STRUCTURE', 'points': s_degree, 'observed_value': CAST(GREATEST(f_in, f_out) AS VARCHAR), 'threshold': '50', 'description': 'Observed counterparty degree of ' || GREATEST(f_in, f_out) || ' entities.'}}
                        ELSE NULL 
                    END,

                    -- Intermediary Topology Evidence
                    CASE 
                        WHEN s_intermediary >= 20.0 THEN 
                            {{'code': 'INTERMEDIARY_CONDUIT_TOPOLOGY', 'family': 'NETWORK_STRUCTURE', 'points': s_intermediary, 'observed_value': CAST(f_in AS VARCHAR) || ' in, ' || CAST(f_out AS VARCHAR) || ' out', 'threshold': '50:50', 'description': 'Active bidirectional counterparty intermediary / layering conduit.'}}
                        WHEN s_intermediary >= 10.0 THEN 
                            {{'code': 'ASYMMETRIC_FLOW_DISPERSAL', 'family': 'NETWORK_STRUCTURE', 'points': s_intermediary, 'observed_value': CAST(f_in AS VARCHAR) || ' in, ' || CAST(f_out AS VARCHAR) || ' out', 'threshold': '20:3', 'description': 'Pronounced directional asymmetry in counterparty topology.'}}
                        ELSE NULL 
                    END,

                    -- Monetary Scale Evidence
                    CASE 
                        WHEN s_volume >= 14.0 THEN 
                            {{'code': 'HIGH_MONETARY_THROUGHPUT', 'family': 'FLOW_STRUCTURE', 'points': s_volume, 'observed_value': CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR), 'threshold': '500000', 'description': 'Account conducted total transaction volume of INR ' || CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR) || '.'}}
                        WHEN s_volume >= 4.0 THEN 
                            {{'code': 'ELEVATED_MONETARY_VOLUME', 'family': 'FLOW_STRUCTURE', 'points': s_volume, 'observed_value': CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR), 'threshold': '100000', 'description': 'Account conducted total transaction volume of INR ' || CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR) || '.'}}
                        ELSE NULL 
                    END,

                    -- Role Candidate Evidence
                    CASE 
                        WHEN l1 THEN 
                            {{'code': 'LAYER1_COLLECTOR_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 10.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 1 Collector Mule Candidate.'}}
                        ELSE NULL 
                    END,
                    CASE 
                        WHEN l2 THEN 
                            {{'code': 'LAYER2_DISTRIBUTOR_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 10.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 2 Distributor Mule Candidate.'}}
                        ELSE NULL 
                    END,
                    CASE 
                        WHEN l3 THEN 
                            {{'code': 'LAYER3_TERMINAL_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 10.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 3 Terminal / Cash-Out Candidate.'}}
                        ELSE NULL 
                    END
                ], x -> x IS NOT NULL)) AS risk_reasons,

                '{ver}' AS risk_model_version,
                CURRENT_TIMESTAMP::TIMESTAMP AS risk_computed_at,
                '{prov}' AS risk_provenance
            FROM composite_eval
        )
        SELECT * FROM final_scores;
    """

    con.execute(sql)

    # 3. Update account_features in-place
    con.execute("""
        UPDATE account_features
        SET
            mule_risk_index = r.mule_risk_index,
            structural_risk_index = r.structural_risk_index,
            behavioral_risk_index = r.behavioral_risk_index,
            risk_band = r.risk_band,
            investigative_signal = r.investigative_signal,
            investigative_summary = r.investigative_summary,
            multi_modal_confirmation = r.multi_modal_confirmation,
            risk_reasons = r.risk_reasons,
            risk_family_scores = r.risk_family_scores,
            risk_model_version = r.risk_model_version,
            risk_computed_at = r.risk_computed_at,
            risk_provenance = r.risk_provenance
        FROM risk_score_results r
        WHERE account_features.account_number = r.account_number;
    """)

    con.execute("DROP TABLE IF EXISTS risk_score_results;")

    t_duration = round((time.perf_counter() - t_start) * 1000, 2)
    total_scored = con.execute("SELECT count(*) FROM account_features WHERE mule_risk_index IS NOT NULL").fetchone()[0]
    return total_scored


def get_account_risk(con: duckdb.DuckDBPyConnection, account_id: str) -> Optional[MuleRiskScore]:
    """
    Retrieves explainable Two-Axis Forensic Mule Risk Score for a single account.
    Returns None if account is not found in feature store.
    """
    cursor = con.cursor()
    try:
        cols_res = cursor.execute("PRAGMA table_info('account_features')").fetchall()
        cols = {row[1] for row in cols_res}
    except Exception:
        cols = set()

    has_two_axis = "structural_risk_index" in cols

    if has_two_axis:
        cursor.execute("""
            SELECT 
                account_number,
                mule_risk_index,
                risk_band,
                risk_model_version,
                risk_provenance,
                risk_computed_at,
                risk_family_scores,
                risk_reasons,
                COALESCE(structural_risk_index, 0.0),
                COALESCE(behavioral_risk_index, 0.0),
                COALESCE(investigative_signal, 'LOW CURRENT INDICATOR'),
                COALESCE(investigative_summary, ''),
                COALESCE(multi_modal_confirmation, false)
            FROM account_features
            WHERE account_number = ?
        """, [account_id.strip()])
    else:
        cursor.execute("""
            SELECT 
                account_number,
                mule_risk_index,
                risk_band,
                risk_model_version,
                risk_provenance,
                risk_computed_at,
                risk_family_scores,
                risk_reasons
            FROM account_features
            WHERE account_number = ?
        """, [account_id.strip()])

    row = cursor.fetchone()
    if not row or row[1] is None:
        return None

    if has_two_axis:
        (
            acc, index, band, ver, prov, comp_at, family_scores_raw, reasons_raw,
            s_risk, b_risk, inv_signal, inv_summary, mm_confirm
        ) = row
    else:
        (
            acc, index, band, ver, prov, comp_at, family_scores_raw, reasons_raw
        ) = row
        s_risk, b_risk = 0.0, float(index) if index else 0.0
        inv_signal = "LOW CURRENT INDICATOR"
        inv_summary = "Legacy single-axis score"
        mm_confirm = False

    # Parse family scores
    family_scores: Dict[str, float] = {}
    if family_scores_raw:
        try:
            family_scores = json.loads(family_scores_raw) if isinstance(family_scores_raw, str) else family_scores_raw
        except Exception:
            family_scores = {}

    # Parse reasons
    reasons: List[RiskReason] = []
    if reasons_raw:
        try:
            parsed = json.loads(reasons_raw) if isinstance(reasons_raw, str) else reasons_raw
            for r in parsed:
                reasons.append(RiskReason(**r))
        except Exception:
            reasons = []

    return MuleRiskScore(
        account_number=acc,
        risk_index=float(index),
        structural_risk_index=float(s_risk),
        behavioral_risk_index=float(b_risk),
        multi_modal_confirmation=bool(mm_confirm),
        investigative_signal=str(inv_signal),
        investigative_summary=str(inv_summary),
        risk_band=band or "LOW",
        risk_model_version=ver or "v2_two_axis",
        risk_provenance=prov or "DERIVED",
        risk_computed_at=comp_at,
        risk_family_scores=family_scores,
        risk_reasons=reasons,
    )
