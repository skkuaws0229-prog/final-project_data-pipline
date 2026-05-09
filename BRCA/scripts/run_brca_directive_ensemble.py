#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


WORKSPACE = Path(__file__).resolve().parent.parent
DIRECTIVE_PATH = Path("/Users/skku_aws2_14/Downloads/BRCA_ensemble_directive.md")
OUTPUT_DIR = WORKSPACE / "20260428_new_BRCA_data"
RESULTS_ROOT = (
    WORKSPACE
    / "20260415_preproject_choi_protocol_v1_bisotest-1"
    / "20260415_preproject_choi_protocol_v1_bisotest"
    / "results"
    / "20260424_multicancer_stad_protocol_rerun"
    / "step4_models"
    / "fs_a_stad_baseline"
)
DRUG_CATALOG = WORKSPACE / "20260415_preproject_protocol_choi" / "data" / "drug_features_catalog.parquet"
ANNOTATED_TOP30 = (
    WORKSPACE
    / "20260415_preproject_choi_protocol_v1_bisotest-1"
    / "20260415_preproject_choi_protocol_v1_bisotest"
    / "results"
    / "20260424_multicancer_stad_protocol_rerun"
    / "step6_external_validation_prep"
    / "identifier_annotation_join"
    / "step6_top30_annotated_candidates.csv"
)

TRACK_DIR = {
    "2A": "2A_numeric",
    "2B": "2B_numeric_smiles",
    "2C": "2C_numeric_smiles_context",
}
FAMILY_DIR = {
    "ML": "ml_step4_1",
    "DL": "dl_step4_2_7model_full",
    "Graph": "graph_step4_3_2model_full",
}


@dataclass(frozen=True)
class Component:
    family: str
    model: str
    phase: str
    weight: float


CONFIGS = {
    "A": [
        Component("ML", "CatBoost", "2C", 0.30),
        Component("DL", "ResidualMLP", "2C", 0.25),
        Component("DL", "WideDeep", "2C", 0.20),
        Component("ML", "LightGBM", "2C", 0.15),
        Component("DL", "FTTransformer", "2C", 0.10),
    ],
    "B": [
        Component("ML", "CatBoost", "2C", 0.30),
        Component("DL", "ResidualMLP", "2C", 0.23),
        Component("ML", "LightGBM", "2C", 0.17),
        Component("DL", "WideDeep", "2C", 0.15),
        Component("DL", "ResidualMLP", "2B", 0.15),
    ],
}

EVAL_MODES = ("groupcv", "scaffoldcv", "holdout")


def fmt(v: float | None) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "NA"
    return f"{v:.4f}"


def locate_prediction_file(component: Component, eval_mode: str) -> Path:
    base = (
        RESULTS_ROOT
        / FAMILY_DIR[component.family]
        / "brca"
        / TRACK_DIR[component.phase]
        / component.model
        / eval_mode
    )
    csv_path = base / "predictions.csv"
    pq_path = base / "predictions.parquet"
    if csv_path.exists():
        return csv_path
    if pq_path.exists():
        return pq_path
    raise FileNotFoundError(f"Prediction file not found for {component} / {eval_mode}")


def read_prediction_file(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported prediction file: {path}")

    df = df.copy()
    rename_map = {}
    if "y_true" in df.columns:
        rename_map["y_true"] = "target"
    elif "target_raw" in df.columns:
        rename_map["target_raw"] = "target"
    elif "target" not in df.columns and "sensitivity_score" in df.columns:
        rename_map["sensitivity_score"] = "target"

    if "model_name" in df.columns and "model" not in df.columns:
        rename_map["model_name"] = "model"

    df = df.rename(columns=rename_map)
    required = {"sample_id", "canonical_drug_id", "y_pred", "target"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")

    df["sample_id"] = df["sample_id"].astype(str)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    keep_cols = ["sample_id", "canonical_drug_id", "target", "y_pred"]
    for col in ["split_id", "scaffold_id", "eval_mode", "track", "cancer"]:
        if col in df.columns:
            keep_cols.append(col)
    return df[keep_cols]


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "spearman": float(spearmanr(y_true, y_pred)[0]),
        "pearson": float(pearsonr(y_true, y_pred)[0]),
        "kendall_tau": float(kendalltau(y_true, y_pred)[0]),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def build_ensemble_predictions(config_name: str, eval_mode: str) -> tuple[pd.DataFrame, list[dict]]:
    components = CONFIGS[config_name]
    merged: pd.DataFrame | None = None
    manifest: list[dict] = []
    pred_cols: list[str] = []
    weight_map: dict[str, float] = {}

    for idx, comp in enumerate(components, start=1):
        pred_path = locate_prediction_file(comp, eval_mode)
        df = read_prediction_file(pred_path)
        pred_col = f"pred_{idx}_{comp.model}_{comp.phase}".replace("-", "_")
        df = df.rename(columns={"y_pred": pred_col})
        base_cols = ["sample_id", "canonical_drug_id", "target", pred_col]
        passthrough = [c for c in ["split_id", "scaffold_id", "eval_mode", "track", "cancer"] if c in df.columns]
        df = df[base_cols + passthrough]

        manifest.append(
            {
                "config": config_name,
                "eval_mode": eval_mode,
                "family": comp.family,
                "model": comp.model,
                "phase": comp.phase,
                "weight": comp.weight,
                "prediction_file": str(pred_path),
            }
        )

        if merged is None:
            merged = df
        else:
            shared = ["sample_id", "canonical_drug_id"]
            merged = merged.merge(df, on=shared, how="inner", suffixes=("", "_dup"))
            if "target_dup" in merged.columns:
                merged["target"] = merged["target"].fillna(merged["target_dup"])
                merged = merged.drop(columns=["target_dup"])
            for col in ["split_id", "scaffold_id", "eval_mode", "track", "cancer"]:
                dup_col = f"{col}_dup"
                if dup_col in merged.columns:
                    merged = merged.drop(columns=[dup_col])

        pred_cols.append(pred_col)
        weight_map[pred_col] = comp.weight

    assert merged is not None
    weights = np.array([weight_map[c] for c in pred_cols], dtype=float)
    pred_matrix = merged[pred_cols].to_numpy(dtype=float)
    merged["ensemble_pred"] = np.average(pred_matrix, axis=1, weights=weights)
    merged["component_pred_std"] = np.std(pred_matrix, axis=1)
    merged["component_pred_mean"] = np.mean(pred_matrix, axis=1)
    merged["config"] = config_name
    merged["component_count"] = len(pred_cols)
    merged["component_models"] = " | ".join(
        [f"{c.family}:{c.model}:{c.phase}:{c.weight:.2f}" for c in components]
    )
    return merged, manifest


def summarize_validation(config_name: str, eval_mode: str, df: pd.DataFrame) -> dict[str, float | str]:
    metrics = compute_metrics(df["target"].to_numpy(dtype=float), df["ensemble_pred"].to_numpy(dtype=float))
    return {
        "config": config_name,
        "eval_mode": eval_mode,
        "row_count": int(len(df)),
        **metrics,
        "component_pred_std_mean": float(df["component_pred_std"].mean()),
        "component_pred_std_median": float(df["component_pred_std"].median()),
    }


def choose_winner(validation_df: pd.DataFrame) -> str:
    pivot = validation_df.pivot(index="config", columns="eval_mode", values="spearman")
    candidates = sorted(pivot.index.tolist())
    return max(
        candidates,
        key=lambda c: (
            pivot.loc[c].get("groupcv", float("-inf")),
            pivot.loc[c].get("scaffoldcv", float("-inf")),
            pivot.loc[c].get("holdout", float("-inf")),
        ),
    )


def load_drug_mapping() -> pd.DataFrame:
    catalog = pd.read_parquet(DRUG_CATALOG).rename(
        columns={"DRUG_ID": "canonical_drug_id", "DRUG_NAME": "catalog_drug_name"}
    )
    catalog["canonical_drug_id"] = catalog["canonical_drug_id"].astype(str)

    ann = pd.read_csv(ANNOTATED_TOP30)
    ann = ann[["canonical_drug_id", "drug_name"]].dropna().drop_duplicates()
    ann["canonical_drug_id"] = ann["canonical_drug_id"].astype(str)

    merged = catalog.merge(ann, on="canonical_drug_id", how="left")
    merged["drug_name"] = merged["drug_name"].fillna(merged["catalog_drug_name"])
    merged["drug_name_norm"] = (
        merged["drug_name"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    return merged[["canonical_drug_id", "drug_name", "drug_name_norm", "canonical_smiles"]].drop_duplicates("canonical_drug_id")


def build_top30(df: pd.DataFrame, winner: str) -> pd.DataFrame:
    drug_map = load_drug_mapping()
    agg = (
        df.groupby("canonical_drug_id", as_index=False)
        .agg(
            drug_level_score=("ensemble_pred", "mean"),
            mean_prediction_score=("ensemble_pred", "mean"),
            median_prediction_score=("ensemble_pred", "median"),
            top_quantile_score=("ensemble_pred", lambda s: float(pd.Series(s).quantile(0.9))),
            n_samples=("ensemble_pred", "count"),
            prediction_std_mean=("component_pred_std", "mean"),
            prediction_std_median=("component_pred_std", "median"),
            target_mean=("target", "mean"),
        )
    )
    agg = agg.merge(drug_map, on="canonical_drug_id", how="left")
    agg["drug_name_norm"] = agg["drug_name_norm"].fillna("")
    agg = agg.sort_values(
        ["drug_level_score", "prediction_std_mean", "top_quantile_score", "canonical_drug_id"],
        ascending=[False, True, False, True],
    ).reset_index(drop=True)

    agg["duplicate_group"] = np.where(
        agg["drug_name_norm"].eq(""),
        "cid:" + agg["canonical_drug_id"].astype(str),
        "name:" + agg["drug_name_norm"],
    )
    deduped = agg.drop_duplicates(subset=["duplicate_group"], keep="first").copy()
    deduped = deduped.head(30).reset_index(drop=True)
    deduped["rank"] = np.arange(1, len(deduped) + 1)
    deduped["selected_config"] = winner
    deduped["ensemble_method"] = "directive_weighted_average"

    q1 = deduped["prediction_std_mean"].quantile(1 / 3) if len(deduped) else 0.0
    q2 = deduped["prediction_std_mean"].quantile(2 / 3) if len(deduped) else 0.0

    def grade(v: float) -> str:
        if v <= q1:
            return "A"
        if v <= q2:
            return "B"
        return "C"

    deduped["confidence_grade"] = deduped["prediction_std_mean"].map(grade)
    return deduped[
        [
            "rank",
            "canonical_drug_id",
            "drug_name",
            "canonical_smiles",
            "selected_config",
            "ensemble_method",
            "drug_level_score",
            "mean_prediction_score",
            "median_prediction_score",
            "top_quantile_score",
            "prediction_std_mean",
            "prediction_std_median",
            "confidence_grade",
            "n_samples",
            "target_mean",
        ]
    ]


def write_markdown_summary(validation_df: pd.DataFrame, winner: str, top30: pd.DataFrame) -> str:
    lines = [
        "# BRCA Directive Ensemble Summary",
        "",
        f"- Directive source: `{DIRECTIVE_PATH}`",
        "- Selection rule: higher GroupCV Spearman, then ScaffoldCV Spearman, then Holdout Spearman",
        "- Final recommendation split: holdout predictions of the winning configuration",
        "- Top30 dedup rule: same `drug_name` removed, highest-ranked one kept",
        "",
        "## Validation",
        "",
        "| Config | Eval Mode | Spearman | Pearson | RMSE | MAE | R2 | Mean Component Std | Rows |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for _, row in validation_df.sort_values(["eval_mode", "config"]).iterrows():
        lines.append(
            f"| {row['config']} | {row['eval_mode']} | {fmt(row['spearman'])} | {fmt(row['pearson'])} | "
            f"{fmt(row['rmse'])} | {fmt(row['mae'])} | {fmt(row['r2'])} | "
            f"{fmt(row['component_pred_std_mean'])} | {int(row['row_count'])} |"
        )

    lines += [
        "",
        f"## Winner",
        "",
        f"- Selected configuration: **{winner}**",
        "",
        "## Top 10 Preview",
        "",
        "| Rank | Drug ID | Drug Name | Score | Pred Std | Grade |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]
    for _, row in top30.head(10).iterrows():
        lines.append(
            f"| {int(row['rank'])} | {row['canonical_drug_id']} | {row['drug_name']} | "
            f"{fmt(row['drug_level_score'])} | {fmt(row['prediction_std_mean'])} | {row['confidence_grade']} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    directive_copy = OUTPUT_DIR / DIRECTIVE_PATH.name
    if DIRECTIVE_PATH.exists():
        shutil.copy2(DIRECTIVE_PATH, directive_copy)

    manifests: list[dict] = []
    validation_rows: list[dict] = []
    saved_prediction_files: list[dict] = []
    holdout_predictions_by_config: dict[str, pd.DataFrame] = {}

    for config_name in CONFIGS:
        for eval_mode in EVAL_MODES:
            ensemble_df, manifest = build_ensemble_predictions(config_name, eval_mode)
            manifests.extend(manifest)

            out_csv = OUTPUT_DIR / f"brca_directive_ensemble_{config_name}_{eval_mode}_predictions.csv"
            out_pq = OUTPUT_DIR / f"brca_directive_ensemble_{config_name}_{eval_mode}_predictions.parquet"
            ensemble_df.to_csv(out_csv, index=False)
            ensemble_df.to_parquet(out_pq, index=False)
            saved_prediction_files.append(
                {"config": config_name, "eval_mode": eval_mode, "csv": str(out_csv), "parquet": str(out_pq)}
            )

            validation_rows.append(summarize_validation(config_name, eval_mode, ensemble_df))
            if eval_mode == "holdout":
                holdout_predictions_by_config[config_name] = ensemble_df

    validation_df = pd.DataFrame(validation_rows)
    winner = choose_winner(validation_df)
    winner_holdout = holdout_predictions_by_config[winner]
    top30 = build_top30(winner_holdout, winner)

    validation_csv = OUTPUT_DIR / "brca_directive_ensemble_validation_summary.csv"
    validation_json = OUTPUT_DIR / "brca_directive_ensemble_validation_summary.json"
    top30_csv = OUTPUT_DIR / "brca_directive_top30_unique_candidates.csv"
    top30_json = OUTPUT_DIR / "brca_directive_top30_unique_candidates.json"
    manifest_json = OUTPUT_DIR / "brca_directive_ensemble_source_manifest.json"
    manifest_csv = OUTPUT_DIR / "brca_directive_ensemble_source_manifest.csv"
    summary_md = OUTPUT_DIR / "brca_directive_ensemble_summary.md"

    validation_df.to_csv(validation_csv, index=False)
    validation_json.write_text(validation_df.to_json(orient="records", indent=2), encoding="utf-8")
    top30.to_csv(top30_csv, index=False)
    top30_json.write_text(top30.to_json(orient="records", indent=2, force_ascii=False), encoding="utf-8")
    pd.DataFrame(manifests).drop_duplicates().to_csv(manifest_csv, index=False)
    manifest_json.write_text(
        json.dumps(
            {
                "directive_copy": str(directive_copy) if directive_copy.exists() else None,
                "component_prediction_sources": manifests,
                "saved_ensemble_prediction_files": saved_prediction_files,
                "winner": winner,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    summary_md.write_text(write_markdown_summary(validation_df, winner, top30), encoding="utf-8")

    print(f"Winner: {winner}")
    print(f"Validation summary: {validation_csv}")
    print(f"Top30 unique candidates: {top30_csv}")


if __name__ == "__main__":
    main()
