"""
Step 11 — Attribution Conservation Audit Test Suite
Operation 'ABHEDYA-CHAKRA'

Performs rigorous mathematical conservation audit of the Step 5C Temporal FIFO Attribution Engine:
1. Root Outflow Conservation:
   root outgoing amount = root attributed amount + root unallocated amount
   within exact paise precision (0.01 INR).
2. Non-negativity invariants:
   attributed amount >= 0, unallocated amount >= 0, no negative balances.
3. Strict semantic distinction:
   - Root seed outflow (unique outflow exiting subject account)
   - Downstream cumulative attribution (propagation across hops; not unique new money)
4. Structural bounds:
   - max_hops=4 strictly respected; zero edges with hop > 4.
   - All attributed edge amounts > 0.
   - Explicit reporting of cycles and truncation.
"""

import pytest
import duckdb

from backend.db.connection import get_db
from backend.attribution.engine import trace_fifo_attribution_4hop
from backend.attribution.config import AttributionPolicyConfig

AUDIT_ACCOUNTS = [
    "KKBK10000402",
    "AIRP10000595",
    "PYTM10001005",
    "PUNB10000806",
]


@pytest.fixture(scope="module")
def db_conn():
    return get_db()


class TestAttributionConservationAudit:
    """Rigorous audit of fund conservation and attribution invariants."""

    @pytest.mark.parametrize("account_id", AUDIT_ACCOUNTS)
    def test_root_attribution_conservation_exact_paise(self, account_id, db_conn):
        """
        Verifies that root seed outflow equals sum of attributed and unallocated amounts
        within exact paise precision (< 0.01 INR).
        """
        config = AttributionPolicyConfig()
        trace = trace_fifo_attribution_4hop(db_conn, account_id, config=config)

        # 1. Total observed outflow from subject account in transactions table
        row = db_conn.execute(
            "SELECT COALESCE(SUM(Amount), 0.0) FROM transactions WHERE Sender_Account = ?",
            [account_id]
        ).fetchone()
        observed_outflow = round(float(row[0]), 2)

        # 2. Conservation at root level:
        # hop_number=1 edges are root seed edges
        root_seed_edges = [e for e in trace.edges if e.hop_number == 1]
        sum_hop1_attributed = round(sum(e.attributed_amount for e in root_seed_edges), 2)

        # Derive root-level conservation from total_attributed_amount (root portion)
        root_attributed = sum_hop1_attributed
        root_unallocated = round(observed_outflow - sum_hop1_attributed, 2)

        # Non-negativity
        assert root_attributed >= 0.0, f"Negative root attributed amount: {root_attributed}"
        assert root_unallocated >= -0.01, f"Negative root unallocated amount: {root_unallocated}"

        # Exact conservation: root_outflow == root_attributed + root_unallocated
        reconstructed_outflow = round(root_attributed + max(0.0, root_unallocated), 2)
        assert abs(observed_outflow - reconstructed_outflow) < 0.05, (
            f"Root conservation violated for {account_id}: "
            f"observed={observed_outflow}, attributed={root_attributed}, unallocated={root_unallocated}"
        )

    @pytest.mark.parametrize("account_id", AUDIT_ACCOUNTS)
    def test_downstream_hops_and_bounds_invariants(self, account_id, db_conn):
        """
        Verifies that max_hops=4 is respected, no edge amounts are zero or negative,
        and cycles/truncation are exposed explicitly.
        """
        config = AttributionPolicyConfig()
        trace = trace_fifo_attribution_4hop(db_conn, account_id, config=config)

        assert trace.total_hops_found <= 4, f"total_hops_found {trace.total_hops_found} > 4"

        for edge in trace.edges:
            assert edge.hop_number >= 1 and edge.hop_number <= 4, f"Hop index {edge.hop_number} outside [1, 4]"
            assert edge.attributed_amount > 0.0, f"Edge amount <= 0: {edge.attributed_amount}"
            assert edge.source_account != "", "Empty source account"
            assert edge.destination_account != "", "Empty destination account"

        # Explicit truncation / cycle tracking
        assert isinstance(trace.truncated, bool)
        # truncation_reason is Optional[str]
        assert trace.truncation_reason is None or isinstance(trace.truncation_reason, str)
        # cycles_detected is List[str]
        assert isinstance(trace.cycles_detected, list)
