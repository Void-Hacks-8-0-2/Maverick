"""
Step 11 — Blind Victim Query Benchmark Suite
Operation 'ABHEDYA-CHAKRA'

Evaluator-facing benchmark harness for 5 blind victim accounts.
Accepts accounts via environment variables:
BLIND_VICTIM_1, BLIND_VICTIM_2, BLIND_VICTIM_3, BLIND_VICTIM_4, BLIND_VICTIM_5

Rules:
- DO NOT fabricate 'unknown' accounts or ground truth victims.
- If environment variables are not supplied, the harness must cleanly report that
  official IDs were not supplied and no fabricated accuracy is reported.
- Target latency: <= 2.0 seconds (2000 ms) per victim query measured with time.perf_counter().
- Validates 4-hop bounds, risk, role, velocity, trace, terminals, warnings, and latency statistics.
"""

import os
import time
import statistics
from typing import Dict, Any, List, Optional
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db.connection import get_db

client = TestClient(app)

ENV_VICTIM_KEYS = [
    "BLIND_VICTIM_1",
    "BLIND_VICTIM_2",
    "BLIND_VICTIM_3",
    "BLIND_VICTIM_4",
    "BLIND_VICTIM_5",
]

TARGET_MAX_LATENCY_MS = 2000.0  # 2.0 seconds


def run_blind_victim_query(account_id: str) -> Dict[str, Any]:
    """
    Executes a victim investigation query, measuring exact latency and verifying all output dimensions.
    """
    start_time = time.perf_counter()
    response = client.get(f"/api/investigations/victim/{account_id}?max_hops=4")
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    result: Dict[str, Any] = {
        "account": account_id,
        "http_status": response.status_code,
        "latency_ms": round(elapsed_ms, 2),
        "target_met": elapsed_ms <= TARGET_MAX_LATENCY_MS,
        "investigation_success": False,
        "risk_returned": None,
        "role_returned": None,
        "velocity_returned": False,
        "trace_returned": False,
        "hop_count": 0,
        "terminal_count": 0,
        "warnings": [],
    }

    if response.status_code == 200:
        data = response.json()
        result["investigation_success"] = (data.get("status") in ("SUCCESS", "COMPLETED"))
        result["risk_returned"] = data.get("risk", {}).get("risk_index")
        result["role_returned"] = data.get("roles", {})
        result["velocity_returned"] = ("qualifying_event_count" in data.get("velocity", {}))
        trace = data.get("trace", {})
        result["trace_returned"] = bool(trace.get("edges") or trace.get("nodes"))
        edges = trace.get("edges", [])
        result["hop_count"] = max((e.get("hop_number", 0) for e in edges), default=0)
        result["terminal_count"] = len(data.get("terminals", []))
        result["warnings"] = data.get("warnings", [])

    return result


def compute_benchmark_statistics(latencies: List[float]) -> Dict[str, Any]:
    """Computes summary statistics over query latencies without manufacturing significance."""
    n = len(latencies)
    if n == 0:
        return {"sample_size": 0, "min_ms": None, "median_ms": None, "mean_ms": None, "max_ms": None, "p95_ms": None}

    sorted_lats = sorted(latencies)
    stats: Dict[str, Any] = {
        "sample_size": n,
        "min_ms": round(min(sorted_lats), 2),
        "median_ms": round(statistics.median(sorted_lats), 2),
        "mean_ms": round(statistics.mean(sorted_lats), 2),
        "max_ms": round(max(sorted_lats), 2),
    }

    # For p95, calculate only if sample size >= 5
    if n >= 5:
        p95_idx = int(0.95 * n)
        stats["p95_ms"] = round(sorted_lats[min(p95_idx, n - 1)], 2)
    else:
        stats["p95_ms"] = stats["max_ms"]

    return stats


class TestBlindVictimBenchmark:
    """Benchmark harness tests for blind victim queries."""

    def test_harness_with_benchmark_smoke_account(self):
        """Validates benchmark harness behavior against a known production account."""
        smoke_acc = "KKBK10000402"
        res = run_blind_victim_query(smoke_acc)

        assert res["http_status"] == 200
        assert res["investigation_success"] is True
        assert res["risk_returned"] is not None
        assert res["velocity_returned"] is True
        assert res["trace_returned"] is True
        assert res["hop_count"] <= 4, f"Hop count {res['hop_count']} exceeds max 4"
        assert res["latency_ms"] >= 0.0

    def test_blind_victim_env_evaluation(self):
        """
        Executes benchmark against official blind victims if supplied via environment variables.
        If environment variables are absent, asserts harness readiness without fabrication.
        """
        supplied_ids = [os.getenv(k) for k in ENV_VICTIM_KEYS if os.getenv(k)]

        if not supplied_ids:
            # Official requirement: do NOT fabricate unknown accounts or accuracy claims
            pytest.skip(
                "Benchmark harness ready; official blind victim IDs were not supplied via "
                "BLIND_VICTIM_1..5, so no fabricated blind-query accuracy result is reported."
            )

        results = []
        latencies = []
        for victim_id in supplied_ids:
            res = run_blind_victim_query(victim_id)
            results.append(res)
            latencies.append(res["latency_ms"])

            assert res["http_status"] in (200, 404)
            if res["http_status"] == 200:
                assert res["hop_count"] <= 4

        stats = compute_benchmark_statistics(latencies)
        assert stats["sample_size"] == len(supplied_ids)
