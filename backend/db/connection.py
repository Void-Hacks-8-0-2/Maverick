"""
Database Connection & Data Access Layer for Operation 'ABHEDYA-CHAKRA'
Centralized DuckDB access over Parquet dataset.
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
    env_path = os.getenv("ABHEDYA_DATASET_PATH", "data/extracted/transactions_recovered.parquet")
    path = Path(env_path)
    if not path.is_absolute():
        path = (get_project_root() / path).resolve()
    return path


def get_db() -> duckdb.DuckDBPyConnection:
    global _con, _dataset_path
    target_path = str(get_dataset_path())

    if _con is None or _dataset_path != target_path:
        if not Path(target_path).exists():
            raise FileNotFoundError(f"Configured dataset Parquet file not found at: {target_path}")

        # In-memory DuckDB connection with view abstraction
        _con = duckdb.connect(database=":memory:", read_only=False)
        # Create standardized 'transactions' view pointing to the analytical Parquet
        # Convert path to forward slashes for DuckDB SQL compatibility
        sql_path = target_path.replace("\\", "/")
        _con.execute(f"CREATE OR REPLACE VIEW transactions AS SELECT * FROM read_parquet('{sql_path}')")
        _dataset_path = target_path

    return _con
