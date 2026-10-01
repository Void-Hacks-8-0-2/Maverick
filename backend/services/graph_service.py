"""
Graph Traversal and Network Service for Operation 'ABHEDYA-CHAKRA'
Base v0.1: Deterministic structural graph extraction & 4-hop traversal.
"""

from typing import Dict, Any, List, Set, Tuple
import duckdb


def get_account_graph(
    con: duckdb.DuckDBPyConnection,
    account_id: str,
    max_hops: int = 1,
    max_nodes: int = 500
) -> Dict[str, Any]:
    """
    Extract 1-hop or multi-hop ego network around account_id.
    Prevents uncontrolled expansion with max_nodes cutoff.
    """
    nodes_map: Dict[str, Dict[str, Any]] = {
        account_id: {"id": account_id, "type": "account", "is_root": True}
    }
    edges_map: Dict[str, Dict[str, Any]] = {}
    current_front: Set[str] = {account_id}
    visited: Set[str] = {account_id}
    truncated = False

    for hop in range(1, max_hops + 1):
        if not current_front or len(nodes_map) >= max_nodes:
            break

        # Query transactions involving current front
        front_list = list(current_front)
        # Use parameterized query or in clause
        placeholders = ", ".join(["?"] * len(front_list))
        query = f"""
            SELECT Transaction_ID, Sender_Account, Receiver_Account, Amount, Payment_Mode, Narration, IP_Address
            FROM transactions
            WHERE Sender_Account IN ({placeholders}) OR Receiver_Account IN ({placeholders})
            LIMIT ?
        """
        params = front_list + front_list + [max_nodes * 5]
        rows = con.execute(query, params).fetchall()

        next_front: Set[str] = set()

        for tx_id, sender, receiver, amt, pm, narr, ip in rows:
            if tx_id not in edges_map:
                edges_map[tx_id] = {
                    "id": tx_id,
                    "source": sender,
                    "target": receiver,
                    "transaction_id": tx_id,
                    "amount": float(amt) if amt is not None else 0.0,
                    "payment_mode": pm or "",
                    "narration": narr or "",
                    "ip_address": ip or ""
                }

            for acc in (sender, receiver):
                if acc not in nodes_map:
                    if len(nodes_map) >= max_nodes:
                        truncated = True
                        break
                    nodes_map[acc] = {
                        "id": acc,
                        "type": "account",
                        "is_root": (acc == account_id)
                    }
                    if acc not in visited:
                        next_front.add(acc)
                        visited.add(acc)

            if truncated:
                break

        current_front = next_front

    return {
        "root_account": account_id,
        "nodes": list(nodes_map.values()),
        "edges": list(edges_map.values()),
        "truncated": truncated,
        "node_limit": max_nodes
    }


def get_account_trace(
    con: duckdb.DuckDBPyConnection,
    account_id: str,
    max_hops: int = 4,
    max_nodes: int = 1000
) -> Dict[str, Any]:
    """
    Deterministic structural forward-flow traversal up to max_hops (default 4).
    Cycle prevention: Does not revisit accounts within the active path.
    """
    nodes_map: Dict[str, Dict[str, Any]] = {
        account_id: {"id": account_id, "type": "account", "is_root": True, "hop": 0}
    }
    edges_map: Dict[str, Dict[str, Any]] = {}
    paths: List[List[str]] = []
    truncated = False

    # Current paths: list of (path_nodes, path_edges)
    active_paths: List[Tuple[List[str], List[str]]] = [([account_id], [])]

    for hop in range(1, max_hops + 1):
        if not active_paths:
            break

        next_active_paths: List[Tuple[List[str], List[str]]] = []
        senders_in_level = list({p[0][-1] for p in active_paths})

        if not senders_in_level:
            break

        placeholders = ", ".join(["?"] * len(senders_in_level))
        query = f"""
            SELECT Transaction_ID, Sender_Account, Receiver_Account, Amount, Payment_Mode, Narration, IP_Address
            FROM transactions
            WHERE Sender_Account IN ({placeholders})
            ORDER BY Amount DESC
            LIMIT ?
        """
        params = senders_in_level + [max_nodes * 3]
        rows = con.execute(query, params).fetchall()

        # Group outbound txs by sender
        tx_by_sender: Dict[str, List[Any]] = {}
        for row in rows:
            tx_by_sender.setdefault(row[1], []).append(row)

        for path_accs, path_edges in active_paths:
            sender = path_accs[-1]
            outbounds = tx_by_sender.get(sender, [])

            if not outbounds:
                if len(path_accs) > 1:
                    paths.append(path_accs)
                continue

            for tx_id, s_acc, r_acc, amt, pm, narr, ip in outbounds:
                # Cycle prevention: target must not already exist in this specific path
                if r_acc in path_accs:
                    continue

                if len(nodes_map) >= max_nodes:
                    truncated = True
                    break

                if r_acc not in nodes_map:
                    nodes_map[r_acc] = {
                        "id": r_acc,
                        "type": "account",
                        "is_root": False,
                        "hop": hop
                    }

                if tx_id not in edges_map:
                    edges_map[tx_id] = {
                        "id": tx_id,
                        "source": s_acc,
                        "target": r_acc,
                        "transaction_id": tx_id,
                        "amount": float(amt) if amt is not None else 0.0,
                        "payment_mode": pm or "",
                        "narration": narr or "",
                        "ip_address": ip or ""
                    }

                new_path_accs = path_accs + [r_acc]
                new_path_edges = path_edges + [tx_id]

                if hop == max_hops:
                    paths.append(new_path_accs)
                else:
                    next_active_paths.append((new_path_accs, new_path_edges))

            if truncated:
                break

        if truncated:
            break

        active_paths = next_active_paths

    # Add remaining active paths if any
    for p_accs, _ in active_paths:
        if p_accs not in paths and len(p_accs) > 1:
            paths.append(p_accs)

    # Sort paths by length descending, limit to top 100 paths
    paths.sort(key=len, reverse=True)
    paths = paths[:100]

    return {
        "root_account": account_id,
        "max_hops": max_hops,
        "nodes": list(nodes_map.values()),
        "edges": list(edges_map.values()),
        "paths": paths,
        "truncated": truncated,
        "node_limit": max_nodes
    }
