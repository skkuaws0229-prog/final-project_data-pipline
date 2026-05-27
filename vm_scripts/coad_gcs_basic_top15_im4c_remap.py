#!/usr/bin/env python3
"""Remap the new COAD GCS basic ADMET top15 onto existing image-modal clusters.

The script reuses existing im1/im2/im3/im4a/im4b outputs:
- im2 embeddings: 225 patients, 1536 dimensions
- im3 clusters: k=4
- im4b cluster pathway profiles

It does not rerun WSI collection or embedding. It produces a new im4c-style
cluster-drug recommendation package for the new GCS basic top15 candidates.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ADMET_TOP15 = Path("/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
DEFAULT_CLUSTER_PROFILES = Path("Colon/0.Image_modal_COAD/step_im4b/coad_cluster_pathway_profiles.csv")
DEFAULT_PRIOR_TIER = Path("Colon/0.Image_modal_COAD/step_im4c/coad_top30_admet_4tier_classification.csv")
DEFAULT_OUTPUT_DIR = Path("Colon/0.Image_modal_COAD/step_gcs_basic_top15_im4c_remap")

PATHWAY_DRIVER_MAP = {
    "ERK MAPK signaling": {"KRAS", "BRAF"},
    "PI3K/MTOR signaling": {"PIK3CA"},
    "DNA replication": {"TP53"},
    "Protein stability and degradation": {"TP53"},
}

TARGET_DRIVER_MAP = {
    "MEK1": {"KRAS", "BRAF"},
    "MEK2": {"KRAS", "BRAF"},
    "ERK": {"KRAS", "BRAF"},
    "TOP1": {"TP53"},
    "MTOR": {"PIK3CA"},
    "PI3K": {"PIK3CA"},
    "PROTEASOME": {"TP53"},
}


def normalize_name(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_semicolon(value: Any) -> set[str]:
    return {part.strip().upper() for part in str(value or "").split(";") if part.strip()}


def load_top15(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).head(15).copy()
    required = {"canonical_drug_id", "drug_name", "admet_filtered_rank", "admet_adjusted_score"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required top15 columns: {missing}")
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    df["drug_name_norm_join"] = df["drug_name"].map(normalize_name)
    return df


def load_prior_tier(path: Path) -> pd.DataFrame:
    prior = pd.read_csv(path).copy()
    prior["canonical_drug_id"] = prior["canonical_drug_id"].astype(str)
    prior["drug_name_norm_join"] = prior["DRUG_NAME"].map(normalize_name)
    keep = [
        "drug_name_norm_join",
        "crc_4tier",
        "crc_4tier_rationale",
        "clinical_tier",
        "verdict",
        "safety_score",
        "admet_category",
    ]
    return prior[[c for c in keep if c in prior.columns]].drop_duplicates("drug_name_norm_join")


def pathway_driver_hits(pathway: Any, target: Any, dominant_drivers: Any) -> set[str]:
    drivers = split_semicolon(dominant_drivers)
    hits: set[str] = set()
    pathway_text = str(pathway or "")
    target_text = str(target or "").upper()
    for key, mapped in PATHWAY_DRIVER_MAP.items():
        if key.lower() in pathway_text.lower():
            hits |= drivers & mapped
    for key, mapped in TARGET_DRIVER_MAP.items():
        if key in target_text:
            hits |= drivers & mapped
    return hits


def protocol_tier(row: pd.Series, prior_tier: str | None) -> tuple[str, str]:
    if prior_tier and str(prior_tier).strip() and str(prior_tier).lower() != "nan":
        return str(prior_tier), "carried_forward_from_existing_coad_4tier_protocol_prior"

    name = str(row.get("drug_name", ""))
    target = str(row.get("putative_target", ""))
    pathway = str(row.get("pathway_name", ""))
    if name.lower() == "irinotecan":
        return "Tier1", "protocol_rule_crc_established_reference_drug"
    if any(token in target.upper() for token in ["MEK", "ERK", "TOP1"]) or any(
        token in pathway.lower() for token in ["mapk", "dna replication"]
    ):
        return "Tier3", "provisional_research_candidate_by_crc_relevant_target_or_pathway"
    if any(token in pathway.lower() for token in ["pi3k", "mtor", "protein stability", "degradation"]):
        return "Tier3", "provisional_biology_supported_research_candidate_needs_verification"
    return "Tier4", "insufficient_existing_coad_image_modal_or_protocol_tier_evidence"


def admet_label(row: pd.Series) -> str:
    if bool(row.get("admet_strict_pass", False)):
        return "PASS"
    return "FAIL"


def score_match(
    tier: str,
    admet: str,
    driver_hits: set[str],
    pathway: Any,
    target: Any,
    cluster_keywords: Any,
) -> tuple[int, str]:
    score = 0
    keywords: list[str] = []
    if tier == "Tier1":
        score += 3
        keywords.append("tier1")
    elif tier in {"Tier2", "Tier3"}:
        score += 1
        keywords.append(tier.lower())
    if admet == "PASS":
        score += 1
        keywords.append("admet")
    if driver_hits:
        score += 2
        keywords.append("driver:" + "/".join(sorted(driver_hits)))
    text = f"{target} {pathway}".upper()
    if any(token in text for token in ["MEK", "ERK", "TOP1", "MTOR", "PI3K", "PROTEASOME"]):
        score += 1
        keywords.append("pathway")
    if "MSI" in str(cluster_keywords).upper() and any(token in text for token in ["TOP1", "DNA", "MEK", "ERK"]):
        score += 1
        keywords.append("cluster_context")
    return score, "/".join(keywords) if keywords else "review"


def build_recommendations(top15: pd.DataFrame, clusters: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    merged = top15.merge(prior, on="drug_name_norm_join", how="left")
    rows: list[dict[str, Any]] = []
    for _, cluster in clusters.sort_values("cluster").iterrows():
        for _, drug in merged.sort_values("admet_filtered_rank").iterrows():
            tier, tier_rationale = protocol_tier(drug, drug.get("crc_4tier"))
            admet = admet_label(drug)
            hits = pathway_driver_hits(drug.get("pathway_name"), drug.get("putative_target"), cluster.get("dominant_drivers"))
            match_score, matched_keywords = score_match(
                tier,
                admet,
                hits,
                drug.get("pathway_name"),
                drug.get("putative_target"),
                cluster.get("candidate_keywords"),
            )
            rows.append(
                {
                    "cluster": int(cluster["cluster"]),
                    "cluster_label": cluster.get("cluster_label"),
                    "n_patients": int(cluster.get("n_patients", 0)),
                    "dominant_drivers": cluster.get("dominant_drivers"),
                    "biology_hypothesis": cluster.get("biology_hypothesis"),
                    "canonical_drug_id": drug.get("canonical_drug_id"),
                    "drug_name": drug.get("drug_name"),
                    "admet_filtered_rank": int(drug.get("admet_filtered_rank")),
                    "crc_4tier": tier,
                    "crc_4tier_rationale": tier_rationale,
                    "target": drug.get("putative_target"),
                    "target_pathway": drug.get("pathway_name"),
                    "admet_verdict": admet,
                    "admet_adjusted_score": drug.get("admet_adjusted_score"),
                    "final_selection_score": drug.get("final_selection_score"),
                    "admet_good_signal_count": drug.get("admet_good_signal_count"),
                    "safety_score": drug.get("safety_score"),
                    "prior_image_modal_matched": pd.notna(drug.get("crc_4tier")),
                    "match_score": match_score,
                    "matched_keywords": matched_keywords,
                    "driver_overlap": ";".join(sorted(hits)),
                    "hypothesis": (
                        f"{drug.get('drug_name')} may fit cluster {int(cluster['cluster'])} "
                        f"({cluster.get('cluster_label')}) via {matched_keywords}."
                    ),
                    "classification_status": (
                        "protocol_prior_needs_current_regulatory_verification"
                        if pd.notna(drug.get("crc_4tier"))
                        else "provisional_im4c_remap_needs_current_regulatory_verification"
                    ),
                }
            )
    return pd.DataFrame(rows)


def summarize_by_drug(recs: pd.DataFrame) -> pd.DataFrame:
    summary = (
        recs.sort_values(["match_score", "admet_adjusted_score"], ascending=[False, False])
        .groupby(["canonical_drug_id", "drug_name"], as_index=False)
        .agg(
            admet_filtered_rank=("admet_filtered_rank", "min"),
            crc_4tier=("crc_4tier", "first"),
            best_match_score=("match_score", "max"),
            mean_match_score=("match_score", "mean"),
            matched_cluster_count=("cluster", "nunique"),
            best_clusters=("cluster_label", lambda s: " | ".join(dict.fromkeys(s.astype(str)))),
            matched_keywords=("matched_keywords", lambda s: " | ".join(dict.fromkeys(s.astype(str)))),
            target=("target", "first"),
            target_pathway=("target_pathway", "first"),
            admet_verdict=("admet_verdict", "first"),
            admet_adjusted_score=("admet_adjusted_score", "first"),
            classification_status=("classification_status", "first"),
        )
    )
    return summary.sort_values(["best_match_score", "admet_adjusted_score"], ascending=[False, False])


def write_report(recs: pd.DataFrame, drug_summary: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# COAD GCS Basic Top15 IM4c Remap",
        "",
        "Existing im1/im2/im3/im4a/im4b outputs were reused. Only the new ADMET top15 drug set was remapped to image-modal clusters.",
        "Tier values are protocol/provisional labels and still need current regulatory or clinical-trial verification before final clinical interpretation.",
        "",
        "## Summary",
        "",
        f"- Top15 drugs: {summary['n_drugs']}",
        f"- Image clusters reused: {summary['n_clusters']}",
        f"- Cluster-drug links: {summary['n_cluster_drug_links']}",
        f"- Prior image-modal tier matches carried forward: {summary['prior_image_modal_matched_drugs']}",
        "",
        "## Drug-Level Ranking",
        "",
        "| ADMET rank | Drug | Tier | Best match | Pathway | Status |",
        "|---:|---|---|---:|---|---|",
    ]
    for _, row in drug_summary.iterrows():
        lines.append(
            f"| {int(row['admet_filtered_rank'])} | {row['drug_name']} | {row['crc_4tier']} | "
            f"{int(row['best_match_score'])} | {row['target_pathway']} | {row['classification_status']} |"
        )
    lines.extend(
        [
            "",
            "## Agentic AI / Orchestrator Insertion Points",
            "",
            "- Preflight agent: verify that im2 embeddings, im3 clusters, im4a clinical tables, and top15 candidates are present and schema-compatible.",
            "- Evidence agent: collect current approval, guideline, clinical-trial, PubMed, and mechanism evidence for Tier1-4 verification.",
            "- Safety agent: review ADMET hard-fail flags, PAINS/Lipinski issues, and known toxicity signals before final ranking.",
            "- Report agent: synthesize cluster-specific hypotheses and flag weak or unsupported cluster-drug links for human review.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remap(admet_top15: Path, cluster_profiles: Path, prior_tier: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    top15 = load_top15(admet_top15)
    clusters = pd.read_csv(cluster_profiles)
    prior = load_prior_tier(prior_tier)
    recs = build_recommendations(top15, clusters, prior)
    drug_summary = summarize_by_drug(recs)

    recs_path = output_dir / "coad_gcs_basic_top15_im4c_cluster_recommendations.csv"
    drug_summary_path = output_dir / "coad_gcs_basic_top15_im4c_drug_summary.csv"
    json_path = output_dir / "coad_gcs_basic_top15_im4c_summary.json"
    report_path = output_dir / "coad_gcs_basic_top15_im4c_report.md"
    recs.to_csv(recs_path, index=False)
    drug_summary.to_csv(drug_summary_path, index=False)

    summary = {
        "step": "gcs_basic_top15_im4c_remap",
        "disease": "COAD",
        "admet_top15_source": str(admet_top15),
        "cluster_profiles_source": str(cluster_profiles),
        "prior_tier_source": str(prior_tier),
        "n_drugs": int(top15["drug_name"].nunique()),
        "n_clusters": int(clusters["cluster"].nunique()),
        "n_cluster_drug_links": int(len(recs)),
        "prior_image_modal_matched_drugs": int(recs.groupby("drug_name")["prior_image_modal_matched"].max().sum()),
        "tier_counts": drug_summary["crc_4tier"].value_counts().to_dict(),
        "top_drug_summary": drug_summary.head(15).to_dict("records"),
        "outputs": {
            "cluster_recommendations_csv": str(recs_path),
            "drug_summary_csv": str(drug_summary_path),
            "report_md": str(report_path),
        },
        "agentic_ai_recommended_after_this_task": [
            "preflight_schema_agent",
            "tier_evidence_verification_agent",
            "safety_admet_review_agent",
            "report_synthesis_agent",
        ],
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(recs, drug_summary, summary, report_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admet-top15", type=Path, default=DEFAULT_ADMET_TOP15)
    parser.add_argument("--cluster-profiles", type=Path, default=DEFAULT_CLUSTER_PROFILES)
    parser.add_argument("--prior-tier", type=Path, default=DEFAULT_PRIOR_TIER)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(json.dumps(remap(args.admet_top15, args.cluster_profiles, args.prior_tier, args.output_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
