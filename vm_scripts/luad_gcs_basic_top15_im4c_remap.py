#!/usr/bin/env python3
"""Remap the LUAD top15 candidate set onto existing LUAD image-modal clusters."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ADMET_TOP15 = Path("LUNG/workspace_reports/lung_step6_current_package/luad_gcs_basic_admet_filtered_top15.csv")
DEFAULT_CLUSTER_PROFILES = Path("LUNG/0.Image_modal_LUAD/step_im4b/luad_cluster_pathway_profiles.csv")
DEFAULT_PRIOR_TIER = Path("LUNG/0.Image_modal_LUAD/step_im4c/luad_top30_4tier_classification.csv")
DEFAULT_OUTPUT_DIR = Path("LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_im4c_remap")


def normalize_name(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    name_col = "DRUG_NAME" if "DRUG_NAME" in prior.columns else "drug_name_display"
    prior["drug_name_norm_join"] = prior[name_col].map(normalize_name)
    keep = [
        "drug_name_norm_join",
        "luad_4tier",
        "luad_4tier_rationale",
        "tier_name",
        "tier_validation_goal",
        "classification_status",
        "TARGET",
        "TARGET_PATHWAY",
    ]
    return prior[[c for c in keep if c in prior.columns]].drop_duplicates("drug_name_norm_join")


def cluster_driver_hits(cluster: pd.Series, target: Any, pathway: Any) -> str:
    text = f"{target} {pathway}".upper()
    hits: list[str] = []
    for driver in ["EGFR", "KRAS", "ALK", "STK11", "KEAP1", "TP53"]:
        rate = cluster.get(f"{driver}_mut_rate")
        if pd.notna(rate) and float(rate) >= 0.1 and driver in text:
            hits.append(driver)
    return ";".join(hits)


def score_match(tier: str, driver_overlap: str, cluster_targets: Any, drug_target: Any, score: Any) -> tuple[int, str]:
    match_score = 0
    tags: list[str] = []
    if tier == "Tier1":
        match_score += 3
        tags.append("tier1")
    elif tier in {"Tier2", "Tier3"}:
        match_score += 1
        tags.append(tier.lower())
    if driver_overlap:
        match_score += 2
        tags.append("driver:" + driver_overlap.replace(";", "/"))
    target_text = str(drug_target or "").upper()
    cluster_text = str(cluster_targets or "").upper()
    if any(token and token in cluster_text for token in re.split(r"[^A-Z0-9]+", target_text)):
        match_score += 1
        tags.append("target_context")
    if pd.notna(score) and float(score) >= 0.5:
        match_score += 1
        tags.append("ranking_score")
    return match_score, "/".join(tags) if tags else "review"


def build_recommendations(top15: pd.DataFrame, clusters: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
    merged = top15.merge(prior, on="drug_name_norm_join", how="left")
    rows: list[dict[str, Any]] = []
    for _, cluster in clusters.sort_values("cluster").iterrows():
        for _, drug in merged.sort_values("admet_filtered_rank").iterrows():
            raw_tier = drug.get("luad_4tier")
            tier = "Tier4" if pd.isna(raw_tier) or not str(raw_tier).strip() else str(raw_tier)
            raw_rationale = drug.get("luad_4tier_rationale")
            tier_rationale = (
                "No existing LUAD 4-tier protocol match for this new GCP top15 drug; defaulted to Tier4/review."
                if pd.isna(raw_rationale) or not str(raw_rationale).strip()
                else str(raw_rationale)
            )
            driver_overlap = cluster_driver_hits(cluster, drug.get("target") or drug.get("TARGET"), drug.get("TARGET_PATHWAY"))
            match_score, matched_keywords = score_match(
                tier,
                driver_overlap,
                cluster.get("Candidate_Targets"),
                drug.get("target") or drug.get("TARGET"),
                drug.get("admet_adjusted_score"),
            )
            cluster_id = int(float(cluster["cluster"]))
            rows.append(
                {
                    "cluster": cluster_id,
                    "cluster_label": cluster.get("Cluster_Label"),
                    "dominant_pathway": cluster.get("Dominant_Pathway"),
                    "candidate_targets": cluster.get("Candidate_Targets"),
                    "canonical_drug_id": drug.get("canonical_drug_id"),
                    "drug_name": drug.get("drug_name"),
                    "admet_filtered_rank": int(drug.get("admet_filtered_rank")),
                    "crc_4tier": tier,
                    "luad_4tier": tier,
                    "crc_4tier_rationale": tier_rationale,
                    "target": drug.get("target") or drug.get("TARGET"),
                    "target_pathway": drug.get("TARGET_PATHWAY") or drug.get("target"),
                    "admet_verdict": "PASS" if bool(drug.get("admet_strict_pass", True)) else "REVIEW",
                    "admet_adjusted_score": drug.get("admet_adjusted_score"),
                    "final_selection_score": drug.get("final_selection_score"),
                    "safety_score": drug.get("safety_score"),
                    "prior_image_modal_matched": pd.notna(drug.get("luad_4tier")),
                    "match_score": match_score,
                    "matched_keywords": matched_keywords,
                    "driver_overlap": driver_overlap,
                    "hypothesis": f"{drug.get('drug_name')} may fit LUAD cluster {cluster_id} via {matched_keywords}.",
                    "classification_status": (
                        drug.get("classification_status")
                        if pd.notna(drug.get("classification_status"))
                        else "luad_gcs_im4c_remap_unmatched_needs_evidence_agent_review"
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
            luad_4tier=("luad_4tier", "first"),
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


def write_report(drug_summary: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# LUAD GCS Basic Top15 IM4c Remap",
        "",
        "Existing LUAD image-modal outputs were reused. Only the prepared top15 drug set was remapped to image-modal clusters.",
        "",
        "## Summary",
        "",
        f"- Top15 drugs: {summary['n_drugs']}",
        f"- Image clusters reused: {summary['n_clusters']}",
        f"- Cluster-drug links: {summary['n_cluster_drug_links']}",
        f"- Prior LUAD tier matches carried forward: {summary['prior_image_modal_matched_drugs']}",
        "",
        "## Drug-Level Ranking",
        "",
        "| ADMET rank | Drug | Tier | Best match | Target | Status |",
        "|---:|---|---|---:|---|---|",
    ]
    for _, row in drug_summary.iterrows():
        lines.append(
            f"| {int(row['admet_filtered_rank'])} | {row['drug_name']} | {row['luad_4tier']} | "
            f"{int(row['best_match_score'])} | {row['target']} | {row['classification_status']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remap(admet_top15: Path, cluster_profiles: Path, prior_tier: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    top15 = load_top15(admet_top15)
    clusters = pd.read_csv(cluster_profiles)
    prior = load_prior_tier(prior_tier)
    recs = build_recommendations(top15, clusters, prior)
    drug_summary = summarize_by_drug(recs)

    recs_path = output_dir / "luad_gcs_basic_top15_im4c_cluster_recommendations.csv"
    drug_summary_path = output_dir / "luad_gcs_basic_top15_im4c_drug_summary.csv"
    json_path = output_dir / "luad_gcs_basic_top15_im4c_summary.json"
    report_path = output_dir / "luad_gcs_basic_top15_im4c_report.md"
    recs.to_csv(recs_path, index=False)
    drug_summary.to_csv(drug_summary_path, index=False)

    summary = {
        "step": "luad_gcs_basic_top15_im4c_remap",
        "disease": "LUAD",
        "admet_top15_source": str(admet_top15),
        "cluster_profiles_source": str(cluster_profiles),
        "prior_tier_source": str(prior_tier),
        "n_drugs": int(top15["drug_name"].nunique()),
        "n_clusters": int(clusters["cluster"].nunique()),
        "n_cluster_drug_links": int(len(recs)),
        "prior_image_modal_matched_drugs": int(recs.groupby("drug_name")["prior_image_modal_matched"].max().sum()),
        "tier_counts": drug_summary["luad_4tier"].value_counts().to_dict(),
        "top_drug_summary": drug_summary.head(15).to_dict("records"),
        "outputs": {
            "cluster_recommendations_csv": str(recs_path),
            "drug_summary_csv": str(drug_summary_path),
            "report_md": str(report_path),
        },
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(drug_summary, summary, report_path)
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
