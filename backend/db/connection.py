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
        _dataset_path = target_path

    return _con
