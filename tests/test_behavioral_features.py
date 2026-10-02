"""
Correctness and Determinism Tests for Deterministic Behavioral Feature Engine
Validates account coverage, flow reconciliation, fan-in/fan-out, counterparties,
device/IP/mode profiles, timestamp spans, zero/NULL semantics, and exact determinism.
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.db.connection import get_db
from backend.features.behavioral import compute_account_features, get_account_features
from backend.features.models import AccountFeatures

client = TestClient(app)


def test_feature_account_coverage():
    """
    Test 1: Every account in accounts_dimension exists in account_features.
    Total count must be exactly 24,873.
    """
    con = get_db()
    dim_count = con.execute("SELECT COUNT(*) FROM accounts_dimension").fetchone()[0]
    feat_count = con.execute("SELECT COUNT(*) FROM account_features").fetchone()[0]

    assert dim_count == 24873, f"Expected 24873 dimension accounts, got {dim_count}"
    assert feat_count == 24873, f"Expected 24873 feature accounts, got {feat_count}"

    # Verify zero missing accounts between dimension and features
    missing = con.execute("""
        SELECT COUNT(*) 
        FROM accounts_dimension d
        LEFT JOIN account_features f ON d.account_number = f.account_number
        WHERE f.account_number IS NULL
    """).fetchone()[0]
    assert missing == 0, f"Found {missing} accounts in dimension that are missing from feature store"


def test_flow_reconciliation():
    """
    Test 2: For selected accounts:
    feature incoming_volume == accounts_dimension total_inflow
    feature outgoing_volume == accounts_dimension total_outflow
    feature net_flow_delta == accounts_dimension net_flow_delta
    """
    con = get_db()
    test_accounts = ["SBIN10012624", "KKBK10000000", "AXIS10023183", "IPOS10021017"]

    for acc in test_accounts:
        dim = con.execute("""
            SELECT total_inflow, total_outflow, net_flow_delta, incoming_txn_count, outgoing_txn_count
            FROM accounts_dimension WHERE account_number = ?
        """, [acc]).fetchone()

        feat = con.execute("""
            SELECT incoming_volume, outgoing_volume, net_flow_delta, incoming_txn_count, outgoing_txn_count
            FROM account_features WHERE account_number = ?
        """, [acc]).fetchone()

        assert dim is not None and feat is not None
        assert feat[0] == dim[0], f"Incoming volume mismatch for {acc}: {feat[0]} != {dim[0]}"
        assert feat[1] == dim[1], f"Outgoing volume mismatch for {acc}: {feat[1]} != {dim[1]}"
        assert feat[2] == dim[2], f"Net flow delta mismatch for {acc}: {feat[2]} != {dim[2]}"
        assert feat[3] == dim[3], f"Incoming txn count mismatch for {acc}: {feat[3]} != {dim[3]}"
        assert feat[4] == dim[4], f"Outgoing txn count mismatch for {acc}: {feat[4]} != {dim[4]}"


def test_fan_in_validation():
    """
    Test 3: Fan-in validates against direct SQL aggregation on raw transactions.
    fan_in = count of unique sender accounts transferring into target account.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_fan_in = con.execute("""
        SELECT COUNT(DISTINCT Sender_Account) 
        FROM transactions 
        WHERE Receiver_Account = ?
    """, [test_acc]).fetchone()[0]

    feat_fan_in = con.execute("""
        SELECT fan_in FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()[0]

    assert feat_fan_in == raw_fan_in, f"Fan-in mismatch: {feat_fan_in} != {raw_fan_in}"


def test_fan_out_validation():
    """
    Test 4: Fan-out validates against direct SQL aggregation on raw transactions.
    fan_out = count of unique receiver accounts receiving from target account.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_fan_out = con.execute("""
        SELECT COUNT(DISTINCT Receiver_Account) 
        FROM transactions 
        WHERE Sender_Account = ?
    """, [test_acc]).fetchone()[0]

    feat_fan_out = con.execute("""
        SELECT fan_out FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()[0]

    assert feat_fan_out == raw_fan_out, f"Fan-out mismatch: {feat_fan_out} != {raw_fan_out}"


def test_counterparties_validation():
    """
    Test 5: Unique counterparties validates against direct SQL union on raw transactions.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_cp = con.execute("""
        SELECT COUNT(DISTINCT cp) FROM (
            SELECT Sender_Account AS cp FROM transactions WHERE Receiver_Account = ?
            UNION
            SELECT Receiver_Account AS cp FROM transactions WHERE Sender_Account = ?
        )
    """, [test_acc, test_acc]).fetchone()[0]

    feat_cp = con.execute("""
        SELECT unique_counterparties FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()[0]

    assert feat_cp == raw_cp, f"Counterparties mismatch: {feat_cp} != {raw_cp}"


def test_device_counts_validation():
    """
    Test 6: Device counts validate against raw transaction data.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_devices = con.execute("""
        SELECT Device_Type, COUNT(*) 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
        GROUP BY Device_Type
    """, [test_acc, test_acc]).fetchall()
    raw_dev_map = {r[0]: r[1] for r in raw_devices}

    feat = con.execute("""
        SELECT unique_device_count, android_txn_count, ios_txn_count, 
               windows_browser_txn_count, web_emulator_txn_count, linux_script_txn_count
        FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()

    assert feat[0] == len(raw_dev_map)
    assert feat[1] == raw_dev_map.get("Android", 0)
    assert feat[2] == raw_dev_map.get("iOS", 0)
    assert feat[3] == raw_dev_map.get("Windows_Browser", 0)
    assert feat[4] == raw_dev_map.get("Web_Emulator", 0)
    assert feat[5] == raw_dev_map.get("Linux_Script", 0)


def test_payment_mode_counts_validation():
    """
    Test 7: Payment-mode counts validate against raw transaction data.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_pm = con.execute("""
        SELECT Payment_Mode, COUNT(*) 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
        GROUP BY Payment_Mode
    """, [test_acc, test_acc]).fetchall()
    raw_pm_map = {r[0]: r[1] for r in raw_pm}

    feat = con.execute("""
        SELECT upi_txn_count, imps_txn_count, neft_txn_count, rtgs_txn_count
        FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()

    assert feat[0] == raw_pm_map.get("UPI", 0)
    assert feat[1] == raw_pm_map.get("IMPS", 0)
    assert feat[2] == raw_pm_map.get("NEFT", 0)
    assert feat[3] == raw_pm_map.get("RTGS", 0)


def test_ip_counts_validation():
    """
    Test 8: Unique IP counts validate against raw transaction data.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_ips = con.execute("""
        SELECT COUNT(DISTINCT IP_Address) 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
    """, [test_acc, test_acc]).fetchone()[0]

    feat_ips = con.execute("""
        SELECT unique_ip_count FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()[0]

    assert feat_ips == raw_ips, f"IP count mismatch: {feat_ips} != {raw_ips}"


def test_timestamp_span_validation():
    """
    Test 9: First and last timestamps validate against raw transaction data.
    """
    con = get_db()
    test_acc = "SBIN10012624"
    raw_span = con.execute("""
        SELECT MIN(Timestamp), MAX(Timestamp) 
        FROM transactions 
        WHERE Sender_Account = ? OR Receiver_Account = ?
    """, [test_acc, test_acc]).fetchone()

    feat_span = con.execute("""
        SELECT first_seen_timestamp, last_seen_timestamp, activity_span_seconds
        FROM account_features WHERE account_number = ?
    """, [test_acc]).fetchone()

    assert feat_span[0] == raw_span[0], "First seen timestamp mismatch"
    assert feat_span[1] == raw_span[1], "Last seen timestamp mismatch"
    expected_seconds = int((raw_span[1] - raw_span[0]).total_seconds())
    assert feat_span[2] == expected_seconds, "Activity span seconds mismatch"


def test_sender_only_account_zero_null_semantics():
    """
    Test 10: Sender-only account has correct zero and NULL semantics:
    incoming_txn_count = 0, incoming_volume = 0.0, fan_in = 0,
    outflow_to_inflow_ratio = NULL, incoming amount stats = NULL.
    """
    con = get_db()
    acc = con.execute("SELECT account_number FROM account_features WHERE incoming_txn_count = 0 LIMIT 1").fetchone()[0]
    row = con.execute("""
        SELECT incoming_txn_count, outgoing_txn_count, incoming_volume, outgoing_volume,
               fan_in, fan_out, outflow_to_inflow_ratio, inflow_to_outflow_ratio,
               incoming_amount_min, outgoing_amount_min
        FROM account_features WHERE account_number = ?
    """, [acc]).fetchone()

    assert row[0] == 0  # incoming_txn_count
    assert row[1] > 0   # outgoing_txn_count
    assert row[2] == 0.0  # incoming_volume
    assert row[3] > 0.0  # outgoing_volume
    assert row[4] == 0  # fan_in
    assert row[5] > 0  # fan_out
    assert row[6] is None  # outflow_to_inflow_ratio (denominator is 0 -> NULL)
    assert row[7] == 0.0   # inflow_to_outflow_ratio (0.0 / outgoing)
    assert row[8] is None  # incoming_amount_min (no incoming txns -> NULL)
    assert row[9] is not None  # outgoing_amount_min (has outgoing txns)


def test_receiver_only_account_zero_null_semantics():
    """
    Test 11: Receiver-only account has correct zero and NULL semantics:
    outgoing_txn_count = 0, outgoing_volume = 0.0, fan_out = 0,
    inflow_to_outflow_ratio = NULL, outgoing amount stats = NULL.
    """
    con = get_db()
    acc = con.execute("SELECT account_number FROM account_features WHERE outgoing_txn_count = 0 LIMIT 1").fetchone()[0]
    row = con.execute("""
        SELECT incoming_txn_count, outgoing_txn_count, incoming_volume, outgoing_volume,
               fan_in, fan_out, outflow_to_inflow_ratio, inflow_to_outflow_ratio,
               incoming_amount_min, outgoing_amount_min
        FROM account_features WHERE account_number = ?
    """, [acc]).fetchone()

    assert row[0] > 0   # incoming_txn_count
    assert row[1] == 0  # outgoing_txn_count
    assert row[2] > 0.0  # incoming_volume
    assert row[3] == 0.0  # outgoing_volume
    assert row[4] > 0  # fan_in
    assert row[5] == 0  # fan_out
    assert row[6] == 0.0   # outflow_to_inflow_ratio (0.0 / incoming)
    assert row[7] is None  # inflow_to_outflow_ratio (denominator is 0 -> NULL)
    assert row[8] is not None  # incoming_amount_min (has incoming txns)
    assert row[9] is None  # outgoing_amount_min (no outgoing txns -> NULL)


def test_feature_determinism():
    """
    Test 12: Running the feature computation twice yields exactly identical results
    across all metrics (ignoring dynamic computed_at metadata).
    """
    con = get_db()
    # Read snapshot before recomputation
    cols = [
        "account_number", "incoming_txn_count", "outgoing_txn_count", "incoming_volume",
        "outgoing_volume", "net_flow_delta", "fan_in", "fan_out", "unique_counterparties",
        "outflow_to_inflow_ratio", "inflow_to_outflow_ratio", "activity_span_seconds",
        "active_day_count", "active_hour_count", "incoming_amount_median", "outgoing_amount_median",
        "unique_device_count", "unique_ip_count", "top_ip_transaction_count", "upi_txn_count",
        "unique_narration_count", "night_transaction_count"
    ]
    col_str = ", ".join(cols)
    snap1 = con.execute(f"SELECT {col_str} FROM account_features ORDER BY account_number").fetchall()

    # Recompute
    count = compute_account_features(con)
    assert count == 24873

    # Read snapshot after recomputation
    snap2 = con.execute(f"SELECT {col_str} FROM account_features ORDER BY account_number").fetchall()

    assert len(snap1) == len(snap2)
    assert snap1 == snap2, "Feature computation is not deterministic!"


def test_account_features_api_endpoint():
    """
    Validates GET /api/accounts/{account_id}/features internal endpoint contract.
    """
    res = client.get("/api/accounts/SBIN10012624/features")
    assert res.status_code == 200
    data = res.json()
    assert data["account_number"] == "SBIN10012624"
    assert data["fan_in"] == 86
    assert data["fan_out"] == 122
    assert data["incoming_txn_count"] == 86
    assert data["outgoing_txn_count"] == 122
    assert data["incoming_volume"] == 119331.69
    assert data["outgoing_volume"] == 183640.92
    assert data["net_flow_delta"] == -64309.23
    assert data["unique_counterparties"] == 206
    assert data["feature_version"] == "v1"
    assert data["provenance"] == "DERIVED"
    # Step 4 Candidate classifications
    assert data["layer1_candidate"] is False
    assert data["layer2_candidate"] is True
    assert data["layer3_candidate"] is False
    assert len(data["layer2_reasons"]) > 0
    assert data["layer2_signal_count"] >= 3
    assert data["classification_version"] == "v1"
    assert data["classification_provenance"] == "CANDIDATE_CLASSIFICATION"
    # Step 5B Mule Risk Index computed value
    assert data["mule_risk_index"] is not None and 0.0 <= data["mule_risk_index"] <= 100.0


    # Test 404
    res_404 = client.get("/api/accounts/NON_EXISTENT_ACC/features")
    assert res_404.status_code == 404
