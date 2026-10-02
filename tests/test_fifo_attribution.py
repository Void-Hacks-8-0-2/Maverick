"""
Test Suite for Step 5C -- Temporal FIFO Attribution
Operation 'ABHEDYA-CHAKRA'

Comprehensive verification of all 14 mandatory attribution invariants & test cases:
TEST 1:  One incoming -> one outgoing
TEST 2:  One incoming -> multiple outgoing
TEST 3:  Multiple incoming -> one outgoing
TEST 4:  Partial source consumption (exact prompt test: TX-A 1000, TX-B 500, Out 700, Out 600)
TEST 5:  Oversized outgoing (allocated 1000, unallocated 500)
TEST 6:  No eligible incoming (zero attribution, unallocated = full)
TEST 7:  Attribution horizon exclusion (horizon_seconds limit)
TEST 8:  Same-timestamp deterministic tie-breaking & no self-funding
TEST 9:  Duplicate Transaction_ID values disambiguated by row_id
TEST 10: 4-hop temporal money-flow provenance chain
TEST 11: Branching downstream flow
TEST 12: Repeated execution produces identical results (determinism)
TEST 13: Strict amount conservation (source & destination invariants)
TEST 14: No source amount reused twice
Additional tests:
TEST 15: Transaction-level attribution with row_id disambiguation
TEST 16: API endpoints integration testing (FastAPI TestClient)
"""

import pytest
import duckdb
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.attribution.config import AttributionPolicyConfig, DEFAULT_ATTRIBUTION_CONFIG
from backend.attribution.engine import (
    compute_account_fifo_attribution,
    trace_fifo_attribution_4hop,
    get_transaction_fifo_attribution
)

client = TestClient(app)


def _make_mem_con(rows: list) -> duckdb.DuckDBPyConnection:
    """
    Build an in-memory DuckDB connection with a transactions table matching the 11 production columns.
    DuckDB automatically provides a virtual rowid column.
    """
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE transactions (
            Transaction_ID   VARCHAR,
            Sender_Account   VARCHAR,
            Receiver_Account VARCHAR,
            Sender_IFSC      VARCHAR,
            Receiver_IFSC    VARCHAR,
            Amount           DOUBLE,
            Timestamp        TIMESTAMP,
            Payment_Mode     VARCHAR,
            Narration        VARCHAR,
            IP_Address       VARCHAR,
            Device_Type      VARCHAR
        );
    """)
    for r in rows:
        con.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", list(r)
        )
    return con


# ==============================================================================
# TEST 1: One incoming -> one outgoing
# ==============================================================================
def test_fifo_one_to_one():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 5, 0)
    rows = [
        ("TX_IN_1", "SENDER_X", "ACC_MULE", "IFSC01", "IFSC02", 1000.0, t0, "UPI", "fund", "1.1.1.1", "Mobile"),
        ("TX_OUT_1", "ACC_MULE", "DEST_Y", "IFSC02", "IFSC03", 700.0, t1, "UPI", "out", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_MULE")

    assert resp.account_id == "ACC_MULE"
    assert resp.total_incoming_volume == 1000.0
    assert resp.total_outgoing_volume == 700.0
    assert resp.total_attributed_volume == 700.0
    assert resp.total_unallocated_outflow == 0.0
    assert len(resp.attribution_records) == 1
    assert len(resp.unallocated_records) == 0

    record = resp.attribution_records[0]
    assert record.source_transaction_id == "TX_IN_1"
    assert record.destination_transaction_id == "TX_OUT_1"
    assert record.attributed_amount == 700.0
    assert record.delay_seconds == 300.0


# ==============================================================================
# TEST 2: One incoming -> multiple outgoing
# ==============================================================================
def test_fifo_one_to_many():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 10, 0)
    t2 = datetime(2025, 1, 1, 10, 20, 0)
    rows = [
        ("TX_IN", "SENDER_X", "ACC_MULE", "IFSC01", "IFSC02", 1000.0, t0, "UPI", "fund", "1.1.1.1", "Mobile"),
        ("TX_OUT_1", "ACC_MULE", "DEST_1", "IFSC02", "IFSC03", 400.0, t1, "UPI", "out1", "1.1.1.1", "Mobile"),
        ("TX_OUT_2", "ACC_MULE", "DEST_2", "IFSC02", "IFSC04", 500.0, t2, "UPI", "out2", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_MULE")

    assert resp.total_attributed_volume == 900.0
    assert resp.total_unallocated_outflow == 0.0
    assert len(resp.attribution_records) == 2

    assert resp.attribution_records[0].source_transaction_id == "TX_IN"
    assert resp.attribution_records[0].destination_transaction_id == "TX_OUT_1"
    assert resp.attribution_records[0].attributed_amount == 400.0

    assert resp.attribution_records[1].source_transaction_id == "TX_IN"
    assert resp.attribution_records[1].destination_transaction_id == "TX_OUT_2"
    assert resp.attribution_records[1].attributed_amount == 500.0


# ==============================================================================
# TEST 3: Multiple incoming -> one outgoing
# ==============================================================================
def test_fifo_many_to_one():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 5, 0)
    t2 = datetime(2025, 1, 1, 10, 10, 0)
    rows = [
        ("TX_IN_1", "SENDER_A", "ACC_MULE", "IFSC01", "IFSC02", 400.0, t0, "UPI", "in1", "1.1.1.1", "Mobile"),
        ("TX_IN_2", "SENDER_B", "ACC_MULE", "IFSC01", "IFSC02", 600.0, t1, "UPI", "in2", "1.1.1.1", "Mobile"),
        ("TX_OUT_1", "ACC_MULE", "DEST_C", "IFSC02", "IFSC03", 800.0, t2, "UPI", "out1", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_MULE")

    assert resp.total_attributed_volume == 800.0
    assert resp.total_unallocated_outflow == 0.0
    assert len(resp.attribution_records) == 2

    # First incoming fully consumed (400.0)
    assert resp.attribution_records[0].source_transaction_id == "TX_IN_1"
    assert resp.attribution_records[0].attributed_amount == 400.0
    # Second incoming partially consumed (400.0 of 600.0)
    assert resp.attribution_records[1].source_transaction_id == "TX_IN_2"
    assert resp.attribution_records[1].attributed_amount == 400.0


# ==============================================================================
# TEST 4: Partial source consumption (Exact prompt example)
# TX-A = ₹1000, TX-B = ₹500
# TX-C = ₹700 -> TX-A contributes ₹700 (rem TX-A = ₹300, TX-B = ₹500)
# TX-D = ₹600 -> TX-A contributes ₹300, TX-B contributes ₹300 (rem TX-B = ₹200)
# ==============================================================================
def test_fifo_partial_source_consumption():
    t0 = datetime(2025, 1, 1, 9, 0, 0)
    t1 = datetime(2025, 1, 1, 9, 10, 0)
    t2 = datetime(2025, 1, 1, 9, 20, 0)
    t3 = datetime(2025, 1, 1, 9, 30, 0)
    rows = [
        ("TX-A", "SRC_1", "ACC_INTERMEDIARY", "IFSC1", "IFSC2", 1000.0, t0, "IMPS", "A", "1.1.1.1", "PC"),
        ("TX-B", "SRC_2", "ACC_INTERMEDIARY", "IFSC1", "IFSC2", 500.0, t1, "IMPS", "B", "1.1.1.1", "PC"),
        ("TX-C", "ACC_INTERMEDIARY", "DEST_1", "IFSC2", "IFSC3", 700.0, t2, "IMPS", "C", "1.1.1.1", "PC"),
        ("TX-D", "ACC_INTERMEDIARY", "DEST_2", "IFSC2", "IFSC4", 600.0, t3, "IMPS", "D", "1.1.1.1", "PC"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_INTERMEDIARY")

    assert resp.total_incoming_volume == 1500.0
    assert resp.total_outgoing_volume == 1300.0
    assert resp.total_attributed_volume == 1300.0
    assert resp.total_unallocated_outflow == 0.0
    assert len(resp.attribution_records) == 3

    # TX-A -> TX-C = 700
    assert resp.attribution_records[0].source_transaction_id == "TX-A"
    assert resp.attribution_records[0].destination_transaction_id == "TX-C"
    assert resp.attribution_records[0].attributed_amount == 700.0

    # TX-A -> TX-D = 300
    assert resp.attribution_records[1].source_transaction_id == "TX-A"
    assert resp.attribution_records[1].destination_transaction_id == "TX-D"
    assert resp.attribution_records[1].attributed_amount == 300.0

    # TX-B -> TX-D = 300
    assert resp.attribution_records[2].source_transaction_id == "TX-B"
    assert resp.attribution_records[2].destination_transaction_id == "TX-D"
    assert resp.attribution_records[2].attributed_amount == 300.0


# ==============================================================================
# TEST 5: Oversized outgoing (Incoming available 1000, Outgoing 1500)
# Result: Attributed = 1000, Unallocated = 500
# ==============================================================================
def test_fifo_oversized_outgoing():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 15, 0)
    rows = [
        ("TX_IN", "SENDER_A", "ACC_TARGET", "IFSC1", "IFSC2", 1000.0, t0, "UPI", "in", "1.1.1.1", "Mobile"),
        ("TX_OUT", "ACC_TARGET", "DEST_B", "IFSC2", "IFSC3", 1500.0, t1, "UPI", "out", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_TARGET")

    assert resp.total_attributed_volume == 1000.0
    assert resp.total_unallocated_outflow == 500.0
    assert len(resp.attribution_records) == 1
    assert resp.attribution_records[0].attributed_amount == 1000.0

    assert len(resp.unallocated_records) == 1
    unalloc = resp.unallocated_records[0]
    assert unalloc.destination_transaction_id == "TX_OUT"
    assert unalloc.destination_amount == 1500.0
    assert unalloc.attributed_amount == 1000.0
    assert unalloc.unallocated_amount == 500.0
    assert unalloc.reason == "INFLOW_DEPLETED"


# ==============================================================================
# TEST 6: No eligible incoming
# Outgoing exists, zero incoming available. Attributed = 0, Unallocated = full
# ==============================================================================
def test_fifo_no_eligible_incoming():
    t1 = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_OUT", "ACC_NO_INFLOW", "DEST_B", "IFSC2", "IFSC3", 5000.0, t1, "UPI", "out", "1.1.1.1", "Mobile")
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_NO_INFLOW")

    assert resp.total_incoming_volume == 0.0
    assert resp.total_outgoing_volume == 5000.0
    assert resp.total_attributed_volume == 0.0
    assert resp.total_unallocated_outflow == 5000.0
    assert len(resp.attribution_records) == 0
    assert len(resp.unallocated_records) == 1
    assert resp.unallocated_records[0].unallocated_amount == 5000.0
    assert resp.unallocated_records[0].reason == "NO_PRIOR_INFLOW"


# ==============================================================================
# TEST 7: Attribution horizon exclusion
# In at T=0, Out at T=1000s. With horizon=500s -> excluded. With horizon=2000s -> attributed.
# ==============================================================================
def test_fifo_horizon_exclusion():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = t0 + timedelta(seconds=1000)
    rows = [
        ("TX_IN", "SENDER_A", "ACC_HORIZON", "IFSC1", "IFSC2", 1000.0, t0, "UPI", "in", "1.1.1.1", "Mobile"),
        ("TX_OUT", "ACC_HORIZON", "DEST_B", "IFSC2", "IFSC3", 1000.0, t1, "UPI", "out", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)

    # 1. Configured with 500 seconds horizon: elapsed is 1000s -> excluded
    resp_strict = compute_account_fifo_attribution(con, "ACC_HORIZON", horizon_seconds=500)
    assert resp_strict.horizon_seconds == 500
    assert resp_strict.total_attributed_volume == 0.0
    assert resp_strict.total_unallocated_outflow == 1000.0
    assert len(resp_strict.unallocated_records) == 1
    assert resp_strict.unallocated_records[0].reason == "HORIZON_EXCEEDED"

    # 2. Configured with 2000 seconds horizon: elapsed is 1000s -> attributed
    resp_wide = compute_account_fifo_attribution(con, "ACC_HORIZON", horizon_seconds=2000)
    assert resp_wide.horizon_seconds == 2000
    assert resp_wide.total_attributed_volume == 1000.0
    assert resp_wide.total_unallocated_outflow == 0.0
    assert len(resp_wide.attribution_records) == 1


# ==============================================================================
# TEST 8: Same timestamp deterministic ordering & no self-funding
# ==============================================================================
def test_fifo_same_timestamp_deterministic_ordering():
    t0 = datetime(2025, 1, 1, 12, 0, 0)
    # Both transactions inserted at the exact same second
    rows = [
        ("TX_IN_SAME", "SENDER_A", "ACC_SAME_TS", "IFSC1", "IFSC2", 800.0, t0, "UPI", "in", "1.1.1.1", "Mobile"),
        ("TX_OUT_SAME", "ACC_SAME_TS", "DEST_B", "IFSC2", "IFSC3", 800.0, t0, "UPI", "out", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_SAME_TS")

    # Inflow has smaller rowid than outflow -> strictly eligible
    assert resp.total_attributed_volume == 800.0
    assert len(resp.attribution_records) == 1
    record = resp.attribution_records[0]
    assert record.source_row_id < record.destination_row_id
    assert record.source_row_id != record.destination_row_id  # No self-funding

    # Reverse insertion test: Outflow inserted BEFORE inflow at same timestamp
    con_rev = duckdb.connect(":memory:")
    con_rev.execute("""
        CREATE TABLE transactions (
            Transaction_ID VARCHAR, Sender_Account VARCHAR, Receiver_Account VARCHAR,
            Sender_IFSC VARCHAR, Receiver_IFSC VARCHAR, Amount DOUBLE, Timestamp TIMESTAMP,
            Payment_Mode VARCHAR, Narration VARCHAR, IP_Address VARCHAR, Device_Type VARCHAR
        );
    """)
    # Insert outflow first (rowid=0), then inflow (rowid=1) at same timestamp
    con_rev.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ["TX_OUT_FIRST", "ACC_SAME_TS", "DEST_B", "IFSC2", "IFSC3", 800.0, t0, "UPI", "out", "1.1.1.1", "Mobile"])
    con_rev.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ["TX_IN_SECOND", "SENDER_A", "ACC_SAME_TS", "IFSC1", "IFSC2", 800.0, t0, "UPI", "in", "1.1.1.1", "Mobile"])

    resp_rev = compute_account_fifo_attribution(con_rev, "ACC_SAME_TS")
    # Because outflow has rowid 0 and inflow has rowid 1 at same timestamp, inflow cannot fund past outflow
    assert resp_rev.total_attributed_volume == 0.0
    assert resp_rev.total_unallocated_outflow == 800.0


# ==============================================================================
# TEST 9: Duplicate Transaction_ID values disambiguated by row_id
# ==============================================================================
def test_fifo_duplicate_transaction_ids():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 5, 0)
    t2 = datetime(2025, 1, 1, 10, 10, 0)
    # Two distinct rows with exact same Transaction_ID "TX_DUP"
    rows = [
        ("TX_DUP", "SENDER_1", "ACC_DUP", "IFSC1", "IFSC2", 500.0, t0, "UPI", "dup1", "1.1.1.1", "Mobile"),
        ("TX_DUP", "SENDER_2", "ACC_DUP", "IFSC1", "IFSC2", 700.0, t1, "UPI", "dup2", "1.1.1.1", "Mobile"),
        ("TX_OUT", "ACC_DUP", "DEST_X", "IFSC2", "IFSC3", 1000.0, t2, "UPI", "out", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_DUP")

    assert resp.total_attributed_volume == 1000.0
    assert len(resp.attribution_records) == 2

    # Both attribution records reference TX_DUP, but have distinct source_row_id values
    r1, r2 = resp.attribution_records[0], resp.attribution_records[1]
    assert r1.source_transaction_id == "TX_DUP"
    assert r2.source_transaction_id == "TX_DUP"
    assert r1.source_row_id != r2.source_row_id
    assert r1.source_row_id < r2.source_row_id
    assert r1.attributed_amount == 500.0
    assert r2.attributed_amount == 500.0


# ==============================================================================
# TEST 10: 4-hop temporal money-flow provenance chain
# Victim (A) -> B -> C -> D -> E
# ==============================================================================
def test_fifo_four_hop_provenance_chain():
    base = datetime(2025, 1, 1, 8, 0, 0)
    rows = [
        # Hop 1: VICTIM_A -> ACC_B (1000)
        ("TX_H1", "VICTIM_A", "ACC_B", "IFSC_A", "IFSC_B", 1000.0, base + timedelta(minutes=5), "UPI", "h1", "1.1.1.1", "Mobile"),
        # Hop 2: ACC_B -> ACC_C (900)
        ("TX_H2", "ACC_B", "ACC_C", "IFSC_B", "IFSC_C", 900.0, base + timedelta(minutes=10), "UPI", "h2", "1.1.1.1", "Mobile"),
        # Hop 3: ACC_C -> ACC_D (800)
        ("TX_H3", "ACC_C", "ACC_D", "IFSC_C", "IFSC_D", 800.0, base + timedelta(minutes=15), "UPI", "h3", "1.1.1.1", "Mobile"),
        # Hop 4: ACC_D -> ACC_E (700)
        ("TX_H4", "ACC_D", "ACC_E", "IFSC_D", "IFSC_E", 700.0, base + timedelta(minutes=20), "UPI", "h4", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "VICTIM_A", max_hops=4)

    assert trace.root_account == "VICTIM_A"
    assert trace.total_hops_found == 4
    assert len(trace.edges) == 4

    # Verify each hop has correct hop_number and temporal causality
    h1 = [e for e in trace.edges if e.hop_number == 1][0]
    h2 = [e for e in trace.edges if e.hop_number == 2][0]
    h3 = [e for e in trace.edges if e.hop_number == 3][0]
    h4 = [e for e in trace.edges if e.hop_number == 4][0]

    assert h1.source_account == "VICTIM_A" and h1.destination_account == "ACC_B" and h1.attributed_amount == 1000.0
    assert h2.intermediary_account == "ACC_B" and h2.destination_account == "ACC_C" and h2.attributed_amount == 900.0
    assert h3.intermediary_account == "ACC_C" and h3.destination_account == "ACC_D" and h3.attributed_amount == 800.0
    assert h4.intermediary_account == "ACC_D" and h4.destination_account == "ACC_E" and h4.attributed_amount == 700.0


# ==============================================================================
# TEST 11: Branching downstream flow
# Victim (A) -> B (1000)
# B -> C (400), B -> D (600)
# C -> E (400), D -> F (300), D -> G (300)
# ==============================================================================
def test_fifo_branching_downstream_flow():
    base = datetime(2025, 1, 1, 9, 0, 0)
    rows = [
        # Hop 1
        ("TX_ROOT", "VICTIM_A", "ACC_B", "IFSC", "IFSC", 1000.0, base, "UPI", "root", "1.1.1.1", "Mobile"),
        # Hop 2: B branches into C (400) and D (600)
        ("TX_B_C", "ACC_B", "ACC_C", "IFSC", "IFSC", 400.0, base + timedelta(minutes=10), "UPI", "bc", "1.1.1.1", "Mobile"),
        ("TX_B_D", "ACC_B", "ACC_D", "IFSC", "IFSC", 600.0, base + timedelta(minutes=15), "UPI", "bd", "1.1.1.1", "Mobile"),
        # Hop 3: C -> E (400), D -> F (300), D -> G (300)
        ("TX_C_E", "ACC_C", "ACC_E", "IFSC", "IFSC", 400.0, base + timedelta(minutes=25), "UPI", "ce", "1.1.1.1", "Mobile"),
        ("TX_D_F", "ACC_D", "ACC_F", "IFSC", "IFSC", 300.0, base + timedelta(minutes=30), "UPI", "df", "1.1.1.1", "Mobile"),
        ("TX_D_G", "ACC_D", "ACC_G", "IFSC", "IFSC", 300.0, base + timedelta(minutes=35), "UPI", "dg", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "VICTIM_A", max_hops=4)

    assert trace.total_hops_found == 3
    # 1 edge at hop 1, 2 edges at hop 2, 3 edges at hop 3 = 6 edges total
    assert len(trace.edges) == 6

    hop2_edges = [e for e in trace.edges if e.hop_number == 2]
    assert len(hop2_edges) == 2
    assert set(e.destination_account for e in hop2_edges) == {"ACC_C", "ACC_D"}

    hop3_edges = [e for e in trace.edges if e.hop_number == 3]
    assert len(hop3_edges) == 3
    assert set(e.destination_account for e in hop3_edges) == {"ACC_E", "ACC_F", "ACC_G"}


# ==============================================================================
# TEST 12: Repeated execution produces identical results (determinism)
# ==============================================================================
def test_fifo_determinism_repeated_execution():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_1", "S1", "ACC_DET", "IFSC1", "IFSC2", 500.0, t0, "UPI", "t1", "1.1.1.1", "Mobile"),
        ("TX_2", "S2", "ACC_DET", "IFSC1", "IFSC2", 750.0, t0 + timedelta(minutes=5), "UPI", "t2", "1.1.1.1", "Mobile"),
        ("TX_3", "ACC_DET", "D1", "IFSC2", "IFSC3", 600.0, t0 + timedelta(minutes=10), "UPI", "t3", "1.1.1.1", "Mobile"),
        ("TX_4", "ACC_DET", "D2", "IFSC2", "IFSC4", 650.0, t0 + timedelta(minutes=15), "UPI", "t4", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    res1 = compute_account_fifo_attribution(con, "ACC_DET")
    res2 = compute_account_fifo_attribution(con, "ACC_DET")

    # JSON model serialization must match identically
    assert res1.model_dump_json() == res2.model_dump_json()


# ==============================================================================
# TEST 13: Strict amount conservation (source & destination invariants)
# ==============================================================================
def test_fifo_amount_conservation_invariants():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("IN1", "SRC1", "ACC_CONS", "IFSC", "IFSC", 300.0, t0, "UPI", "", "1.1.1.1", "Mobile"),
        ("IN2", "SRC2", "ACC_CONS", "IFSC", "IFSC", 500.0, t0 + timedelta(minutes=1), "UPI", "", "1.1.1.1", "Mobile"),
        ("IN3", "SRC3", "ACC_CONS", "IFSC", "IFSC", 200.0, t0 + timedelta(minutes=2), "UPI", "", "1.1.1.1", "Mobile"),
        ("OUT1", "ACC_CONS", "DST1", "IFSC", "IFSC", 450.0, t0 + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("OUT2", "ACC_CONS", "DST2", "IFSC", "IFSC", 400.0, t0 + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
        ("OUT3", "ACC_CONS", "DST3", "IFSC", "IFSC", 300.0, t0 + timedelta(minutes=15), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_CONS")

    # Inflow: 300 + 500 + 200 = 1000
    # Outflow: 450 + 400 + 300 = 1150
    # Attributed = 1000, Unallocated = 150
    assert resp.total_incoming_volume == 1000.0
    assert resp.total_outgoing_volume == 1150.0
    assert resp.total_attributed_volume == 1000.0
    assert resp.total_unallocated_outflow == 150.0

    # Source Conservation: For every source transaction, sum(attributed) <= source_amount
    source_attribution_sums = {}
    for r in resp.attribution_records:
        source_attribution_sums[r.source_row_id] = source_attribution_sums.get(r.source_row_id, 0.0) + r.attributed_amount

    # Destination Conservation: For every destination transaction, sum(attributed) <= destination_amount
    dest_attribution_sums = {}
    for r in resp.attribution_records:
        dest_attribution_sums[r.destination_row_id] = dest_attribution_sums.get(r.destination_row_id, 0.0) + r.attributed_amount

    for r in resp.attribution_records:
        assert round(source_attribution_sums[r.source_row_id], 2) <= r.source_amount
        assert round(dest_attribution_sums[r.destination_row_id], 2) <= r.destination_amount

    # Total conservation check: total attributed + unallocated = total outgoing
    assert round(resp.total_attributed_volume + resp.total_unallocated_outflow, 2) == resp.total_outgoing_volume


# ==============================================================================
# TEST 14: No source amount reused twice
# ==============================================================================
def test_fifo_no_source_amount_reused():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("IN_SINGLE", "SRC", "ACC_NO_REUSE", "IFSC", "IFSC", 1000.0, t0, "UPI", "", "1.1.1.1", "Mobile"),
        ("OUT_1", "ACC_NO_REUSE", "DST1", "IFSC", "IFSC", 600.0, t0 + timedelta(minutes=1), "UPI", "", "1.1.1.1", "Mobile"),
        ("OUT_2", "ACC_NO_REUSE", "DST2", "IFSC", "IFSC", 600.0, t0 + timedelta(minutes=2), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    resp = compute_account_fifo_attribution(con, "ACC_NO_REUSE")

    # OUT_1 takes 600. Remaining: 400.
    # OUT_2 can only take 400 from IN_SINGLE. Unallocated: 200.
    assert len(resp.attribution_records) == 2
    assert resp.attribution_records[0].attributed_amount == 600.0
    assert resp.attribution_records[1].attributed_amount == 400.0
    assert resp.total_attributed_volume == 1000.0
    assert resp.total_unallocated_outflow == 200.0


# ==============================================================================
# TEST 15: Transaction-level attribution with row_id disambiguation
# ==============================================================================
def test_fifo_transaction_level_attribution():
    t0 = datetime(2025, 1, 1, 10, 0, 0)
    t1 = datetime(2025, 1, 1, 10, 5, 0)
    t2 = datetime(2025, 1, 1, 10, 10, 0)
    rows = [
        ("IN_FUND", "SRC", "ACC_TX_TEST", "IFSC", "IFSC", 1000.0, t0, "UPI", "", "1.1.1.1", "Mobile"),
        ("TX_SAME_ID", "ACC_TX_TEST", "DST1", "IFSC", "IFSC", 400.0, t1, "UPI", "", "1.1.1.1", "Mobile"),
        ("TX_SAME_ID", "ACC_TX_TEST", "DST2", "IFSC", "IFSC", 500.0, t2, "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)

    # First row with TX_SAME_ID (rowid=1)
    res_row1 = get_transaction_fifo_attribution(con, "TX_SAME_ID", row_id=1)
    assert res_row1.row_id == 1
    assert res_row1.transaction_id == "TX_SAME_ID"
    assert res_row1.amount == 400.0
    assert res_row1.attributed_amount == 400.0
    assert res_row1.remaining_or_unallocated_amount == 0.0

    # Second row with TX_SAME_ID (rowid=2)
    res_row2 = get_transaction_fifo_attribution(con, "TX_SAME_ID", row_id=2)
    assert res_row2.row_id == 2
    assert res_row2.transaction_id == "TX_SAME_ID"
    assert res_row2.amount == 500.0
    assert res_row2.attributed_amount == 500.0
    assert res_row2.remaining_or_unallocated_amount == 0.0


# ==============================================================================
# TEST 16: API endpoints integration testing (FastAPI TestClient)
# ==============================================================================
def test_fifo_api_endpoints_live():
    # 1. Test account attribution endpoint on a known account
    res = client.get("/api/accounts/KKBK10000402/attribution")
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == "KKBK10000402"
    assert data["policy_name"] == "TEMPORAL_FIFO"
    assert "total_attributed_volume" in data
    assert "total_unallocated_outflow" in data
    assert isinstance(data["attribution_records"], list)
    assert isinstance(data["unallocated_records"], list)

    # 2. Test account attribution with horizon_seconds parameter
    res_horizon = client.get("/api/accounts/KKBK10000402/attribution?horizon_seconds=3600")
    assert res_horizon.status_code == 200
    data_h = res_horizon.json()
    assert data_h["horizon_seconds"] == 3600

    # 3. Test 4-hop temporal money-flow trace endpoint
    res_trace = client.get("/api/accounts/KKBK10000402/attribution/trace?max_hops=4")
    assert res_trace.status_code == 200
    data_t = res_trace.json()
    assert data_t["root_account"] == "KKBK10000402"
    assert "nodes" in data_t
    assert "edges" in data_t
    assert "hop_summaries" in data_t
    assert "total_attributed_amount" in data_t

    # 4. Test 404 for non-existent account
    res_404 = client.get("/api/accounts/NON_EXISTENT_ACC_9999/attribution")
    assert res_404.status_code == 404


# ==============================================================================
# TEST 17: Root branch truncation (51 outgoing with limit 50 -> truncated=True)
# ==============================================================================
def test_fifo_root_branch_truncation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    # Generate 51 outgoing transactions from root
    rows = []
    for i in range(51):
        rows.append((
            f"TX_ROOT_{i}", "ROOT_ACC", f"DEST_{i}", "IFSC1", "IFSC2",
            100.0, base + timedelta(minutes=i), "UPI", "", "1.1.1.1", "Mobile"
        ))
    con = _make_mem_con(rows)
    custom_config = AttributionPolicyConfig(max_branches_per_hop=50)
    trace = trace_fifo_attribution_4hop(con, "ROOT_ACC", config=custom_config)

    assert trace.truncated is True
    assert trace.truncation_reason == "ROOT_OUTGOING_BRANCH_LIMIT"
    # Root seed edges are capped at configured limit (50)
    assert len(trace.edges) == 50


# ==============================================================================
# TEST 18: Intermediary branch truncation (51 outgoing from B with limit 50 -> truncated=True)
# ==============================================================================
def test_fifo_intermediary_branch_truncation():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        # Hop 1: ROOT -> INTER_B (10000)
        ("TX_ROOT", "ROOT_ACC", "INTER_B", "IFSC", "IFSC", 10000.0, base, "UPI", "", "1.1.1.1", "Mobile")
    ]
    # 51 outgoing transactions from INTER_B
    for i in range(51):
        rows.append((
            f"TX_INTER_{i}", "INTER_B", f"DEST_{i}", "IFSC", "IFSC",
            50.0, base + timedelta(minutes=10 + i), "UPI", "", "1.1.1.1", "Mobile"
        ))
    con = _make_mem_con(rows)
    custom_config = AttributionPolicyConfig(max_branches_per_hop=50)
    trace = trace_fifo_attribution_4hop(con, "ROOT_ACC", config=custom_config)

    assert trace.truncated is True
    assert trace.truncation_reason == "ACCOUNT_OUTGOING_BRANCH_LIMIT:INTER_B"
    # 1 root seed edge + 50 intermediary edges = 51 total edges
    assert len(trace.edges) == 51


# ==============================================================================
# TEST 19: Exactly-at-limit behavior (50 outgoing with limit 50 -> truncated=False)
# ==============================================================================
def test_fifo_exactly_at_limit():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = []
    for i in range(50):
        rows.append((
            f"TX_{i}", "ROOT_EXACT", f"DEST_{i}", "IFSC", "IFSC",
            100.0, base + timedelta(minutes=i), "UPI", "", "1.1.1.1", "Mobile"
        ))
    con = _make_mem_con(rows)
    custom_config = AttributionPolicyConfig(max_branches_per_hop=50)
    trace = trace_fifo_attribution_4hop(con, "ROOT_EXACT", config=custom_config)

    assert trace.truncated is False
    assert trace.truncation_reason is None
    assert len(trace.edges) == 50


# ==============================================================================
# TEST 20: Root seed edge distinction (ROOT_SEED vs FIFO_ATTRIBUTION)
# ==============================================================================
def test_fifo_root_seed_edge_distinction():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("TX_H1", "ROOT_ACC", "ACC_B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("TX_H2", "ACC_B", "ACC_C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "ROOT_ACC", max_hops=2)

    assert len(trace.edges) == 2
    root_edge = trace.edges[0]
    fifo_edge = trace.edges[1]

    # Root seed edge carries ROOT_SEED
    assert root_edge.hop_number == 1
    assert root_edge.edge_type == "ROOT_SEED"
    assert root_edge.source_row_id == root_edge.destination_row_id

    # Downstream attribution edge carries FIFO_ATTRIBUTION
    assert fifo_edge.hop_number == 2
    assert fifo_edge.edge_type == "FIFO_ATTRIBUTION"
    assert fifo_edge.source_row_id != fifo_edge.destination_row_id


# ==============================================================================
# TEST 21: Path-aware cycle detection (A -> B -> C -> B circular branch)
# ==============================================================================
def test_fifo_path_aware_cycle_detection():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        # Hop 1: A -> B (1000)
        ("TX_A_B", "ACC_A", "ACC_B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 2: B -> C (900)
        ("TX_B_C", "ACC_B", "ACC_C", "IFSC", "IFSC", 900.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 3: C -> B (800) -- Cycle back to B!
        ("TX_C_B", "ACC_C", "ACC_B", "IFSC", "IFSC", 800.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 4: B -> D (700) (if cyclic recursion continued, this would erroneously re-attribute)
        ("TX_B_D", "ACC_B", "ACC_D", "IFSC", "IFSC", 700.0, base + timedelta(minutes=15), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "ACC_A", max_hops=4)

    # Cycle must be detected and documented
    assert len(trace.cycles_detected) >= 1
    assert "ACC_A -> ACC_B -> ACC_C -> ACC_B" in trace.cycles_detected[0]

    # Circular branch terminated: no Hop 4 edge generated from the circular B
    hop4_edges = [e for e in trace.edges if e.hop_number == 4]
    assert len(hop4_edges) == 0


# ==============================================================================
# TEST 22: Victim propagation carry forward (Victim -> B 1000, B -> C 600 => only 600 to C)
# ==============================================================================
def test_fifo_victim_propagation_carry_forward():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        # Hop 1: Victim -> B = 1000
        ("TX_V_B", "VICTIM", "ACC_B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 2: B -> C = 600
        ("TX_B_C", "ACC_B", "ACC_C", "IFSC", "IFSC", 600.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 3: C attempts to send 900 to D. But C only received 600 of victim funds!
        ("TX_C_D", "ACC_C", "ACC_D", "IFSC", "IFSC", 900.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "VICTIM", max_hops=3)

    assert len(trace.edges) == 3
    # Hop 1: 1000
    assert trace.edges[0].attributed_amount == 1000.0
    # Hop 2: 600
    assert trace.edges[1].attributed_amount == 600.0
    # Hop 3: C can only attribute up to 600.0 to D (not 900.0!)
    assert trace.edges[2].attributed_amount == 600.0


# ==============================================================================
# TEST 23: Branching with partial attributed amounts
# ==============================================================================
def test_fifo_branching_with_partial_attributed_amounts():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        # Hop 1: Victim -> B = 1000
        ("TX_ROOT", "VICTIM", "ACC_B", "IFSC", "IFSC", 1000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 2: B splits into C (300) and D (700)
        ("TX_B_C", "ACC_B", "ACC_C", "IFSC", "IFSC", 300.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("TX_B_D", "ACC_B", "ACC_D", "IFSC", "IFSC", 700.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
        # Hop 3: C sends 500 to E (can only attribute 300); D sends 700 to F (fully attributes 700)
        ("TX_C_E", "ACC_C", "ACC_E", "IFSC", "IFSC", 500.0, base + timedelta(minutes=15), "UPI", "", "1.1.1.1", "Mobile"),
        ("TX_D_F", "ACC_D", "ACC_F", "IFSC", "IFSC", 700.0, base + timedelta(minutes=20), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "VICTIM", max_hops=3)

    # Edges: 1 root + 2 hop2 + 2 hop3 = 5
    assert len(trace.edges) == 5

    c_to_e = [e for e in trace.edges if e.destination_account == "ACC_E"][0]
    assert c_to_e.attributed_amount == 300.0  # Capped by C's inflow

    d_to_f = [e for e in trace.edges if e.destination_account == "ACC_F"][0]
    assert d_to_f.attributed_amount == 700.0  # Exactly 700


# ==============================================================================
# TEST 24: Mathematical conservation after 4 full hops
# ==============================================================================
def test_fifo_conservation_after_four_hops():
    base = datetime(2025, 1, 1, 10, 0, 0)
    rows = [
        ("T1", "A", "B", "IFSC", "IFSC", 5000.0, base, "UPI", "", "1.1.1.1", "Mobile"),
        ("T2", "B", "C", "IFSC", "IFSC", 4000.0, base + timedelta(minutes=5), "UPI", "", "1.1.1.1", "Mobile"),
        ("T3", "C", "D", "IFSC", "IFSC", 3500.0, base + timedelta(minutes=10), "UPI", "", "1.1.1.1", "Mobile"),
        ("T4", "D", "E", "IFSC", "IFSC", 2000.0, base + timedelta(minutes=15), "UPI", "", "1.1.1.1", "Mobile"),
    ]
    con = _make_mem_con(rows)
    trace = trace_fifo_attribution_4hop(con, "A", max_hops=4)

    assert trace.total_hops_found == 4
    # Check that at every hop, attributed amount is monotonic non-increasing
    h_amts = [e.attributed_amount for e in trace.edges]
    assert h_amts == [5000.0, 4000.0, 3500.0, 2000.0]

    # Verify nodes tracking
    nodes = {n.id: n for n in trace.nodes}
    assert nodes["A"].outflow_attributed == 5000.0
    assert nodes["B"].inflow_attributed == 5000.0
    assert nodes["B"].outflow_attributed == 4000.0
    assert nodes["C"].inflow_attributed == 4000.0
    assert nodes["C"].outflow_attributed == 3500.0
    assert nodes["D"].inflow_attributed == 3500.0
    assert nodes["D"].outflow_attributed == 2000.0
    assert nodes["E"].inflow_attributed == 2000.0
