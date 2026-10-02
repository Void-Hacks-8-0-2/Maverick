"""
Database Connection & Data Access Layer for Operation 'ABHEDYA-CHAKRA'
Centralized DuckDB access over 2,000,000-row production dataset.
"""

import os
from pathlib import Path
from typing import Optional
import duckdb

_con: Optional[duckdb.DuckDBPyConnection] = None
_dataset_path: Optional[str] = None


def get_project_root() -> Path:
    # Anchor to project root (contains 'data' directory)
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "data").exists():
            return current
        current = current.parent
    return Path.cwd()


def get_dataset_path() -> Path:
    # Authoritative production dataset: 2,000,000-row CSV
    env_path = os.getenv("ABHEDYA_DATASET_PATH", "data/VoidHacks8_MuleAccount_2M_Transactions.csv")
    path = Path(env_path)
    if not path.is_absolute():
        path = (get_project_root() / path).resolve()
    return path


def get_db() -> duckdb.DuckDBPyConnection:
    global _con, _dataset_path
    target_path = str(get_dataset_path())

    if _con is None or _dataset_path != target_path:
        if not Path(target_path).exists():
            raise FileNotFoundError(
                f"Configured production dataset file not found at: {target_path}. "
                "Operation Abhedya-Chakra requires data/VoidHacks8_MuleAccount_2M_Transactions.csv."
            )

        # In-memory DuckDB connection with high-performance table & index materialization
        _con = duckdb.connect(database=":memory:", read_only=False)
        sql_path = target_path.replace("\\", "/")
        
        if sql_path.endswith(".csv"):
            _con.execute(f"CREATE OR REPLACE TABLE transactions AS SELECT * FROM read_csv('{sql_path}', header=true)")
        elif sql_path.endswith(".parquet"):
            _con.execute(f"CREATE OR REPLACE TABLE transactions AS SELECT * FROM read_parquet('{sql_path}')")
        else:
            raise ValueError(f"Unsupported dataset format: {sql_path}")

        # Materialize b-tree indexes for real-time sub-millisecond forensics & graph queries
        _con.execute("CREATE INDEX IF NOT EXISTS idx_sender_account ON transactions(Sender_Account)")
        _con.execute("CREATE INDEX IF NOT EXISTS idx_receiver_account ON transactions(Receiver_Account)")
        _con.execute("CREATE INDEX IF NOT EXISTS idx_transaction_id ON transactions(Transaction_ID)")
        _con.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(Timestamp)")
        
        # Step 2: Materialize Tier 2 analytical accounts dimension & Tier 3 feature store
        init_analytical_tier(_con)
        
        _dataset_path = target_path

    return _con.cursor()


def init_analytical_tier(con: duckdb.DuckDBPyConnection) -> None:
    """
    Materializes the Tier 2 analytical dimension (accounts_dimension)
    representing the union of all senders and receivers with pre-aggregated flow metrics,
    and initializes Tier 3 feature store schema (account_features).
    """
    con.execute("""
        CREATE OR REPLACE TABLE accounts_dimension AS
        WITH entity_tx AS (
            SELECT Sender_Account AS acc, Receiver_Account AS cp, Sender_IFSC AS ifsc, IP_Address AS ip, Device_Type AS dev, Payment_Mode AS pm, Timestamp AS ts, Amount AS amt, 1 AS is_out, 0 AS is_in FROM transactions
            UNION ALL
            SELECT Receiver_Account AS acc, Sender_Account AS cp, Receiver_IFSC AS ifsc, IP_Address AS ip, Device_Type AS dev, Payment_Mode AS pm, Timestamp AS ts, Amount AS amt, 0 AS is_out, 1 AS is_in FROM transactions
        )
        SELECT 
            acc AS account_number,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS total_inflow,
            ROUND(COALESCE(SUM(CASE WHEN is_out = 1 THEN amt ELSE 0.0 END), 0.0), 2) AS total_outflow,
            ROUND(COALESCE(SUM(CASE WHEN is_in = 1 THEN amt ELSE -amt END), 0.0), 2) AS net_flow_delta,
            CAST(SUM(is_in) AS BIGINT) AS incoming_txn_count,
            CAST(SUM(is_out) AS BIGINT) AS outgoing_txn_count,
            CAST(COUNT(*) AS BIGINT) AS transaction_count,
            CAST(COUNT(DISTINCT CASE WHEN is_in = 1 THEN cp END) AS BIGINT) AS unique_senders,
            CAST(COUNT(DISTINCT CASE WHEN is_out = 1 THEN cp END) AS BIGINT) AS unique_receivers,
            CAST(COUNT(DISTINCT cp) AS BIGINT) AS counterparty_count,
            MIN(ts) AS first_seen_timestamp,
            MAX(ts) AS last_seen_timestamp,
            CAST(COUNT(DISTINCT CASE WHEN is_out = 1 THEN ifsc END) AS BIGINT) AS sender_ifsc_count,
            CAST(COUNT(DISTINCT CASE WHEN is_in = 1 THEN ifsc END) AS BIGINT) AS receiver_ifsc_count,
            CAST(COUNT(DISTINCT ip) AS BIGINT) AS unique_ip_count,
            CAST(COUNT(DISTINCT dev) AS BIGINT) AS unique_device_count,
            CAST(COUNT(DISTINCT pm) AS BIGINT) AS unique_payment_mode_count,
            'DERIVED' AS provenance
        FROM entity_tx
        GROUP BY acc
    """)
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_acc_number ON accounts_dimension(account_number)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_dim_tx_count ON accounts_dimension(transaction_count)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_dim_inflow ON accounts_dimension(total_inflow)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_dim_outflow ON accounts_dimension(total_outflow)")

    from backend.features.store import init_feature_store
    init_feature_store(con, populate=True)

