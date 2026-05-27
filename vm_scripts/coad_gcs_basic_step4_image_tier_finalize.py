#!/usr/bin/env python3
"""Finalize COAD GCS basic top15 with existing image-modal/4-tier evidence.

This script intentionally does not make new regulatory claims. It carries
forward the existing COAD image-modal protocol tier when a top15 drug matches,
and marks unmatched drugs for image-modal remapping plus current clinical
verification.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_ADMET_TOP15 = Path("/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
DEFAULT_IMAGE_TIER = Path("Colon/0.Image_modal_COAD/step_im4c/coad_top30_admet_4tier_classification.csv")
DEFAULT_CLUSTER_RECS = Path("Colon/0.Image_modal_COAD/step_im4c/coad_final_drug_cluster_recommendations.csv")
DEFAULT_OUTPUT_DIR = Path("Colon/0.Image_modal_COAD/step_gcs_basic_top15_image_tier")


def normalize_name(value: Any) -> str:
    text = str(value or "").lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_unique(values: pd.Series) -> str:
    seen: list[str] = []
    for value in values.dropna().astype(str):
        value = value.strip()
        if value and value not in seen:
            seen.append(value)
    return " | ".join(seen)


def load_admet_top15(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"canonical_drug_id", "drug_name", "admet_filtered_rank", "admet_adjusted_score"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"ADMET top15 is missing required columns: {missing}")
    df = df.copy()
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    df["drug_name_norm_join"] = df["drug_name"].map(normalize_name)
    return df


def load_image_tier(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    df["drug_name_norm_join"] = df["DRUG_NAME"].map(normalize_name)
    keep = [
        "canonical_drug_id",
        "drug_name_norm_join",
        "DRUG_NAME",
        "TARGET",
        "TARGET_PATHWAY",
        "rank",
        "crc_4tier",
        "crc_4tier_rationale",
        "clinical_tier",
        "safety_score",
        "verdict",
        "admet_category",
        "tier",
        "tier_rationale",
    ]
    return df[[c for c in keep if c in df.columns]]


def load_cluster_evidence(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.copy()
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    df["drug_name_norm_join"] = df["drug_name"].map(normalize_name)
    grouped = (
        df.groupby("drug_name_norm_join", dropna=False)
        .agg(
            image_cluster_count=("cluster", "nunique"),
            image_clusters=("cluster_label", split_unique),
            image_dominant_drivers=("dominant_drivers", split_unique),
            image_biology_hypotheses=("biology_hypothesis", split_unique),
            image_drug_hypotheses=("hypothesis", split_unique),
            image_match_score_max=("match_score", "max"),
            image_match_score_mean=("match_score", "mean"),
            image_cluster_admet_verdict=("admet_verdict", split_unique),
            image_cluster_safety_score=("safety_score", "max"),
        )
        .reset_index()
    )
    return grouped


def choose_provisional_tier(row: pd.Series) -> tuple[str, str, str]:
    image_tier = str(row.get("image_crc_4tier") or "").strip()
    if image_tier and image_tier.lower() != "nan":
        return (
            image_tier,
            "carried_forward_from_existing_coad_image_modal_protocol_prior",
            "needs_current_regulatory_verification",
        )
    return (
        "Needs image-modal remapping",
        "new_gcs_basic_top15_candidate_not_found_in_existing_coad_image_modal_top30",
        "needs_image_modal_mapping_and_current_regulatory_verification",
    )


def write_report(final: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# COAD GCS Basic Top15 Image/Tier Finalization",
        "",
        "This file combines the new GCS basic pipeline ADMET top15 with the existing COAD image-modal 4-tier evidence.",
        "Tier values copied here are protocol priors, not newly verified current regulatory claims.",
        "",
        "## Summary",
        "",
        f"- ADMET top15 rows: {summary['admet_top15_rows']}",
        f"- Image-modal matched rows: {summary['image_modal_matched_rows']}",
        f"- Image-modal unmatched rows: {summary['image_modal_unmatched_rows']}",
        f"- Existing cluster-evidence matched rows: {summary['cluster_evidence_matched_rows']}",
        "",
        "## Top15",
        "",
        "| Rank | Drug | ADMET score | Image match | Provisional tier | Status |",
        "|---:|---|---:|---|---|---|",
    ]
    for _, row in final.sort_values("admet_filtered_rank").iterrows():
        lines.append(
            "| {rank} | {drug} | {score:.6f} | {match} | {tier} | {status} |".format(
                rank=int(row["admet_filtered_rank"]),
                drug=row["drug_name"],
                score=float(row["admet_adjusted_score"]),
                match="yes" if bool(row["image_modal_matched"]) else "no",
                tier=row["provisional_crc_4tier"],
                status=row["classification_status"],
            )
        )
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            "Run image-modal drug-cluster remapping for the 12 unmatched GCS basic top15 drugs before using the table as a final image-aware recommendation set.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def finalize(admet_top15: Path, image_tier: Path, cluster_recs: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    admet = load_admet_top15(admet_top15)
    tier = load_image_tier(image_tier).add_prefix("image_")
    tier = tier.rename(
        columns={
            "image_drug_name_norm_join": "drug_name_norm_join",
            "image_canonical_drug_id": "image_canonical_drug_id",
            "image_DRUG_NAME": "image_drug_name",
            "image_TARGET": "image_target",
            "image_TARGET_PATHWAY": "image_target_pathway",
            "image_rank": "image_prior_rank",
            "image_crc_4tier": "image_crc_4tier",
            "image_crc_4tier_rationale": "image_crc_4tier_rationale",
        }
    )
    clusters = load_cluster_evidence(cluster_recs)

    final = admet.merge(tier, on="drug_name_norm_join", how="left")
    final = final.merge(clusters, on="drug_name_norm_join", how="left")
    final["image_modal_matched"] = final["image_crc_4tier"].notna()
    final["cluster_evidence_matched"] = final["image_cluster_count"].notna()

    tier_rows = final.apply(choose_provisional_tier, axis=1, result_type="expand")
    final["provisional_crc_4tier"] = tier_rows[0]
    final["provisional_tier_rationale"] = tier_rows[1]
    final["classification_status"] = tier_rows[2]
    final["finalization_note"] = (
        "ADMET top15 from new GCS basic pipeline; image/tier evidence carried from existing "
        "COAD image-modal outputs only when matched by normalized drug name."
    )

    front_cols = [
        "admet_filtered_rank",
        "drug_name",
        "canonical_drug_id",
        "admet_adjusted_score",
        "final_selection_score",
        "admet_strict_pass",
        "admet_good_signal_count",
        "image_modal_matched",
        "cluster_evidence_matched",
        "provisional_crc_4tier",
        "classification_status",
        "provisional_tier_rationale",
        "image_crc_4tier",
        "image_crc_4tier_rationale",
        "image_drug_name",
        "image_target",
        "image_target_pathway",
        "image_prior_rank",
        "image_clinical_tier",
        "image_verdict",
        "image_safety_score",
        "image_admet_category",
        "image_cluster_count",
        "image_clusters",
        "image_dominant_drivers",
        "image_biology_hypotheses",
        "image_drug_hypotheses",
        "image_match_score_max",
        "image_match_score_mean",
        "finalization_note",
    ]
    ordered = [c for c in front_cols if c in final.columns] + [c for c in final.columns if c not in front_cols]
    final = final[ordered].sort_values("admet_filtered_rank")

    csv_path = output_dir / "coad_gcs_basic_top15_admet_image_4tier_classification.csv"
    json_path = output_dir / "coad_gcs_basic_top15_admet_image_4tier_summary.json"
    report_path = output_dir / "coad_gcs_basic_top15_admet_image_4tier_report.md"
    final.to_csv(csv_path, index=False)

    summary = {
        "step": "step4_image_tier_finalize",
        "disease": "COAD",
        "admet_top15_source": str(admet_top15),
        "image_tier_source": str(image_tier),
        "cluster_recommendation_source": str(cluster_recs),
        "output_csv": str(csv_path),
        "admet_top15_rows": int(len(final)),
        "image_modal_matched_rows": int(final["image_modal_matched"].sum()),
        "image_modal_unmatched_rows": int((~final["image_modal_matched"]).sum()),
        "cluster_evidence_matched_rows": int(final["cluster_evidence_matched"].sum()),
        "matched_drugs": final.loc[final["image_modal_matched"], "drug_name"].tolist(),
        "unmatched_drugs": final.loc[~final["image_modal_matched"], "drug_name"].tolist(),
        "tier_counts": final["provisional_crc_4tier"].value_counts(dropna=False).to_dict(),
        "classification_scope": "Existing image-modal protocol prior only; current regulatory/trial verification is not performed in this script.",
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(final, summary, report_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admet-top15", type=Path, default=DEFAULT_ADMET_TOP15)
    parser.add_argument("--image-tier", type=Path, default=DEFAULT_IMAGE_TIER)
    parser.add_argument("--cluster-recs", type=Path, default=DEFAULT_CLUSTER_RECS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = finalize(args.admet_top15, args.image_tier, args.cluster_recs, args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
