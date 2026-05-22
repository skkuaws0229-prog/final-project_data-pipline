#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "06_graph" / "validation"
API_BASE_URL = "http://127.0.0.1:8010"
DISEASE_IDS = ["BRCA", "Colon", "HNSC", "IPF", "LUNG", "Liver", "PAH", "PDAC", "Psoriasis", "RA", "STAD"]


def fetch_graph(disease_id: str, limit: int = 200) -> dict:
    query = urlencode({"disease_id": disease_id, "limit": limit})
    with urllib.request.urlopen(f"{API_BASE_URL}/graph/relations?{query}", timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, object]] = []
    issue_rows: list[dict[str, object]] = []

    for disease_id in DISEASE_IDS:
        graph = fetch_graph(disease_id)
        nodes = graph["nodes"]
        edges = graph["edges"]
        node_ids = [node["id"] for node in nodes]
        edge_ids = [edge["id"] for edge in edges]
        node_id_counts = Counter(node_ids)
        edge_id_counts = Counter(edge_ids)
        node_id_set = set(node_ids)

        duplicate_node_ids = [node_id for node_id, count in node_id_counts.items() if count > 1]
        duplicate_edge_ids = [edge_id for edge_id, count in edge_id_counts.items() if count > 1]
        broken_edges = [
            edge
            for edge in edges
            if edge["source"] not in node_id_set or edge["target"] not in node_id_set
        ]

        label_counts = Counter(node["label"] for node in nodes)
        edge_type_counts = Counter(edge["type"] for edge in edges)
        candidate_edges = [edge for edge in edges if edge["type"] == "CANDIDATE_FOR"]
        supports_edges = [edge for edge in edges if edge["type"] == "SUPPORTS_DRUG"]
        target_edges = [edge for edge in edges if edge["type"] == "HAS_TARGET"]
        evidence_nodes = [node for node in nodes if node["label"] == "ImageEvidence"]
        target_nodes = [node for node in nodes if node["label"] == "TargetConcept"]

        summary_rows.append(
            {
                "disease_id": disease_id,
                "nodes": len(nodes),
                "edges": len(edges),
                "candidate_edges": len(candidate_edges),
                "support_edges": len(supports_edges),
                "target_edges": len(target_edges),
                "evidence_nodes": len(evidence_nodes),
                "target_nodes": len(target_nodes),
                "duplicate_node_ids": len(duplicate_node_ids),
                "duplicate_edge_ids": len(duplicate_edge_ids),
                "broken_edges": len(broken_edges),
                "node_labels": json.dumps(dict(sorted(label_counts.items())), ensure_ascii=False),
                "edge_types": json.dumps(dict(sorted(edge_type_counts.items())), ensure_ascii=False),
            }
        )

        for node_id in duplicate_node_ids:
            issue_rows.append({"disease_id": disease_id, "issue_type": "duplicate_node_id", "object_id": node_id, "detail": str(node_id_counts[node_id])})
        for edge_id in duplicate_edge_ids:
            issue_rows.append({"disease_id": disease_id, "issue_type": "duplicate_edge_id", "object_id": edge_id, "detail": str(edge_id_counts[edge_id])})
        for edge in broken_edges:
            issue_rows.append(
                {
                    "disease_id": disease_id,
                    "issue_type": "broken_edge_endpoint",
                    "object_id": edge["id"],
                    "detail": f"{edge['source']} -> {edge['target']}",
                }
            )

        if len(candidate_edges) == 0:
            issue_rows.append({"disease_id": disease_id, "issue_type": "missing_candidate_edges", "object_id": disease_id, "detail": "No CANDIDATE_FOR edges in API graph"})

    write_csv(
        OUT_DIR / "graph_api_summary_v1.csv",
        summary_rows,
        [
            "disease_id",
            "nodes",
            "edges",
            "candidate_edges",
            "support_edges",
            "target_edges",
            "evidence_nodes",
            "target_nodes",
            "duplicate_node_ids",
            "duplicate_edge_ids",
            "broken_edges",
            "node_labels",
            "edge_types",
        ],
    )
    write_csv(OUT_DIR / "graph_api_issues_v1.csv", issue_rows, ["disease_id", "issue_type", "object_id", "detail"])

    print("Graph API validation")
    for row in summary_rows:
        print(
            f"{row['disease_id']}: nodes={row['nodes']} edges={row['edges']} "
            f"candidate={row['candidate_edges']} support={row['support_edges']} target={row['target_edges']} "
            f"duplicate_nodes={row['duplicate_node_ids']} duplicate_edges={row['duplicate_edge_ids']} broken_edges={row['broken_edges']}"
        )
    print(f"Issues: {len(issue_rows)}")


if __name__ == "__main__":
    main()
