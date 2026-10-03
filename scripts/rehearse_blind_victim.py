"""
Rehearsal Script for 40% Blind-Victim Evaluation Criterion
Operation 'ABHEDYA-CHAKRA'
"""

import sys
import time
import json
from pathlib import Path

project_root = Path(r"c:\Users\sdmgo\.gemini\antigravity-ide\scratch\Maverick")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.db.connection import get_db
from backend.investigations.orchestrator import investigate_victim_account
from backend.features import get_account_features

con = get_db()

rehearsal_victims = [
    "BARB10000009",
    "IPOS10000042",
    "ICIC10000106",
    "SBIN10000110",
    "BARB10000115",
]

print("=== RUNNING 5-CASE BLIND VICTIM REHEARSAL ===")

results = []

for idx, victim_id in enumerate(rehearsal_victims, 1):
    print(f"\n--- Case {idx}: Victim Account {victim_id} ---")
    t_start = time.perf_counter()
    try:
        resp = investigate_victim_account(con, victim_id, max_hops=4)
        latency = time.perf_counter() - t_start
    except Exception as e:
        print(f"FAILED: {e}")
        continue

    # Extract path nodes per hop
    hops_map = {}
    for edge in resp.trace.edges:
        h = edge.hop_number
        hops_map.setdefault(h, set()).add((edge.source_account, edge.destination_account, edge.source_transaction_id, edge.attributed_amount, edge.source_timestamp))

    # Collect nodes per role
    l1_nodes = [t.account_number for t in resp.terminals if "L1" in t.primary_role]
    l2_nodes = [t.account_number for t in resp.terminals if "L2" in t.primary_role]
    l3_nodes = [t.account_number for t in resp.terminals if "L3" in t.primary_role]

    # Check root victim properties
    feat = get_account_features(con, victim_id)
    victim_is_mule = feat.predicted_mule_candidate if feat else False
    victim_l1 = feat.layer1_candidate if feat else False
    victim_l2 = feat.layer2_candidate if feat else False
    victim_l3 = feat.layer3_candidate if feat else False

    case_data = {
        "case_number": idx,
        "victim_account": victim_id,
        "latency_seconds": round(latency, 4),
        "sub_2_sec": latency < 2.0,
        "victim_is_predicted_mule": victim_is_mule,
        "victim_legacy_role": "NONE" if not (victim_l1 or victim_l2 or victim_l3) else "ROLE_TRIGGERED",
        "total_edges": len(resp.trace.edges),
        "total_nodes": len(resp.trace.nodes),
        "max_hop_reached": resp.evidence_summary.max_verified_propagation,
        "total_attributed_amount": resp.trace.total_attributed_amount,
        "terminals_count": len(resp.terminals),
        "sample_edges": [
            {
                "hop": e.hop_number,
                "source": e.source_account,
                "dest": e.destination_account,
                "amount": e.attributed_amount,
                "tx_id": e.source_transaction_id,
                "timestamp": e.source_timestamp,
            }
            for e in resp.trace.edges[:6]
        ],
        "terminals_sample": [
            {
                "account": t.account_number,
                "hop": t.hop,
                "amount": t.attributed_amount,
                "role": t.primary_role,
                "risk_band": t.risk_band,
            }
            for t in resp.terminals[:4]
        ]
    }
    results.append(case_data)
    print(f"  Latency: {case_data['latency_seconds']}s (Sub-2s target: {case_data['sub_2_sec']})")
    print(f"  Max Hop Reached: {case_data['max_hop_reached']}")
    print(f"  Total Attributed: INR {case_data['total_attributed_amount']:,.2f}")
    print(f"  Edges: {case_data['total_edges']}, Nodes: {case_data['total_nodes']}, Terminals: {case_data['terminals_count']}")
    print(f"  Root victim classified as mule: {case_data['victim_is_predicted_mule']}")
    for e in case_data["sample_edges"][:3]:
        print(f"    Hop {e['hop']}: {e['source']} -> {e['dest']} (INR {e['amount']:,.2f}, Tx: {e['tx_id']})")

print("\n=== AGGREGATE REHEARSAL METRICS ===")
latencies = [c["latency_seconds"] for c in results]
print(f"Cases Attempted: {len(results)}")
print(f"Successful Traces: {sum(1 for c in results if c['max_hop_reached'] >= 2)}")
print(f"Avg Latency: {round(sum(latencies)/len(latencies), 4)}s")
print(f"Max Latency: {round(max(latencies), 4)}s")
print(f"All Sub-2-Second: {all(c['sub_2_sec'] for c in results)}")
print(f"Victim Root Independent of Mule Prediction: {all(not c['victim_is_predicted_mule'] for c in results)}")

# Save report
Path("reports").mkdir(exist_ok=True)
with open("reports/blind_victim_rehearsal.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved detailed report to reports/blind_victim_rehearsal.json")
