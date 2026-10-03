"""
Syndicate Predictor for Operation 'ABHEDYA-CHAKRA'
Base v0.4: Deterministic Evaluator Prediction Layer.

DERIVES predicted_mule_candidate based strictly on observable, verified forensic evidence:
Non-victim nodes participating in verified connected:
Victim/Source -> Collector -> Pass-Through Distributor -> Terminal
multi-hop chains.

PRESERVES EXISTING INVESTIGATIVE CLASSIFICATIONS (L1, L2, L3, Two-Axis Risk).
NOT "confirmed mule", NOT "criminal", NOT ground truth.
"""

from typing import Dict, Any, Optional
import duckdb


def compute_syndicate_predictions(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """
    Computes deterministic evaluator prediction status (predicted_mule_candidate)
    for all accounts in account_features.

    Updates account_features in-place:
    - predicted_mule_candidate (BOOLEAN)
    - syndicate_stage (VARCHAR)
    - syndicate_evidence (JSON)

    Pure vectorized DuckDB execution -- no row-by-row Python iteration.
    """
    # 1. Ensure required schema columns exist in account_features
    existing_cols = {d[0] for d in con.execute("DESCRIBE account_features").fetchall()}
    col_definitions = [
        ("predicted_mule_candidate", "BOOLEAN DEFAULT false"),
        ("syndicate_stage", "VARCHAR DEFAULT NULL"),
        ("syndicate_evidence", "JSON DEFAULT '{}'"),
    ]
    for col_name, col_type in col_definitions:
        if col_name not in existing_cols:
            con.execute(f"ALTER TABLE account_features ADD COLUMN {col_name} {col_type};")

    # 2. Materialize the verified multi-hop syndicate connected chains
    # Reuses existing pass-through velocity detection and terminal automation evidence
    sql_detect = """
        CREATE OR REPLACE TEMP TABLE syndicate_predictions_temp AS
        WITH pt_distributors AS (
            SELECT account_number FROM account_features WHERE pass_through_candidate = true
        ),
        stage1_links AS (
            SELECT DISTINCT t.Sender_Account AS collector, t.Receiver_Account AS distributor
            FROM transactions t
            JOIN pt_distributors p ON t.Receiver_Account = p.account_number
        ),
        stage2_links AS (
            SELECT DISTINCT t.Sender_Account AS distributor, t.Receiver_Account AS terminal
            FROM transactions t
            JOIN pt_distributors p ON t.Sender_Account = p.account_number
            JOIN account_features f ON t.Receiver_Account = f.account_number AND f.layer3_candidate = true
        ),
        connected_chains AS (
            SELECT s1.collector, s1.distributor, s2.terminal
            FROM stage1_links s1
            JOIN stage2_links s2 ON s1.distributor = s2.distributor
        ),
        collectors AS (SELECT DISTINCT collector AS acc FROM connected_chains),
        distributors AS (SELECT DISTINCT distributor AS acc FROM connected_chains),
        terminals AS (SELECT DISTINCT terminal AS acc FROM connected_chains),
        all_syndicate_nodes AS (
            SELECT acc, 'STAGE_1_COLLECTOR' AS stage FROM collectors
            UNION ALL
            SELECT acc, 'STAGE_2_DISTRIBUTOR' AS stage FROM distributors
            UNION ALL
            SELECT acc, 'STAGE_3_TERMINAL' AS stage FROM terminals
        ),
        ranked_nodes AS (
            SELECT 
                acc,
                CASE 
                    WHEN COUNT(DISTINCT stage) > 1 THEN 'MULTI_STAGE'
                    ELSE MAX(stage)
                END AS assigned_stage,
                to_json(struct_pack(
                    stage := CASE WHEN COUNT(DISTINCT stage) > 1 THEN 'MULTI_STAGE' ELSE MAX(stage) END,
                    in_connected_chain := true,
                    policy := 'Forensic_Syndicate_Subgraph',
                    lineage := 'Victim/Source -> Collector -> Pass-Through Distributor -> Terminal Cash-Out'
                )) AS evidence_json
            FROM all_syndicate_nodes
            GROUP BY acc
        )
        SELECT acc, assigned_stage, evidence_json FROM ranked_nodes;
    """
    con.execute(sql_detect)

    # 3. Update account_features in-place
    # Default all accounts to non-predicted
    con.execute("""
        UPDATE account_features
        SET 
            predicted_mule_candidate = false,
            syndicate_stage = NULL,
            syndicate_evidence = '{}';
    """)

    # Set predicted status for accounts in the verified syndicate subgraph
    con.execute("""
        UPDATE account_features
        SET 
            predicted_mule_candidate = true,
            syndicate_stage = s.assigned_stage,
            syndicate_evidence = s.evidence_json
        FROM syndicate_predictions_temp s
        WHERE account_features.account_number = s.acc;
    """)

    # 4. Gather summary statistics
    total_predicted = con.execute(
        "SELECT COUNT(*) FROM account_features WHERE predicted_mule_candidate = true"
    ).fetchone()[0]

    stage_breakdown = con.execute("""
        SELECT COALESCE(syndicate_stage, 'NONE'), COUNT(*)
        FROM account_features
        WHERE predicted_mule_candidate = true
        GROUP BY 1
        ORDER BY 2 DESC
    """).fetchall()

    chain_metrics = con.execute("""
        WITH pt_distributors AS (
            SELECT account_number FROM account_features WHERE pass_through_candidate = true
        ),
        stage1_links AS (
            SELECT DISTINCT t.Sender_Account AS collector, t.Receiver_Account AS distributor
            FROM transactions t
            JOIN pt_distributors p ON t.Receiver_Account = p.account_number
        ),
        stage2_links AS (
            SELECT DISTINCT t.Sender_Account AS distributor, t.Receiver_Account AS terminal
            FROM transactions t
            JOIN pt_distributors p ON t.Sender_Account = p.account_number
            JOIN account_features f ON t.Receiver_Account = f.account_number AND f.layer3_candidate = true
        ),
        connected_chains AS (
            SELECT s1.collector, s1.distributor, s2.terminal
            FROM stage1_links s1
            JOIN stage2_links s2 ON s1.distributor = s2.distributor
        )
        SELECT 
            COUNT(DISTINCT collector),
            COUNT(DISTINCT distributor),
            COUNT(DISTINCT terminal),
            COUNT(*)
        FROM connected_chains;
    """).fetchone()

    # Clean up temp table
    con.execute("DROP TABLE IF EXISTS syndicate_predictions_temp;")

    return {
        "total_predicted_mules": total_predicted,
        "stages": dict(stage_breakdown),
        "chain_metrics": {
            "collectors_count": chain_metrics[0],
            "distributors_count": chain_metrics[1],
            "terminals_count": chain_metrics[2],
            "total_connected_paths": chain_metrics[3],
            "stage_node_sum": chain_metrics[0] + chain_metrics[1] + chain_metrics[2],
        }
    }


def get_account_prediction(con: duckdb.DuckDBPyConnection, account_number: str) -> Optional[Dict[str, Any]]:
    """
    Returns the prediction candidate status and explainable evidence for a single account.
    """
    row = con.execute("""
        SELECT predicted_mule_candidate, syndicate_stage, syndicate_evidence
        FROM account_features
        WHERE account_number = ?
    """, [account_number.strip()]).fetchone()

    if not row:
        return None

    return {
        "account_number": account_number,
        "predicted_mule_candidate": bool(row[0]),
        "syndicate_stage": row[1],
        "syndicate_evidence": row[2] if isinstance(row[2], dict) else {},
    }
