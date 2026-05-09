#!/usr/bin/env python3
"""
Build the LUAD/LUNG directive ensemble described in LUNG_ensemble_directive.md.

Outputs:
  - weighted per-sample predictions for each eval mode
  - eval-mode metric summary
  - top drug recommendations with uncertainty / confidence grades
  - markdown summary report
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT
    / "20260415_preproject_choi_protocol_v1_bisotest-1"
    / "20260415_preproject_choi_protocol_v1_bisotest"
)
STEP4_ROOT = (
    SOURCE_ROOT
    / "results"
    / "20260424_multicancer_stad_protocol_rerun"
    / "step4_models"
    / "fs_a_stad_baseline"
)
OUT_DIR = ROOT / "reports" / "lung_directive_ensemble"

TRACK = "2C_numeric_smiles_context"
CANCER = "luad"
EVAL_MODES = ["cv", "groupcv", "scaffoldcv", "holdout", "unseen_drug"]


@dataclass(frozen=True)
class ModelSpec:
    name: str
    weight: float
    fmt: str
    base_dir: Path


MODEL_SPECS = [
    ModelSpec(
        name="XGBoost",
        weight=0.25,
        fmt="parquet",
        base_dir=STEP4_ROOT / "ml_step4_1" / CANCER / TRACK / "XGBoost",
    ),
    ModelSpec(
        name="FTTransformer",
        weight=0.22,
        fmt="csv",
        base_dir=STEP4_ROOT / "dl_step4_2_7model_full" / CANCER / TRACK / "FTTransformer",
    ),
    ModelSpec(
        name="CatBoost",
        weight=0.20,
        fmt="parquet",
        base_dir=STEP4_ROOT / "ml_step4_1" / CANCER / TRACK / "CatBoost",
    ),
    ModelSpec(
        name="LightGBM",
        weight=0.18,
        fmt="parquet",
        base_dir=STEP4_ROOT / "ml_step4_1" / CANCER / TRACK / "LightGBM",
    ),
    ModelSpec(
        name="ResidualMLP",
        weight=0.15,
        fmt="csv",
        base_dir=STEP4_ROOT / "dl_step4_2_7model_full" / CANCER / TRACK / "ResidualMLP",
    ),
]


def read_prediction_file(path: Path, fmt: str) -> pd.DataFrame:
    if fmt == "parquet":
        return pd.read_parquet(path)
    if fmt == "csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported format: {fmt}")


def load_model_predictions(model: ModelSpec, eval_mode: str) -> pd.DataFrame:
    path = model.base_dir / eval_mode / f"predictions.{model.fmt}"
    df = read_prediction_file(path, model.fmt)
    df = df.copy()
    df["sample_id"] = df["sample_id"].astype(str)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    keep = ["sample_id", "canonical_drug_id", "y_true", "split_id", "eval_mode", "track", "cancer", "y_pred"]
    df = df[keep].rename(columns={"y_pred": model.name})
    return df


def merge_eval_mode_predictions(eval_mode: str) -> pd.DataFrame:
    merged = None
    keys = ["sample_id", "canonical_drug_id", "split_id", "eval_mode", "track", "cancer"]

    for model in MODEL_SPECS:
        df = load_model_predictions(model, eval_mode)
        if merged is None:
            merged = df
        else:
            merged = merged.merge(df[keys + [model.name]], on=keys, how="inner")

    assert merged is not None
    return merged


def compute_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    y_true_np = y_true.to_numpy()
    y_pred_np = y_pred.to_numpy()

    spearman_val = spearmanr(y_true_np, y_pred_np).statistic
    pearson_val = pearsonr(y_true_np, y_pred_np).statistic
    kendall_val = kendalltau(y_true_np, y_pred_np).statistic
    rmse_val = float(np.sqrt(mean_squared_error(y_true_np, y_pred_np)))
    mae_val = mean_absolute_error(y_true_np, y_pred_np)
    r2_val = r2_score(y_true_np, y_pred_np)

    return {
        "spearman": float(spearman_val),
        "pearson": float(pearson_val),
        "kendall_tau": float(kendall_val),
        "rmse": float(rmse_val),
        "mae": float(mae_val),
        "r2": float(r2_val),
    }


def load_single_model_metric(model: ModelSpec, eval_mode: str) -> float:
    metrics_path = model.base_dir / eval_mode / "metrics.json"
    data = json.loads(metrics_path.read_text())
    return float(data["core_mean"]["spearman"])


def build_confidence_table(pred_df: pd.DataFrame) -> pd.DataFrame:
    model_names = [m.name for m in MODEL_SPECS]
    per_drug = (
        pred_df.groupby("canonical_drug_id", as_index=False)
        .agg(
            pred_ic50_weighted_mean=("ensemble_pred", "mean"),
            pred_ic50_weighted_std=("ensemble_pred", "std"),
            pred_ic50_weighted_min=("ensemble_pred", "min"),
            pred_ic50_weighted_max=("ensemble_pred", "max"),
            sample_count=("ensemble_pred", "size"),
            ensemble_member_std_mean=("ensemble_member_std", "mean"),
            ensemble_member_std_max=("ensemble_member_std", "max"),
            target_raw_mean=("y_true", "mean"),
            **{f"{name}_mean": (name, "mean") for name in model_names},
        )
    )
    per_drug["pred_ic50_weighted_std"] = per_drug["pred_ic50_weighted_std"].fillna(0.0)
    per_drug["rank"] = per_drug["pred_ic50_weighted_mean"].rank(method="first", ascending=True).astype(int)
    per_drug["rank_pct"] = per_drug["rank"] / len(per_drug)

    variance_low = per_drug["ensemble_member_std_mean"].quantile(0.33)
    variance_mid = per_drug["ensemble_member_std_mean"].quantile(0.66)

    votes = []
    for name in model_names:
        rank_col = f"{name}_rank"
        per_drug[rank_col] = per_drug[f"{name}_mean"].rank(method="average", ascending=True) / len(per_drug)
        votes.append((per_drug[rank_col] <= 0.10).astype(int))
    per_drug["top_model_vote_count"] = np.sum(votes, axis=0)

    def assign_grade(row: pd.Series) -> str:
        low_var = row["ensemble_member_std_mean"] <= variance_low
        mid_var = row["ensemble_member_std_mean"] <= variance_mid
        if row["top_model_vote_count"] == len(model_names) and low_var:
            return "A"
        if row["top_model_vote_count"] >= 3 and mid_var:
            return "B"
        return "C"

    per_drug["confidence_grade"] = per_drug.apply(assign_grade, axis=1)
    return per_drug.sort_values("pred_ic50_weighted_mean", ascending=True)


def load_drug_name_map() -> pd.DataFrame:
    candidates = [
        ROOT / "20260416_new_pre_project_biso_Lung" / "data" / "drug_features.parquet",
        ROOT / "20260416_new_pre_project_biso_Lung" / "curated_data" / "processed" / "gdsc_annotation.parquet",
    ]

    features = pd.read_parquet(candidates[0])[["canonical_drug_id", "drug_name_norm"]].copy()
    features["canonical_drug_id"] = features["canonical_drug_id"].astype(str)
    features = features.rename(columns={"drug_name_norm": "drug_name"})

    gdsc = pd.read_parquet(candidates[1])[["DRUG_ID", "DRUG_NAME", "TARGET", "TARGET_PATHWAY"]].copy()
    gdsc["canonical_drug_id"] = gdsc["DRUG_ID"].astype(str)
    gdsc = gdsc.drop(columns=["DRUG_ID"]).rename(
        columns={"DRUG_NAME": "drug_name_gdsc", "TARGET": "target", "TARGET_PATHWAY": "target_pathway"}
    )

    mapping = features.merge(gdsc, on="canonical_drug_id", how="left")
    mapping["drug_name_display"] = mapping["drug_name_gdsc"].fillna(mapping["drug_name"])
    return mapping.drop_duplicates(subset=["canonical_drug_id"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    drug_map = load_drug_name_map()

    metric_rows: list[dict[str, object]] = []
    detailed_outputs: list[pd.DataFrame] = []
    top_outputs: list[pd.DataFrame] = []

    model_names = [m.name for m in MODEL_SPECS]
    weights = np.array([m.weight for m in MODEL_SPECS], dtype=float)

    for eval_mode in EVAL_MODES:
        merged = merge_eval_mode_predictions(eval_mode)
        pred_matrix = merged[model_names].to_numpy()
        merged["ensemble_pred"] = pred_matrix @ weights
        merged["ensemble_member_mean"] = merged[model_names].mean(axis=1)
        merged["ensemble_member_std"] = merged[model_names].std(axis=1, ddof=0)
        merged["ensemble_member_range"] = merged[model_names].max(axis=1) - merged[model_names].min(axis=1)

        metrics = compute_metrics(merged["y_true"], merged["ensemble_pred"])
        single_scores = {m.name: load_single_model_metric(m, eval_mode) for m in MODEL_SPECS}
        best_single_name, best_single_spearman = max(single_scores.items(), key=lambda item: item[1])

        metric_rows.append(
            {
                "eval_mode": eval_mode,
                "ensemble_spearman": metrics["spearman"],
                "ensemble_pearson": metrics["pearson"],
                "ensemble_kendall_tau": metrics["kendall_tau"],
                "ensemble_rmse": metrics["rmse"],
                "ensemble_mae": metrics["mae"],
                "ensemble_r2": metrics["r2"],
                "best_single_model": best_single_name,
                "best_single_spearman": best_single_spearman,
                "spearman_gain_vs_best_single": metrics["spearman"] - best_single_spearman,
                "n_rows": len(merged),
            }
        )

        detailed = merged.copy()
        detailed["eval_mode"] = eval_mode
        detailed_outputs.append(detailed)

        drug_summary = build_confidence_table(merged)
        drug_summary["eval_mode"] = eval_mode
        drug_summary = drug_summary.merge(drug_map, on="canonical_drug_id", how="left")
        top_outputs.append(drug_summary.head(30))

    metrics_df = pd.DataFrame(metric_rows).sort_values("eval_mode")
    detailed_df = pd.concat(detailed_outputs, ignore_index=True)
    top_df = pd.concat(top_outputs, ignore_index=True)

    metrics_path = OUT_DIR / "lung_directive_ensemble_metrics.csv"
    detailed_path = OUT_DIR / "lung_directive_ensemble_predictions_detailed.csv"
    top_path = OUT_DIR / "lung_directive_ensemble_top30_by_eval_mode.csv"
    summary_path = OUT_DIR / "lung_directive_ensemble_summary.md"

    metrics_df.to_csv(metrics_path, index=False)
    detailed_df.to_csv(detailed_path, index=False)
    top_df.to_csv(top_path, index=False)

    group_row = metrics_df.loc[metrics_df["eval_mode"] == "groupcv"].iloc[0]
    scaffold_row = metrics_df.loc[metrics_df["eval_mode"] == "scaffoldcv"].iloc[0]
    holdout_top = top_df.loc[top_df["eval_mode"] == "holdout"].copy()
    unseen_top = top_df.loc[top_df["eval_mode"] == "unseen_drug"].copy()

    lines = [
        "# LUNG Directive Ensemble Output",
        "",
        "- Source directive: `/Users/skku_aws2_14/Downloads/LUNG_ensemble_directive.md`",
        f"- Cancer: `{CANCER}`",
        f"- Track: `{TRACK}`",
        "- Ensemble: 0.25 XGBoost + 0.22 FTTransformer + 0.20 CatBoost + 0.18 LightGBM + 0.15 ResidualMLP",
        "",
        "## Metrics",
        "",
        metrics_df.round(4).to_markdown(index=False),
        "",
        "## Key Readout",
        "",
        f"- GroupCV Spearman: `{group_row['ensemble_spearman']:.4f}` vs best single `{group_row['best_single_model']}` `{group_row['best_single_spearman']:.4f}`",
        f"- ScaffoldCV Spearman: `{scaffold_row['ensemble_spearman']:.4f}` vs best single `{scaffold_row['best_single_model']}` `{scaffold_row['best_single_spearman']:.4f}`",
        "",
        "## Holdout Top 10 Recommendations",
        "",
        holdout_top[
            [
                "rank",
                "canonical_drug_id",
                "drug_name_display",
                "pred_ic50_weighted_mean",
                "ensemble_member_std_mean",
                "top_model_vote_count",
                "confidence_grade",
            ]
        ]
        .head(10)
        .round(4)
        .to_markdown(index=False),
        "",
        "## Unseen Drug Top 10 Recommendations",
        "",
        unseen_top[
            [
                "rank",
                "canonical_drug_id",
                "drug_name_display",
                "pred_ic50_weighted_mean",
                "ensemble_member_std_mean",
                "top_model_vote_count",
                "confidence_grade",
            ]
        ]
        .head(10)
        .round(4)
        .to_markdown(index=False),
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {metrics_path}")
    print(f"Wrote: {detailed_path}")
    print(f"Wrote: {top_path}")
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
