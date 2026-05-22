#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = ROOT / "03_normalized"
OUT_DIR = ROOT / "06_graph" / "import"
VALIDATION_DIR = ROOT / "06_graph" / "validation"


def read_csv(name: str) -> list[dict[str, str]]:
    with (NORMALIZED / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean(value: str | None) -> str:
    text = (value or "").strip()
    if text.lower() in {"nan", "none", "null", "na", "n/a"}:
        return ""
    return text


def normalize_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", clean(value).lower())
    return normalized


def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def add_target(targets: dict[str, dict[str, str]], concept_text: str, concept_type: str) -> str:
    text = clean(concept_text)
    normalized = normalize_text(text)
    target_id = stable_id("target", concept_type, normalized)
    targets.setdefault(
        target_id,
        {
            "target_id": target_id,
            "concept_text": text,
            "normalized_text": normalized,
            "concept_type": concept_type,
        },
    )
    return target_id


def main() -> None:
    diseases = read_csv("diseases.csv")
    canonical_drugs = read_csv("canonical_drugs.csv")
    drug_aliases = read_csv("drug_aliases.csv")
    disease_aliases = read_csv("disease_aliases.csv")
    candidates = read_csv("drug_candidates.csv")
    admet_rows = read_csv("admet_results.csv")
    clusters = read_csv("image_modal_clusters.csv")
    evidence_rows = read_csv("image_modal_drug_evidence.csv")
    evidence_matches = read_csv("image_modal_evidence_drug_matches.csv")

    canonical_by_source_drug_id = {
        clean(row["source_drug_id"]): clean(row["canonical_drug_id"])
        for row in drug_aliases
        if clean(row.get("source_drug_id"))
    }
    candidate_canonical_ids = {
        canonical_by_source_drug_id.get(clean(row["drug_id"]), "")
        for row in candidates
    }
    evidence_match_by_id = {clean(row["evidence_id"]): row for row in evidence_matches}
    admet_by_candidate_id = {clean(row["candidate_id"]): row for row in admet_rows}

    graph_diseases = [
        {
            "disease_id": clean(row["disease_id"]),
            "display_name": clean(row["display_name"]),
            "source_file": clean(row["source_file"]),
            "source_s3_key": clean(row["source_s3_key"]),
        }
        for row in diseases
    ]

    graph_drugs = []
    for row in canonical_drugs:
        canonical_id = clean(row["canonical_drug_id"])
        graph_drugs.append(
            {
                "canonical_drug_id": canonical_id,
                "primary_drug_name": clean(row["primary_drug_name"]),
                "primary_smiles": clean(row["primary_smiles"]),
                "primary_source_drug_id": clean(row["primary_source_drug_id"]),
                "drug_source_status": "candidate_table" if canonical_id in candidate_canonical_ids else "evidence_only",
            }
        )

    graph_drug_aliases = [
        {
            "alias_id": clean(row["alias_id"]),
            "canonical_drug_id": clean(row["canonical_drug_id"]),
            "source_drug_id": clean(row["source_drug_id"]),
            "alias_name": clean(row["alias_name"]),
            "normalized_alias": clean(row["normalized_alias"]),
            "alias_type": clean(row["alias_type"]),
        }
        for row in drug_aliases
    ]

    graph_disease_aliases = [
        {
            "alias_id": clean(row["alias_id"]),
            "disease_id": clean(row["disease_id"]),
            "alias": clean(row["alias"]),
            "normalized_alias": clean(row["normalized_alias"]),
        }
        for row in disease_aliases
    ]

    graph_clusters = [
        {
            "cluster_id": clean(row["cluster_id"]),
            "disease_id": clean(row["disease_id"]),
            "cluster_key": clean(row["cluster_key"]),
            "cluster_label": clean(row["cluster_label"]),
            "n_observations": clean(row["n_observations"]),
            "clinical_summary": clean(row["clinical_summary"]),
            "pathway_summary": clean(row["pathway_summary"]),
            "source_file": clean(row["source_file"]),
        }
        for row in clusters
    ]

    targets: dict[str, dict[str, str]] = {}
    candidate_for_edges: list[dict[str, str]] = []
    candidate_target_edges: list[dict[str, str]] = []

    for row in candidates:
        candidate_id = clean(row["candidate_id"])
        canonical_id = canonical_by_source_drug_id.get(clean(row["drug_id"]), "")
        if not canonical_id:
            continue
        admet = admet_by_candidate_id.get(candidate_id, {})
        candidate_for_edges.append(
            {
                "candidate_id": candidate_id,
                "canonical_drug_id": canonical_id,
                "disease_id": clean(row["disease_id"]),
                "rank": clean(row["rank"]),
                "tier": clean(row["tier"]),
                "score": clean(row["score"]),
                "evidence_summary": clean(row["evidence_summary"]),
                "safety_score": clean(admet.get("safety_score")),
                "verdict": clean(admet.get("verdict")),
                "admet_status": clean(admet.get("admet_status")),
                "hard_fail": clean(admet.get("hard_fail")),
                "hard_fail_reasons": clean(admet.get("hard_fail_reasons")),
                "soft_flags": clean(admet.get("soft_flags")),
                "source_file": clean(row["source_file"]),
                "source_row_number": clean(row["source_row_number"]),
            }
        )
        for field_name, relation_kind, concept_type in (
            ("target", "target", "raw_target"),
            ("target_pathway", "pathway", "raw_pathway"),
        ):
            value = clean(row.get(field_name))
            if not value:
                continue
            target_id = add_target(targets, value, concept_type)
            candidate_target_edges.append(
                {
                    "canonical_drug_id": canonical_id,
                    "target_id": target_id,
                    "source_kind": "candidate",
                    "source_id": candidate_id,
                    "disease_id": clean(row["disease_id"]),
                    "relation_kind": relation_kind,
                }
            )

    graph_evidence: list[dict[str, str]] = []
    cluster_evidence_edges: list[dict[str, str]] = []
    evidence_drug_edges: list[dict[str, str]] = []
    evidence_target_edges: list[dict[str, str]] = []

    for row in evidence_rows:
        evidence_id = clean(row["evidence_id"])
        match = evidence_match_by_id.get(evidence_id, {})
        canonical_id = clean(match.get("canonical_drug_id"))
        match_status = clean(match.get("match_status")) or "unmatched"

        graph_evidence.append(
            {
                "evidence_id": evidence_id,
                "disease_id": clean(row["disease_id"]),
                "cluster_id": clean(row["cluster_id"]),
                "drug_name": clean(row["drug_name"]),
                "rank": clean(row["rank"]),
                "tier": clean(row["tier"]),
                "target": clean(row["target"]),
                "target_pathway": clean(row["target_pathway"]),
                "evidence_text": clean(row["evidence_text"]),
                "source_file": clean(row["source_file"]),
                "match_status": match_status,
                "canonical_drug_id": canonical_id,
            }
        )

        if clean(row["cluster_id"]):
            cluster_evidence_edges.append(
                {
                    "cluster_id": clean(row["cluster_id"]),
                    "evidence_id": evidence_id,
                    "disease_id": clean(row["disease_id"]),
                    "source_file": clean(row["source_file"]),
                }
            )

        if canonical_id:
            evidence_drug_edges.append(
                {
                    "evidence_id": evidence_id,
                    "canonical_drug_id": canonical_id,
                    "match_status": match_status,
                    "drug_name": clean(row["drug_name"]),
                    "rank": clean(row["rank"]),
                    "tier": clean(row["tier"]),
                }
            )

        for field_name, relation_kind, concept_type in (
            ("target", "target", "raw_target"),
            ("target_pathway", "pathway", "raw_pathway"),
        ):
            value = clean(row.get(field_name))
            if not value:
                continue
            target_id = add_target(targets, value, concept_type)
            evidence_target_edges.append(
                {
                    "evidence_id": evidence_id,
                    "target_id": target_id,
                    "source_kind": "image_modal_evidence",
                    "source_id": evidence_id,
                    "disease_id": clean(row["disease_id"]),
                    "relation_kind": relation_kind,
                }
            )

    graph_targets = sorted(targets.values(), key=lambda row: (row["concept_type"], row["normalized_text"]))

    write_csv(
        OUT_DIR / "graph_diseases.csv",
        graph_diseases,
        ["disease_id", "display_name", "source_file", "source_s3_key"],
    )
    write_csv(
        OUT_DIR / "graph_drugs.csv",
        graph_drugs,
        ["canonical_drug_id", "primary_drug_name", "primary_smiles", "primary_source_drug_id", "drug_source_status"],
    )
    write_csv(
        OUT_DIR / "graph_drug_aliases.csv",
        graph_drug_aliases,
        ["alias_id", "canonical_drug_id", "source_drug_id", "alias_name", "normalized_alias", "alias_type"],
    )
    write_csv(
        OUT_DIR / "graph_disease_aliases.csv",
        graph_disease_aliases,
        ["alias_id", "disease_id", "alias", "normalized_alias"],
    )
    write_csv(
        OUT_DIR / "graph_target_concepts.csv",
        graph_targets,
        ["target_id", "concept_text", "normalized_text", "concept_type"],
    )
    write_csv(
        OUT_DIR / "graph_image_clusters.csv",
        graph_clusters,
        [
            "cluster_id",
            "disease_id",
            "cluster_key",
            "cluster_label",
            "n_observations",
            "clinical_summary",
            "pathway_summary",
            "source_file",
        ],
    )
    write_csv(
        OUT_DIR / "graph_image_evidence.csv",
        graph_evidence,
        [
            "evidence_id",
            "disease_id",
            "cluster_id",
            "drug_name",
            "rank",
            "tier",
            "target",
            "target_pathway",
            "evidence_text",
            "source_file",
            "match_status",
            "canonical_drug_id",
        ],
    )
    write_csv(
        OUT_DIR / "graph_candidate_for_edges.csv",
        candidate_for_edges,
        [
            "candidate_id",
            "canonical_drug_id",
            "disease_id",
            "rank",
            "tier",
            "score",
            "evidence_summary",
            "safety_score",
            "verdict",
            "admet_status",
            "hard_fail",
            "hard_fail_reasons",
            "soft_flags",
            "source_file",
            "source_row_number",
        ],
    )
    write_csv(
        OUT_DIR / "graph_candidate_target_edges.csv",
        candidate_target_edges,
        ["canonical_drug_id", "target_id", "source_kind", "source_id", "disease_id", "relation_kind"],
    )
    write_csv(
        OUT_DIR / "graph_cluster_evidence_edges.csv",
        cluster_evidence_edges,
        ["cluster_id", "evidence_id", "disease_id", "source_file"],
    )
    write_csv(
        OUT_DIR / "graph_evidence_drug_edges.csv",
        evidence_drug_edges,
        ["evidence_id", "canonical_drug_id", "match_status", "drug_name", "rank", "tier"],
    )
    write_csv(
        OUT_DIR / "graph_evidence_target_edges.csv",
        evidence_target_edges,
        ["evidence_id", "target_id", "source_kind", "source_id", "disease_id", "relation_kind"],
    )

    validation_rows = [
        {"artifact": "Disease nodes", "count": str(len(graph_diseases))},
        {"artifact": "Drug nodes", "count": str(len(graph_drugs))},
        {"artifact": "DrugAlias nodes", "count": str(len(graph_drug_aliases))},
        {"artifact": "DiseaseAlias nodes", "count": str(len(graph_disease_aliases))},
        {"artifact": "TargetConcept nodes", "count": str(len(graph_targets))},
        {"artifact": "ImageCluster nodes", "count": str(len(graph_clusters))},
        {"artifact": "ImageEvidence nodes", "count": str(len(graph_evidence))},
        {"artifact": "CANDIDATE_FOR edges", "count": str(len(candidate_for_edges))},
        {"artifact": "HAS_TARGET candidate edges", "count": str(len(candidate_target_edges))},
        {"artifact": "HAS_IMAGE_EVIDENCE edges", "count": str(len(cluster_evidence_edges))},
        {"artifact": "SUPPORTS_DRUG edges", "count": str(len(evidence_drug_edges))},
        {"artifact": "MENTIONS_TARGET evidence edges", "count": str(len(evidence_target_edges))},
    ]
    write_csv(VALIDATION_DIR / "graph_import_counts_v1.csv", validation_rows, ["artifact", "count"])

    print("Neo4j import CSV generated")
    for row in validation_rows:
        print(f"{row['artifact']}: {row['count']}")


if __name__ == "__main__":
    main()
