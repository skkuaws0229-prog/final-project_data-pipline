#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


WORKSPACE = Path(__file__).resolve().parent.parent
REPORT_DIR = WORKSPACE / "reports" / "lung_directive_ensemble"
LUNG_ROOT = WORKSPACE / "20260416_new_pre_project_biso_Lung"

PREDICTIONS_CSV = REPORT_DIR / "lung_directive_ensemble_predictions_detailed.csv"
DRUG_FEATURES = LUNG_ROOT / "data" / "drug_features.parquet"
GDSC_ANNOT = LUNG_ROOT / "curated_data" / "processed" / "gdsc_annotation.parquet"

OUT_FINAL = REPORT_DIR / "lung_directive_ensemble_top30_unseen_drug_finalized.csv"
OUT_AUDIT = REPORT_DIR / "lung_directive_ensemble_top30_unseen_drug_finalization_audit.csv"
OUT_SUMMARY = REPORT_DIR / "lung_directive_ensemble_top30_unseen_drug_finalization_summary.md"


def normalize_name(value: object) -> str:
    return str(value or "").strip().lower()


def load_ranked_candidates() -> pd.DataFrame:
    preds = pd.read_csv(PREDICTIONS_CSV)
    preds = preds[preds["eval_mode"] == "unseen_drug"].copy()

    ranked = (
        preds.groupby("canonical_drug_id", as_index=False)
        .agg(
            pred_ic50_weighted_mean=("ensemble_pred", "mean"),
            pred_ic50_weighted_std=("ensemble_pred", "std"),
            pred_ic50_weighted_min=("ensemble_pred", "min"),
            pred_ic50_weighted_max=("ensemble_pred", "max"),
            sample_count=("sample_id", "count"),
            ensemble_member_std_mean=("ensemble_member_std", "mean"),
            ensemble_member_std_max=("ensemble_member_std", "max"),
            target_raw_mean=("y_true", "mean"),
            XGBoost_mean=("XGBoost", "mean"),
            FTTransformer_mean=("FTTransformer", "mean"),
            CatBoost_mean=("CatBoost", "mean"),
            LightGBM_mean=("LightGBM", "mean"),
            ResidualMLP_mean=("ResidualMLP", "mean"),
        )
        .sort_values("pred_ic50_weighted_mean", ascending=True)
        .reset_index(drop=True)
    )
    ranked["rank"] = ranked.index + 1
    ranked["rank_pct"] = ranked["rank"] / len(ranked)

    features = pd.read_parquet(DRUG_FEATURES)[
        ["canonical_drug_id", "canonical_smiles", "canonical_smiles_raw", "drug_name_norm", "has_smiles"]
    ].copy()
    features["canonical_drug_id"] = features["canonical_drug_id"].astype(int)

    gdsc = pd.read_parquet(GDSC_ANNOT).copy()
    gdsc["canonical_drug_id"] = gdsc["DRUG_ID"].astype(int)
    keep_cols = [c for c in ["canonical_drug_id", "DRUG_NAME", "TARGET", "TARGET_PATHWAY", "SYNONYMS"] if c in gdsc.columns]
    gdsc = gdsc[keep_cols].drop_duplicates(subset=["canonical_drug_id"])

    ranked = ranked.merge(features, on="canonical_drug_id", how="left").merge(gdsc, on="canonical_drug_id", how="left")
    ranked["drug_name_display"] = ranked["DRUG_NAME"].fillna(ranked["drug_name_norm"]).fillna(ranked["canonical_drug_id"].astype(str))
    ranked["drug_name_key"] = ranked["drug_name_display"].map(normalize_name)
    ranked["has_smiles"] = ranked["has_smiles"].fillna(0).astype(int)
    return ranked


def finalize_top30(ranked: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    seen_names: set[str] = set()

    for _, row in ranked.iterrows():
        drug_name_key = row["drug_name_key"]
        if drug_name_key in seen_names:
            audit_rows.append(
                {
                    "canonical_drug_id": row["canonical_drug_id"],
                    "drug_name_display": row["drug_name_display"],
                    "rank": row["rank"],
                    "action": "skipped_duplicate_name",
                    "reason": "duplicate drug_name_display after normalization",
                }
            )
            continue

        if int(row["has_smiles"]) != 1 or pd.isna(row["canonical_smiles"]) or not str(row["canonical_smiles"]).strip():
            audit_rows.append(
                {
                    "canonical_drug_id": row["canonical_drug_id"],
                    "drug_name_display": row["drug_name_display"],
                    "rank": row["rank"],
                    "action": "skipped_missing_smiles",
                    "reason": "canonical_smiles unavailable",
                }
            )
            continue

        seen_names.add(drug_name_key)
        selected_rows.append(row.to_dict())
        audit_rows.append(
            {
                "canonical_drug_id": row["canonical_drug_id"],
                "drug_name_display": row["drug_name_display"],
                "rank": row["rank"],
                "action": "selected",
                "reason": "unique name and canonical_smiles available",
            }
        )
        if len(selected_rows) == 30:
            break

    finalized = pd.DataFrame(selected_rows).copy()
    finalized["raw_rank"] = finalized["rank"].astype(int)
    finalized["dedup_rank"] = range(1, len(finalized) + 1)
    finalized["top_model_vote_count"] = finalized[
        ["XGBoost_mean", "FTTransformer_mean", "CatBoost_mean", "LightGBM_mean", "ResidualMLP_mean"]
    ].rank(axis=0, method="min", ascending=True).le(30).sum(axis=1)
    finalized["confidence_grade"] = finalized["ensemble_member_std_mean"].apply(
        lambda x: "A" if x <= 0.35 else ("B" if x <= 0.55 else "C")
    )

    ordered = [
        "dedup_rank",
        "raw_rank",
        "canonical_drug_id",
        "drug_name_display",
        "pred_ic50_weighted_mean",
        "ensemble_member_std_mean",
        "top_model_vote_count",
        "confidence_grade",
        "pred_ic50_weighted_std",
        "pred_ic50_weighted_min",
        "pred_ic50_weighted_max",
        "sample_count",
        "rank_pct",
        "target_raw_mean",
        "XGBoost_mean",
        "FTTransformer_mean",
        "CatBoost_mean",
        "LightGBM_mean",
        "ResidualMLP_mean",
        "DRUG_NAME",
        "TARGET",
        "TARGET_PATHWAY",
        "SYNONYMS",
        "canonical_smiles",
        "canonical_smiles_raw",
        "drug_name_norm",
        "has_smiles",
    ]
    finalized = finalized[ordered]
    audit = pd.DataFrame(audit_rows)
    return finalized, audit


def build_summary(finalized: pd.DataFrame, audit: pd.DataFrame) -> str:
    skipped_smiles = audit[audit["action"] == "skipped_missing_smiles"].copy()
    lines = [
        "# LUNG Finalized Top30",
        "",
        "- Source: `reports/lung_directive_ensemble/lung_directive_ensemble_predictions_detailed.csv`",
        "- Rule: `unseen_drug` rank ascending, unique drug name, `canonical_smiles` required",
        "",
        "## Summary",
        "",
        f"- Finalized candidate count: `{len(finalized)}`",
        f"- Unique names: `{finalized['drug_name_display'].nunique()}`",
        f"- Canonical SMILES coverage: `{finalized['canonical_smiles'].notna().sum()}/{len(finalized)}`",
        "",
        "## Replacement Notes",
        "",
    ]
    if skipped_smiles.empty:
        lines.append("- No missing-SMILES candidates were skipped.")
    else:
        for _, row in skipped_smiles.iterrows():
            lines.append(f"- Skipped `{row['drug_name_display']}` (raw rank {int(row['rank'])}) because `canonical_smiles` was missing.")

    if len(finalized) >= 30:
        last = finalized.iloc[-1]
        lines.append(f"- Final slot filled by `{last['drug_name_display']}` from raw rank `{int(last['raw_rank'])}`.")

    lines += [
        "",
        "## Finalized Top30",
        "",
        finalized[["dedup_rank", "raw_rank", "drug_name_display", "pred_ic50_weighted_mean", "confidence_grade"]]
        .round(4)
        .to_markdown(index=False),
    ]
    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ranked = load_ranked_candidates()
    finalized, audit = finalize_top30(ranked)
    if len(finalized) != 30:
        raise RuntimeError(f"Expected 30 finalized candidates, found {len(finalized)}")

    finalized.to_csv(OUT_FINAL, index=False)
    audit.to_csv(OUT_AUDIT, index=False)
    OUT_SUMMARY.write_text(build_summary(finalized, audit), encoding="utf-8")

    print(f"wrote: {OUT_FINAL}")
    print(f"wrote: {OUT_AUDIT}")
    print(f"wrote: {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
