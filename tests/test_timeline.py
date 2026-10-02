"""
Unit & Integration Tests for Step 10A — Timeline Investigation
Tests chronological ordering, filtering, pagination, summary metrics,
velocity event classification, and FIFO attribution integration.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db
from backend.timeline.service import build_timeline
from backend.timeline.models import TimelineEventType

client = TestClient(app)

BENCHMARK_ACCOUNT = "KKBK10000402"


@pytest.fixture(scope="module")
def db_conn():
    return get_db()


class TestTimelineService:
    def test_dataset_temporal_boundaries(self, db_conn):
        resp = build_timeline(db_conn, page_size=10)
        assert resp.range.dataset_min_time == "2026-09-15 00:00:00"
        assert resp.range.dataset_max_time == "2026-09-29 23:59:58"
        assert resp.provenance.dataset_sha256 == "2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101"
        assert resp.provenance.total_dataset_rows == 2000000

    def test_chronological_ordering_and_tie_breaking(self, db_conn):
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, page_size=100)
        assert len(resp.events) > 0
        timestamps = [e.timestamp for e in resp.events]
        # Must be sorted ascending
        assert timestamps == sorted(timestamps)

        # Check deterministic tie-breaking (no None IDs, stable identifiers)
        for e in resp.events:
            assert e.event_id is not None
            assert len(e.event_id) > 0

    def test_account_filtering(self, db_conn):
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, page_size=50)
        assert resp.account_id == BENCHMARK_ACCOUNT
        assert resp.summary.transaction_count > 0
        assert resp.summary.incoming_volume > 0
        assert resp.summary.outgoing_volume > 0

        # Every transaction event should touch the account
        tx_events = [e for e in resp.events if e.event_type == TimelineEventType.TRANSACTION]
        for tx in tx_events:
            assert tx.source_account == BENCHMARK_ACCOUNT or tx.destination_account == BENCHMARK_ACCOUNT

    def test_direction_filtering(self, db_conn):
        in_resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, direction="in", page_size=50)
        in_txs = [e for e in in_resp.events if e.event_type == TimelineEventType.TRANSACTION]
        for tx in in_txs:
            assert tx.destination_account == BENCHMARK_ACCOUNT
            assert tx.direction == "INCOMING"

        out_resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, direction="out", page_size=50)
        out_txs = [e for e in out_resp.events if e.event_type == TimelineEventType.TRANSACTION]
        for tx in out_txs:
            assert tx.source_account == BENCHMARK_ACCOUNT
            assert tx.direction == "OUTGOING"

    def test_date_and_time_filtering(self, db_conn):
        start = "2026-09-20 00:00:00"
        end = "2026-09-21 23:59:59"
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, start_time=start, end_time=end, page_size=50)
        assert resp.range.start_time == start
        assert resp.range.end_time == end
        for e in resp.events:
            assert start <= e.timestamp <= end

    def test_payment_mode_filtering(self, db_conn):
        resp = build_timeline(db_conn, payment_mode="UPI", page_size=20)
        tx_events = [e for e in resp.events if e.event_type == TimelineEventType.TRANSACTION]
        for tx in tx_events:
            assert tx.payment_mode == "UPI"

    def test_device_filtering(self, db_conn):
        resp = build_timeline(db_conn, device_type="Android", page_size=20)
        tx_events = [e for e in resp.events if e.event_type == TimelineEventType.TRANSACTION]
        for tx in tx_events:
            assert tx.device_type == "Android"

    def test_event_type_filtering(self, db_conn):
        # Filter for velocity only
        vel_resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, event_type="velocity", page_size=50)
        for e in vel_resp.events:
            assert e.event_type == TimelineEventType.VELOCITY

        # Filter for attribution only
        attr_resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, event_type="attribution", page_size=50)
        for e in attr_resp.events:
            assert e.event_type == TimelineEventType.ATTRIBUTION

    def test_velocity_event_classification(self, db_conn):
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, event_type="velocity", page_size=50)
        for e in resp.events:
            assert "window_classification" in e.details
            assert e.details["window_classification"] in ["<3 min", "3–15 min", ">15 min"]
            assert "delay_minutes" in e.details

    def test_fifo_attribution_and_seed_distinction(self, db_conn):
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, event_type="attribution", page_size=50)
        for e in resp.events:
            edge_type = e.details.get("edge_type")
            assert edge_type in ["ROOT_SEED", "FIFO_ATTRIBUTION"]
            assert "hop" in e.details

    def test_pagination_correctness(self, db_conn):
        p1 = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, page=1, page_size=10)
        p2 = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, page=2, page_size=10)
        assert p1.page == 1
        assert p2.page == 2
        assert len(p1.events) <= 10
        assert len(p2.events) <= 10
        if len(p1.events) > 0 and len(p2.events) > 0:
            assert p1.events[0].event_id != p2.events[0].event_id

    def test_summary_metrics(self, db_conn):
        resp = build_timeline(db_conn, account_id=BENCHMARK_ACCOUNT, page_size=50)
        s = resp.summary
        assert s.total_events >= s.transaction_count
        assert s.net_volume == round(s.incoming_volume - s.outgoing_volume, 2)
        assert s.risk_role_findings is not None
        assert "mule_risk_score" in s.risk_role_findings
        assert "role" in s.risk_role_findings


class TestTimelineAPI:
    def test_get_timeline_endpoint_success(self):
        res = client.get("/api/timeline?account_id=KKBK10000402&page_size=20")
        assert res.status_code == 200
        data = res.json()
        assert data["account_id"] == "KKBK10000402"
        assert "summary" in data
        assert "events" in data
        assert "range" in data
        assert "provenance" in data
        assert len(data["events"]) <= 20

    def test_get_timeline_global_window(self):
        res = client.get("/api/timeline?start_time=2026-09-20%2000:00:00&end_time=2026-09-20%2001:00:00&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert len(data["events"]) <= 10

    def test_get_timeline_invalid_direction(self):
        res = client.get("/api/timeline?direction=sideways")
        assert res.status_code == 422
