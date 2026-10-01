"""
Regression tests for Graph Integrity & Duplicate Transaction_ID Handling
Validates collision-safe deterministic edge identities and multi-hop traversal.
"""

import duckdb
from backend.services.graph_service import get_account_graph, get_account_trace, make_edge_id


def test_make_edge_id_determinism_and_collision_safety():
    # Different senders/receivers
    id1 = make_edge_id("ACC_A", "ACC_B", "TX001", "2026-09-15 10:00:00", 0)
    id2 = make_edge_id("ACC_B", "ACC_C", "TX001", "2026-09-15 10:05:00", 1)
    assert id1 != id2
    assert "TX001" in id1
    assert "TX001" in id2

    # Identical accounts, tx_id, and timestamp but different row_id (source record identifier)
    id3 = make_edge_id("ACC_A", "ACC_B", "TX001", "2026-09-15 10:00:00", 2)
    assert id1 != id3


def test_duplicate_transaction_id_preservation_in_graph():
    """
    Controlled test dataset with duplicate Transaction_ID 'TX001'.
    Verifies:
    1. Both source transactions remain present.
    2. Both graph edges remain present.
    3. Neither overwrites the other.
    4. Traversal does not silently lose either transaction.
    5. Transaction metadata remains associated with the correct edge.
    """
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE transactions (
            Transaction_ID VARCHAR,
            Sender_Account VARCHAR,
            Receiver_Account VARCHAR,
            Sender_IFSC VARCHAR,
            Receiver_IFSC VARCHAR,
            Amount DOUBLE,
            Timestamp TIMESTAMP,
            Payment_Mode VARCHAR,
            Narration VARCHAR,
            IP_Address VARCHAR,
            Device_Type VARCHAR
        )
    """)

    # Record 1: ACC_A -> ACC_B (TX001 at 10:00)
    # Record 2: ACC_B -> ACC_C (TX001 at 10:05)
    # Record 3: ACC_B -> ACC_C (TX001 at 10:05) - identical sender, receiver, tx_id, timestamp!
    con.execute("""
        INSERT INTO transactions VALUES
        ('TX001', 'ACC_A', 'ACC_B', 'IFSC_A', 'IFSC_B', 1000.0, '2026-09-15 10:00:00', 'UPI', 'Transfer 1', '10.0.0.1', 'Android'),
        ('TX001', 'ACC_B', 'ACC_C', 'IFSC_B', 'IFSC_C', 800.0, '2026-09-15 10:05:00', 'IMPS', 'Transfer 2', '10.0.0.2', 'iOS'),
        ('TX001', 'ACC_B', 'ACC_C', 'IFSC_B', 'IFSC_C', 200.0, '2026-09-15 10:05:00', 'NEFT', 'Transfer 3', '10.0.0.3', 'Web_Emulator')
    """)

    # 1. Both source transactions remain present
    count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert count == 3

    # 2 & 3. Both graph edges remain present; neither overwrites the other
    graph = get_account_graph(con, "ACC_B", max_hops=2)
    assert len(graph["edges"]) == 3, f"Expected 3 distinct edges, got {len(graph['edges'])}"
    
    # Verify all edges carry original Transaction_ID as data
    for edge in graph["edges"]:
        assert edge["transaction_id"] == "TX001"
        assert "record_id" in edge
        assert "timestamp" in edge

    # 5. Metadata remains correctly associated
    edge_amounts = sorted([e["amount"] for e in graph["edges"]])
    assert edge_amounts == [200.0, 800.0, 1000.0]

    # Verify payment modes match the amounts exactly
    amt_mode_map = {e["amount"]: e["payment_mode"] for e in graph["edges"]}
    assert amt_mode_map[1000.0] == "UPI"
    assert amt_mode_map[800.0] == "IMPS"
    assert amt_mode_map[200.0] == "NEFT"

    # 4. Traversal does not silently lose either transaction
    trace = get_account_trace(con, "ACC_A", max_hops=2)
    assert len(trace["edges"]) == 3, f"Expected 3 trace edges, got {len(trace['edges'])}"
    trace_amounts = sorted([e["amount"] for e in trace["edges"]])
    assert trace_amounts == [200.0, 800.0, 1000.0]
