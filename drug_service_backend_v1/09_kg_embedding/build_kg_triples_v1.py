#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT = ROOT / "06_graph" / "import"
OUT = ROOT / "09_kg_embedding"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean(value: str | None) -> str:
    return (value or "").strip()


def add_triple(rows: list[dict[str, str]], head: str, relation: str, tail: str, source_id: str) -> None:
    if head and relation and tail:
        rows.append({"head": head, "relation": relation, "tail": tail, "source_id": source_id})


def main() -> None:
    triples: list[dict[str, str]] = []

    for row in read_csv(IMPORT / "graph_candidate_for_edges.csv"):
        add_triple(triples, f"drug:{clean(row['canonical_drug_id'])}", "CANDIDATE_FOR", f"disease:{clean(row['disease_id'])}", clean(row["candidate_id"]))

    for row in read_csv(IMPORT / "graph_image_clusters.csv"):
        add_triple(triples, f"disease:{clean(row['disease_id'])}", "HAS_IMAGE_CLUSTER", f"cluster:{clean(row['cluster_id'])}", clean(row["cluster_id"]))

    for row in read_csv(IMPORT / "graph_cluster_evidence_edges.csv"):
        add_triple(triples, f"cluster:{clean(row['cluster_id'])}", "HAS_IMAGE_EVIDENCE", f"evidence:{clean(row['evidence_id'])}", clean(row["evidence_id"]))

    for row in read_csv(IMPORT / "graph_evidence_drug_edges.csv"):
        add_triple(triples, f"evidence:{clean(row['evidence_id'])}", "SUPPORTS_DRUG", f"drug:{clean(row['canonical_drug_id'])}", clean(row["evidence_id"]))

    for row in read_csv(IMPORT / "graph_candidate_target_edges.csv"):
        add_triple(triples, f"drug:{clean(row['canonical_drug_id'])}", "HAS_TARGET", f"target:{clean(row['target_id'])}", clean(row["source_id"]))

    for row in read_csv(IMPORT / "graph_evidence_target_edges.csv"):
        add_triple(triples, f"evidence:{clean(row['evidence_id'])}", "MENTIONS_TARGET", f"target:{clean(row['target_id'])}", clean(row["evidence_id"]))

    deduped = {(row["head"], row["relation"], row["tail"]): row for row in triples}
    triples = sorted(deduped.values(), key=lambda row: (row["relation"], row["head"], row["tail"]))

    entities = sorted({row["head"] for row in triples} | {row["tail"] for row in triples})
    relations = sorted({row["relation"] for row in triples})

    write_csv(OUT / "kg_triples_v1.csv", triples, ["head", "relation", "tail", "source_id"])
    write_csv(OUT / "kg_entities_v1.csv", [{"entity_id": entity, "entity_index": str(i)} for i, entity in enumerate(entities)], ["entity_id", "entity_index"])
    write_csv(OUT / "kg_relations_v1.csv", [{"relation": rel, "relation_index": str(i)} for i, rel in enumerate(relations)], ["relation", "relation_index"])

    print(f"triples={len(triples)} entities={len(entities)} relations={len(relations)}")


if __name__ == "__main__":
    main()

