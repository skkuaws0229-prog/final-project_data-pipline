#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "03_normalized"
IMPORT = ROOT / "06_graph" / "import"
VALIDATION = ROOT / "06_graph" / "validation"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: str | None) -> str:
    return (value or "").strip()


def check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def main() -> None:
    source_candidates = read_csv(NORMALIZED / "drug_candidates.csv")
    source_evidence = read_csv(NORMALIZED / "image_modal_drug_evidence.csv")
    source_matches = read_csv(NORMALIZED / "image_modal_evidence_drug_matches.csv")
    source_clusters = read_csv(NORMALIZED / "image_modal_clusters.csv")
    source_diseases = read_csv(NORMALIZED / "diseases.csv")
    source_canonical_drugs = read_csv(NORMALIZED / "canonical_drugs.csv")
    source_drug_aliases = read_csv(NORMALIZED / "drug_aliases.csv")
    source_disease_aliases = read_csv(NORMALIZED / "disease_aliases.csv")

    graph_diseases = read_csv(IMPORT / "graph_diseases.csv")
    graph_drugs = read_csv(IMPORT / "graph_drugs.csv")
    graph_drug_aliases = read_csv(IMPORT / "graph_drug_aliases.csv")
    graph_disease_aliases = read_csv(IMPORT / "graph_disease_aliases.csv")
    graph_targets = read_csv(IMPORT / "graph_target_concepts.csv")
    graph_clusters = read_csv(IMPORT / "graph_image_clusters.csv")
    graph_evidence = read_csv(IMPORT / "graph_image_evidence.csv")
    candidate_edges = read_csv(IMPORT / "graph_candidate_for_edges.csv")
    candidate_target_edges = read_csv(IMPORT / "graph_candidate_target_edges.csv")
    cluster_evidence_edges = read_csv(IMPORT / "graph_cluster_evidence_edges.csv")
    evidence_drug_edges = read_csv(IMPORT / "graph_evidence_drug_edges.csv")
    evidence_target_edges = read_csv(IMPORT / "graph_evidence_target_edges.csv")

    disease_ids = {clean(row["disease_id"]) for row in graph_diseases}
    drug_ids = {clean(row["canonical_drug_id"]) for row in graph_drugs}
    target_ids = {clean(row["target_id"]) for row in graph_targets}
    cluster_ids = {clean(row["cluster_id"]) for row in graph_clusters}
    evidence_ids = {clean(row["evidence_id"]) for row in graph_evidence}

    candidate_ids = {clean(row["candidate_id"]) for row in candidate_edges}
    source_candidate_ids = {clean(row["candidate_id"]) for row in source_candidates}
    source_evidence_ids = {clean(row["evidence_id"]) for row in source_evidence}
    source_match_ids = {clean(row["evidence_id"]) for row in source_matches}
    source_cluster_ids = {clean(row["cluster_id"]) for row in source_clusters}
    graph_drug_alias_ids = {clean(row["alias_id"]) for row in graph_drug_aliases}
    source_drug_alias_ids = {clean(row["alias_id"]) for row in source_drug_aliases}
    graph_disease_alias_ids = {clean(row["alias_id"]) for row in graph_disease_aliases}
    source_disease_alias_ids = {clean(row["alias_id"]) for row in source_disease_aliases}

    checks = [
        check("Disease count preserved", len(graph_diseases) == len(source_diseases), f"{len(graph_diseases)} graph vs {len(source_diseases)} source"),
        check("Canonical drug count preserved", len(graph_drugs) == len(source_canonical_drugs), f"{len(graph_drugs)} graph vs {len(source_canonical_drugs)} source"),
        check("Drug alias count preserved", len(graph_drug_aliases) == len(source_drug_aliases), f"{len(graph_drug_aliases)} graph vs {len(source_drug_aliases)} source"),
        check("Disease alias count preserved", len(graph_disease_aliases) == len(source_disease_aliases), f"{len(graph_disease_aliases)} graph vs {len(source_disease_aliases)} source"),
        check("Candidate edge count preserved", len(candidate_edges) == len(source_candidates), f"{len(candidate_edges)} graph vs {len(source_candidates)} source"),
        check("Image evidence count preserved", len(graph_evidence) == len(source_evidence), f"{len(graph_evidence)} graph vs {len(source_evidence)} source"),
        check("Evidence drug edge count preserved", len(evidence_drug_edges) == len(source_matches), f"{len(evidence_drug_edges)} graph vs {len(source_matches)} source matches"),
        check("Cluster count preserved", len(graph_clusters) == len(source_clusters), f"{len(graph_clusters)} graph vs {len(source_clusters)} source"),
        check("Candidate ids preserved", candidate_ids == source_candidate_ids, f"missing={len(source_candidate_ids - candidate_ids)}, extra={len(candidate_ids - source_candidate_ids)}"),
        check("Evidence ids preserved", evidence_ids == source_evidence_ids, f"missing={len(source_evidence_ids - evidence_ids)}, extra={len(evidence_ids - source_evidence_ids)}"),
        check("Evidence match ids preserved", {clean(row['evidence_id']) for row in evidence_drug_edges} == source_match_ids, f"missing={len(source_match_ids - {clean(row['evidence_id']) for row in evidence_drug_edges})}"),
        check("Cluster ids preserved", cluster_ids == source_cluster_ids, f"missing={len(source_cluster_ids - cluster_ids)}, extra={len(cluster_ids - source_cluster_ids)}"),
        check("Drug alias ids preserved", graph_drug_alias_ids == source_drug_alias_ids, f"missing={len(source_drug_alias_ids - graph_drug_alias_ids)}, extra={len(graph_drug_alias_ids - source_drug_alias_ids)}"),
        check("Disease alias ids preserved", graph_disease_alias_ids == source_disease_alias_ids, f"missing={len(source_disease_alias_ids - graph_disease_alias_ids)}, extra={len(graph_disease_alias_ids - source_disease_alias_ids)}"),
    ]

    broken_refs: list[dict[str, str]] = []

    for row in candidate_edges:
        if clean(row["canonical_drug_id"]) not in drug_ids:
            broken_refs.append({"edge_file": "graph_candidate_for_edges.csv", "edge_id": clean(row["candidate_id"]), "missing_label": "Drug", "missing_id": clean(row["canonical_drug_id"])})
        if clean(row["disease_id"]) not in disease_ids:
            broken_refs.append({"edge_file": "graph_candidate_for_edges.csv", "edge_id": clean(row["candidate_id"]), "missing_label": "Disease", "missing_id": clean(row["disease_id"])})

    for row in graph_drug_aliases:
        if clean(row["canonical_drug_id"]) not in drug_ids:
            broken_refs.append({"edge_file": "graph_drug_aliases.csv", "edge_id": clean(row["alias_id"]), "missing_label": "Drug", "missing_id": clean(row["canonical_drug_id"])})

    for row in graph_disease_aliases:
        if clean(row["disease_id"]) not in disease_ids:
            broken_refs.append({"edge_file": "graph_disease_aliases.csv", "edge_id": clean(row["alias_id"]), "missing_label": "Disease", "missing_id": clean(row["disease_id"])})

    for row in candidate_target_edges:
        edge_id = clean(row["source_id"])
        if clean(row["canonical_drug_id"]) not in drug_ids:
            broken_refs.append({"edge_file": "graph_candidate_target_edges.csv", "edge_id": edge_id, "missing_label": "Drug", "missing_id": clean(row["canonical_drug_id"])})
        if clean(row["target_id"]) not in target_ids:
            broken_refs.append({"edge_file": "graph_candidate_target_edges.csv", "edge_id": edge_id, "missing_label": "TargetConcept", "missing_id": clean(row["target_id"])})

    for row in cluster_evidence_edges:
        if clean(row["cluster_id"]) not in cluster_ids:
            broken_refs.append({"edge_file": "graph_cluster_evidence_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "ImageCluster", "missing_id": clean(row["cluster_id"])})
        if clean(row["evidence_id"]) not in evidence_ids:
            broken_refs.append({"edge_file": "graph_cluster_evidence_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "ImageEvidence", "missing_id": clean(row["evidence_id"])})

    for row in evidence_drug_edges:
        if clean(row["evidence_id"]) not in evidence_ids:
            broken_refs.append({"edge_file": "graph_evidence_drug_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "ImageEvidence", "missing_id": clean(row["evidence_id"])})
        if clean(row["canonical_drug_id"]) not in drug_ids:
            broken_refs.append({"edge_file": "graph_evidence_drug_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "Drug", "missing_id": clean(row["canonical_drug_id"])})

    for row in evidence_target_edges:
        if clean(row["evidence_id"]) not in evidence_ids:
            broken_refs.append({"edge_file": "graph_evidence_target_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "ImageEvidence", "missing_id": clean(row["evidence_id"])})
        if clean(row["target_id"]) not in target_ids:
            broken_refs.append({"edge_file": "graph_evidence_target_edges.csv", "edge_id": clean(row["evidence_id"]), "missing_label": "TargetConcept", "missing_id": clean(row["target_id"])})

    checks.append(check("Graph edge endpoint references", not broken_refs, f"broken_refs={len(broken_refs)}"))

    blank_target_candidates = [
        row for row in source_candidates if not clean(row.get("target")) and not clean(row.get("target_pathway"))
    ]
    blank_target_evidence = [
        row for row in source_evidence if not clean(row.get("target")) and not clean(row.get("target_pathway"))
    ]

    target_omission_rows = [
        {"source": "drug_candidates", "rows_without_target_or_pathway": str(len(blank_target_candidates)), "interpretation": "expected omission from HAS_TARGET edges"},
        {"source": "image_modal_drug_evidence", "rows_without_target_or_pathway": str(len(blank_target_evidence)), "interpretation": "expected omission from MENTIONS_TARGET edges"},
    ]

    write_csv(VALIDATION / "graph_integrity_checks_v1.csv", checks, ["check", "status", "detail"])
    write_csv(VALIDATION / "graph_broken_references_v1.csv", broken_refs, ["edge_file", "edge_id", "missing_label", "missing_id"])
    write_csv(VALIDATION / "graph_target_omissions_v1.csv", target_omission_rows, ["source", "rows_without_target_or_pathway", "interpretation"])

    print("Graph integrity checks")
    for row in checks:
        print(f"{row['status']}: {row['check']} - {row['detail']}")
    print(f"Broken references: {len(broken_refs)}")
    print(f"Candidate rows without target/pathway: {len(blank_target_candidates)}")
    print(f"Evidence rows without target/pathway: {len(blank_target_evidence)}")


if __name__ == "__main__":
    main()
