"""
Deterministic Forensic Mule Risk Scoring Engine for Operation 'ABHEDYA-CHAKRA'
Step 5B: Explainable 0-100 Mule Risk Index Implementation.

Aggregates 6 independent evidence families into a bounded, reproducible 0-100 index:
  Family A: Flow Structure & Volume Scale (Max 20 pts)
  Family B: 3-15 Minute Pass-Through Velocity (Max 25 pts)
  Family C: Automation / Device / IP Behavior (Max 20 pts)
  Family D: Counterparty & Graph Network Structure (Max 15 pts)
  Family E: Transaction Behavior & Anomaly Profile (Max 10 pts)
  Family F: Step 4 Role Classification Support (Max 10 pts)
  Total Max = 100.0 pts.

Four Risk Bands:
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
    Computes deterministic 0-100 Mule Risk Index for all accounts in account_features.
    Executes vectorized SQL across all 24,873 account records in milliseconds.
    Updates account_features in-place with risk score, band, reasons, and family breakdowns.
    Returns the total number of accounts scored.
    """
    t_start = time.perf_counter()

    # 1. Ensure required schema columns exist in account_features
    existing_cols = {d[0] for d in con.execute("DESCRIBE account_features").fetchall()}
    col_definitions = [
        ("mule_risk_index", "DOUBLE"),
        ("risk_band", "VARCHAR"),
        ("risk_reasons", "VARCHAR"),
        ("risk_family_scores", "VARCHAR"),
        ("risk_model_version", "VARCHAR"),
        ("risk_computed_at", "TIMESTAMP"),
        ("risk_provenance", "VARCHAR"),
    ]
    for col_name, col_type in col_definitions:
        if col_name not in existing_cols:
            con.execute(f"ALTER TABLE account_features ADD COLUMN {col_name} {col_type};")

    # 2. Vectorized SQL calculation with strict family caps and non-duplicative evidence
    cfg_flow = config.flow
    cfg_vel = config.velocity
    cfg_auto = config.automation
    cfg_net = config.network
    cfg_tx = config.transaction
    cfg_role = config.role_support
    ver = config.version
    prov = config.provenance

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
        family_eval AS (
            SELECT
                account_number,
                -- Family A: Flow Structure (Max {cfg_flow.max_family_points})
                -- A1: Volume Scale (0 to 10)
                CASE 
                    WHEN (in_vol + out_vol) >= {cfg_flow.vol_tier1} THEN 10.0
                    WHEN (in_vol + out_vol) >= {cfg_flow.vol_tier2} THEN 7.0
                    WHEN (in_vol + out_vol) >= {cfg_flow.vol_tier3} THEN 4.0
                    WHEN (in_vol + out_vol) >= {cfg_flow.vol_tier4} THEN 2.0
                    ELSE 0.0
                END AS score_flow_vol,
                -- A2: Transit Parity or Terminal Accumulation Sink (0 to 10)
                CASE 
                    WHEN in_vol > 0 AND out_vol > 0 AND (LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol)) >= {cfg_flow.balanced_transit_ratio_high} THEN 10.0
                    WHEN in_vol > 0 AND out_vol > 0 AND (LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol)) >= {cfg_flow.balanced_transit_ratio_mod} THEN 6.0
                    WHEN out_tx = 0 AND in_vol >= {cfg_flow.one_sided_sink_inflow} THEN 8.0
                    ELSE 0.0
                END AS score_flow_ratio,

                -- Family B: Velocity / Pass-Through (Max {cfg_vel.max_family_points})
                CASE 
                    WHEN pt_events >= 1 AND pt_out_tx >= {cfg_vel.min_qualifying_tx_for_full_bands} THEN
                        CASE
                            WHEN pt_ratio >= {cfg_vel.ratio_band_critical} THEN 25.0
                            WHEN pt_ratio >= {cfg_vel.ratio_band_high} THEN 20.0
                            WHEN pt_ratio >= {cfg_vel.ratio_band_elevated} THEN 15.0
                            WHEN pt_ratio >= {cfg_vel.ratio_band_moderate} THEN 8.0
                            ELSE 0.0
                        END
                    WHEN pt_events >= 1 AND pt_out_tx = 1 THEN
                        CASE
                            WHEN pt_ratio >= {cfg_vel.ratio_band_high} THEN {cfg_vel.single_event_high}
                            WHEN pt_ratio >= {cfg_vel.ratio_band_moderate} THEN {cfg_vel.single_event_mod}
                            ELSE 0.0
                        END
                    ELSE 0.0
                END AS score_velocity,

                -- Family C: Automation / Device / IP (Max {cfg_auto.max_family_points})
                -- C1: Automated Device Environment (0 to 14)
                CASE 
                    WHEN (emu_tx + scr_tx) >= {cfg_auto.heavy_automated_tx_count} OR ((in_tx + out_tx) > 0 AND ((emu_tx + scr_tx)::DOUBLE / (in_tx + out_tx)) >= {cfg_auto.heavy_automated_ratio}) THEN 14.0
                    WHEN (emu_tx + scr_tx) >= {cfg_auto.detected_automated_tx_count} THEN 8.0
                    ELSE 0.0
                END AS score_automation,
                -- C2: IP Concentration (0 to 6)
                CASE 
                    WHEN (in_tx + out_tx) >= 5 AND top_ip_r >= {cfg_auto.top_ip_ratio_high} THEN 6.0
                    WHEN (in_tx + out_tx) >= {cfg_auto.min_tx_for_ip_eval} AND top_ip_r >= {cfg_auto.top_ip_ratio_mod} THEN 3.0
                    ELSE 0.0
                END AS score_ip,

                -- Family D: Network Structure (Max {cfg_net.max_family_points})
                -- D1: Max Degree Dispersal/Consolidation (0 to 10)
                CASE 
                    WHEN GREATEST(f_in, f_out) >= {cfg_net.degree_tier1} THEN 10.0
                    WHEN GREATEST(f_in, f_out) >= {cfg_net.degree_tier2} THEN 7.0
                    WHEN GREATEST(f_in, f_out) >= {cfg_net.degree_tier3} THEN 4.0
                    WHEN GREATEST(f_in, f_out) >= {cfg_net.degree_tier4} THEN 2.0
                    ELSE 0.0
                END AS score_degree,
                -- D2: Network Asymmetry / Intermediary (0 to 5)
                CASE 
                    WHEN (f_in >= {cfg_net.asymmetry_major_min} AND f_out <= {cfg_net.asymmetry_minor_max}) OR (f_out >= {cfg_net.asymmetry_major_min} AND f_in <= {cfg_net.asymmetry_minor_max}) THEN {cfg_net.asymmetry_points}
                    WHEN f_in >= {cfg_net.multi_hop_connectivity_degree} AND f_out >= {cfg_net.multi_hop_connectivity_degree} THEN {cfg_net.multi_hop_points}
                    ELSE 0.0
                END AS score_asymmetry,

                -- Family E: Transaction Behavior & Anomaly (Max {cfg_tx.max_family_points})
                -- E1: Night activity (0 to 5)
                CASE 
                    WHEN night_tx >= {cfg_tx.night_tx_heavy_count} AND (in_tx + out_tx) > 0 AND (night_tx::DOUBLE / (in_tx + out_tx)) >= {cfg_tx.night_tx_heavy_ratio} THEN {cfg_tx.night_heavy_points}
                    WHEN night_tx >= {cfg_tx.night_detected_count} THEN {cfg_tx.night_detected_points}
                    ELSE 0.0
                END AS score_night,
                -- E2: Burst rate (0 to 5)
                CASE 
                    WHEN burst_rate >= {cfg_tx.burst_rate_high} THEN {cfg_tx.burst_points_high}
                    WHEN burst_rate >= {cfg_tx.burst_rate_mod} THEN {cfg_tx.burst_points_mod}
                    ELSE 0.0
                END AS score_burst,

                -- Family F: Role Support (Max {cfg_role.max_family_points})
                LEAST({cfg_role.max_family_points}, (
                    CASE WHEN l1 THEN {cfg_role.points_per_candidate_role} ELSE 0.0 END +
                    CASE WHEN l2 THEN {cfg_role.points_per_candidate_role} ELSE 0.0 END +
                    CASE WHEN l3 THEN {cfg_role.points_per_candidate_role} ELSE 0.0 END
                )) AS score_role,

                -- Pass raw metrics for structured reason generation
                in_vol, out_vol, in_tx, out_tx, f_in, f_out, pt_ratio, pt_events, pt_out_tx,
                emu_tx, scr_tx, top_ip_r, night_tx, burst_rate, l1, l2, l3
            FROM base_eval
        ),
        capped_eval AS (
            SELECT
                account_number,
                ROUND(LEAST({cfg_flow.max_family_points}, score_flow_vol + score_flow_ratio), 1) AS fam_flow,
                ROUND(LEAST({cfg_vel.max_family_points}, score_velocity), 1) AS fam_vel,
                ROUND(LEAST({cfg_auto.max_family_points}, score_automation + score_ip), 1) AS fam_auto,
                ROUND(LEAST({cfg_net.max_family_points}, score_degree + score_asymmetry), 1) AS fam_net,
                ROUND(LEAST({cfg_tx.max_family_points}, score_night + score_burst), 1) AS fam_tx,
                ROUND(LEAST({cfg_role.max_family_points}, score_role), 1) AS fam_role,
                
                score_flow_vol, score_flow_ratio, score_velocity,
                score_automation, score_ip, score_degree, score_asymmetry,
                score_night, score_burst, score_role,

                in_vol, out_vol, in_tx, out_tx, f_in, f_out, pt_ratio, pt_events, pt_out_tx,
                emu_tx, scr_tx, top_ip_r, night_tx, burst_rate, l1, l2, l3
            FROM family_eval
        ),
        total_eval AS (
            SELECT
                account_number,
                ROUND(LEAST(100.0, GREATEST(0.0, fam_flow + fam_vel + fam_auto + fam_net + fam_tx + fam_role)), 1) AS total_score,
                fam_flow, fam_vel, fam_auto, fam_net, fam_tx, fam_role,
                
                score_flow_vol, score_flow_ratio, score_velocity,
                score_automation, score_ip, score_degree, score_asymmetry,
                score_night, score_burst, score_role,

                in_vol, out_vol, in_tx, out_tx, f_in, f_out, pt_ratio, pt_events, pt_out_tx,
                emu_tx, scr_tx, top_ip_r, night_tx, burst_rate, l1, l2, l3
            FROM capped_eval
        )
        SELECT
            account_number,
            total_score AS mule_risk_index,
            CASE
                WHEN total_score >= 75.0 THEN 'VERY_HIGH'
                WHEN total_score >= 50.0 THEN 'HIGH'
                WHEN total_score >= 25.0 THEN 'MODERATE'
                ELSE 'LOW'
            END AS risk_band,

            -- Structured Family Breakdown JSON
            to_json({{
                'FLOW_STRUCTURE': fam_flow,
                'VELOCITY': fam_vel,
                'AUTOMATION': fam_auto,
                'NETWORK_STRUCTURE': fam_net,
                'TRANSACTION_BEHAVIOR': fam_tx,
                'ROLE_SUPPORT': fam_role
            }}) AS risk_family_scores,

            -- Structured Explainable Reasons JSON
            to_json(list_filter([
                -- Flow Reasons
                CASE 
                    WHEN score_flow_vol >= 4.0 THEN 
                        {{'code': 'HIGH_MONETARY_THROUGHPUT', 'family': 'FLOW_STRUCTURE', 'points': score_flow_vol, 'observed_value': CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR), 'threshold': '{cfg_flow.vol_tier3}', 'description': 'Account conducted total transaction volume of INR ' || CAST(ROUND(in_vol + out_vol, 2) AS VARCHAR) || '.'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN score_flow_ratio >= 6.0 AND in_vol > 0 AND out_vol > 0 THEN 
                        {{'code': 'BALANCED_TRANSIT_FLOW', 'family': 'FLOW_STRUCTURE', 'points': score_flow_ratio, 'observed_value': CAST(ROUND(LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol), 2) AS VARCHAR), 'threshold': '{cfg_flow.balanced_transit_ratio_mod}', 'description': 'Observed balanced inflow-to-outflow transit parity (ratio ' || CAST(ROUND(LEAST(in_vol, out_vol) / GREATEST(in_vol, out_vol), 2) AS VARCHAR) || ').'}}
                    WHEN score_flow_ratio >= 8.0 AND out_tx = 0 THEN
                        {{'code': 'TERMINAL_ACCUMULATION_SINK', 'family': 'FLOW_STRUCTURE', 'points': score_flow_ratio, 'observed_value': CAST(ROUND(in_vol, 2) AS VARCHAR), 'threshold': '{cfg_flow.one_sided_sink_inflow}', 'description': 'Inflow absorption with zero observed outbound disbursement.'}}
                    ELSE NULL 
                END,

                -- Velocity Reasons
                CASE 
                    WHEN score_velocity >= 20.0 THEN 
                        {{'code': 'CRITICAL_PASS_THROUGH_VELOCITY', 'family': 'VELOCITY', 'points': score_velocity, 'observed_value': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR), 'threshold': '85.0', 'description': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR) || '% of incoming funds drained within 3-15 minute window across ' || pt_out_tx || ' outgoing transactions.'}}
                    WHEN score_velocity >= 8.0 THEN 
                        {{'code': 'ELEVATED_PASS_THROUGH_VELOCITY', 'family': 'VELOCITY', 'points': score_velocity, 'observed_value': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR), 'threshold': '50.0', 'description': CAST(ROUND(pt_ratio * 100, 1) AS VARCHAR) || '% of incoming funds drained within 3-15 minute qualifying window.'}}
                    ELSE NULL 
                END,

                -- Automation & Device Reasons
                CASE 
                    WHEN score_automation >= 14.0 THEN 
                        {{'code': 'HEAVY_AUTOMATED_DEVICE_USAGE', 'family': 'AUTOMATION', 'points': score_automation, 'observed_value': CAST((emu_tx + scr_tx) AS VARCHAR), 'threshold': '{cfg_auto.heavy_automated_tx_count}', 'description': CAST((emu_tx + scr_tx) AS VARCHAR) || ' transactions conducted via automated environments (Web_Emulator / Linux_Script).'}}
                    WHEN score_automation >= 8.0 THEN 
                        {{'code': 'AUTOMATED_DEVICE_DETECTED', 'family': 'AUTOMATION', 'points': score_automation, 'observed_value': CAST((emu_tx + scr_tx) AS VARCHAR), 'threshold': '1', 'description': 'Observed transactions originating from automated device environment.'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN score_ip >= 3.0 THEN 
                        {{'code': 'HIGH_IP_CONCENTRATION', 'family': 'AUTOMATION', 'points': score_ip, 'observed_value': CAST(ROUND(top_ip_r * 100, 1) AS VARCHAR), 'threshold': '50.0', 'description': CAST(ROUND(top_ip_r * 100, 1) AS VARCHAR) || '% of transactions routed through a single IP address.'}}
                    ELSE NULL 
                END,

                -- Network Reasons
                CASE 
                    WHEN score_degree >= 7.0 THEN 
                        {{'code': 'EXTREME_COUNTERPARTY_DEGREE', 'family': 'NETWORK_STRUCTURE', 'points': score_degree, 'observed_value': CAST(GREATEST(f_in, f_out) AS VARCHAR), 'threshold': '50', 'description': 'Extensive connectivity with ' || GREATEST(f_in, f_out) || ' unique counterparties.'}}
                    WHEN score_degree >= 2.0 THEN 
                        {{'code': 'ELEVATED_COUNTERPARTY_DEGREE', 'family': 'NETWORK_STRUCTURE', 'points': score_degree, 'observed_value': CAST(GREATEST(f_in, f_out) AS VARCHAR), 'threshold': '10', 'description': 'Observed counterparty degree of ' || GREATEST(f_in, f_out) || ' entities.'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN score_asymmetry >= 5.0 THEN 
                        {{'code': 'ASYMMETRIC_FLOW_DISPERSAL', 'family': 'NETWORK_STRUCTURE', 'points': score_asymmetry, 'observed_value': CAST(f_in AS VARCHAR) || ' in, ' || CAST(f_out AS VARCHAR) || ' out', 'threshold': '10:2', 'description': 'Pronounced directional asymmetry in counterparty topology.'}}
                    WHEN score_asymmetry >= 3.0 THEN 
                        {{'code': 'MULTI_HOP_CONNECTIVITY', 'family': 'NETWORK_STRUCTURE', 'points': score_asymmetry, 'observed_value': CAST(f_in AS VARCHAR) || ' in, ' || CAST(f_out AS VARCHAR) || ' out', 'threshold': '5:5', 'description': 'Active bidirectional counterparty intermediary connectivity.'}}
                    ELSE NULL 
                END,

                -- Transaction Anomaly Reasons
                CASE 
                    WHEN score_night >= 2.0 THEN 
                        {{'code': 'TEMPORAL_OFF_HOURS_ACTIVITY', 'family': 'TRANSACTION_BEHAVIOR', 'points': score_night, 'observed_value': CAST(night_tx AS VARCHAR), 'threshold': '2', 'description': CAST(night_tx AS VARCHAR) || ' transactions executed during night hours (00:00 - 05:59).'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN score_burst >= 3.0 THEN 
                        {{'code': 'HIGH_BURST_FREQUENCY', 'family': 'TRANSACTION_BEHAVIOR', 'points': score_burst, 'observed_value': CAST(ROUND(burst_rate, 1) AS VARCHAR), 'threshold': '10.0', 'description': 'High burst rate averaging ' || CAST(ROUND(burst_rate, 1) AS VARCHAR) || ' transactions per active day.'}}
                    ELSE NULL 
                END,

                -- Role Support Reasons
                CASE 
                    WHEN l1 THEN 
                        {{'code': 'LAYER1_COLLECTOR_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 4.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 1 Collector Mule Candidate.'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN l2 THEN 
                        {{'code': 'LAYER2_DISTRIBUTOR_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 4.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 2 Distributor Mule Candidate.'}}
                    ELSE NULL 
                END,
                CASE 
                    WHEN l3 THEN 
                        {{'code': 'LAYER3_TERMINAL_ROLE_CANDIDATE', 'family': 'ROLE_SUPPORT', 'points': 4.0, 'observed_value': 'True', 'threshold': 'True', 'description': 'Verified Step 4 Layer 3 Terminal / Cash-Out Candidate.'}}
                    ELSE NULL 
                END
            ], x -> x IS NOT NULL)) AS risk_reasons,

            '{ver}' AS risk_model_version,
            CURRENT_TIMESTAMP::TIMESTAMP AS risk_computed_at,
            '{prov}' AS risk_provenance
        FROM total_eval;
    """

    con.execute(sql)

    # 3. Update account_features in-place
    con.execute("""
        UPDATE account_features
        SET
            mule_risk_index = r.mule_risk_index,
            risk_band = r.risk_band,
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
    Retrieves explainable 0-100 Mule Risk Index for a single account.
    Returns None if account is not found in feature store.
    """
    cursor = con.cursor()
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

    acc, index, band, ver, prov, comp_at, family_scores_raw, reasons_raw = row

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
        risk_band=band or "LOW",
        risk_model_version=ver or "v1",
        risk_provenance=prov or "DERIVED",
        risk_computed_at=comp_at,
        risk_family_scores=family_scores,
        risk_reasons=reasons,
    )
