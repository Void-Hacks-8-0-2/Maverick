"""
Feature Store Management & Lifecycle for Operation 'ABHEDYA-CHAKRA'
"""

import duckdb
from backend.features.models import AccountFeatures
from backend.features.behavioral import compute_account_features, get_account_features


def init_feature_store(con: duckdb.DuckDBPyConnection, populate: bool = True) -> int:
    """
    Initializes and populates the account_features store.
    If populate=True, computes all deterministic behavioral features across the dataset.
    Returns the number of feature records populated.
    """
    if populate:
        return compute_account_features(con)
    return 0


# Backwards compatibility alias for tests
def init_feature_store_schema(con: duckdb.DuckDBPyConnection) -> None:
    compute_account_features(con)
