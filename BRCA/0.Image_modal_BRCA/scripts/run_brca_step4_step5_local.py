#!/usr/bin/env python3
"""Run BRCA Step 4/5 reranking and ablation from local S3-downloaded files.

This script intentionally records the TCGA-slide-to-base-patient matching result.
The available BRCA base pipeline rows are GDSC cell lines, while the image
embeddings are TCGA WSI slides, so direct row-level matching is expected to be 0.
When that happens, we run the requested image ablation with a BRCA shard00 mean
embedding as the cancer-level image representative vector.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, KFold


BASE_FEATURE_COLS = [
    "ensemble_pred",
    "component_pred_std",
    "component_pred_mean",
]


@dataclass
class EvalResult:
    experiment: str
    eval_mode: str
    spearman: float
    rmse: float
    mae: float
    r2: float
    n_train_total: int
    n_test_total: int
    n_folds: int
    model: str
    image_strategy: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="brca_data")
    parser.add_argument(
        "--embedding-npy",
        default="output/embeddings_mid/shard00_merged/all_slide_embeddings_shard00_merged.npy",
    )
    parser.add_argument(
        "--embedding-manifest",
        default="output/embeddings_mid/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="results/brca_step4_step5_local_20260430_v1",
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--max-bin", type=int, default=128)
    return parser.parse_args()


def tcga_case_id(slide_id: str) -> str:
    fields = str(slide_id).split("-")
    if len(fields) >= 3 and fields[0] == "TCGA":
        return "-".join(fields[:3])
    return str(slide_id)


def canonicalize_id(value: str) -> str:
    return str(value).upper().replace("_", "-").strip()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def load_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, pd.DataFrame]:
    data_dir = Path(args.data_dir)
    eval_df = pd.read_csv(data_dir / "brca_directive_ensemble_A_groupcv_predictions.csv")
    top30_df = pd.read_csv(data_dir / "brca_directive_top30_tiered_candidates.csv")
    embeddings = np.load(args.embedding_npy)
    manifest = pd.read_csv(args.embedding_manifest)
    return eval_df, top30_df, embeddings, manifest


def build_mapping_report(eval_df: pd.DataFrame, manifest: pd.DataFrame, embeddings: np.ndarray) -> dict:
    manifest = manifest.copy()
    manifest["tcga_case_id"] = manifest["slide_id"].map(tcga_case_id)
    manifest["tcga_case_id_norm"] = manifest["tcga_case_id"].map(canonicalize_id)

    base_ids = pd.Series(eval_df["sample_id"].unique(), name="base_sample_id")
    base_norm = set(base_ids.map(canonicalize_id))
    tcga_norm = set(manifest["tcga_case_id_norm"])
    matched = sorted(base_norm & tcga_norm)

    return {
        "base_unique_sample_ids": int(base_ids.nunique()),
        "base_sample_id_examples": base_ids.head(15).tolist(),
        "tcga_unique_case_ids": int(manifest["tcga_case_id"].nunique()),
        "tcga_case_id_examples": manifest["tcga_case_id"].head(15).tolist(),
        "matched_patient_ids": len(matched),
        "matched_patient_id_examples": matched[:15],
        "direct_patient_slide_matching_used": False,
        "reason": (
            "Base pipeline rows use GDSC BRCA cell-line IDs, while image embeddings "
            "come from TCGA WSI patient slides. Direct patient-level matching has 0 rows."
        ),
        "embedding_shape": list(embeddings.shape),
        "embedding_nan_count": int(np.isnan(embeddings).sum()),
        "embedding_inf_count": int(np.isinf(embeddings).sum()),
    }


def metric_bundle(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    rho = spearmanr(y_true, y_pred).statistic
    if np.isnan(rho):
        rho = 0.0
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return {
        "spearman": float(rho),
        "rmse": rmse,
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def make_model(args: argparse.Namespace) -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(
        objective="regression",
        n_estimators=args.n_estimators,
        max_bin=args.max_bin,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.0,
        reg_lambda=1.0,
        random_state=args.random_state,
        n_jobs=-1,
        verbose=-1,
    )


def splitter(eval_mode: str, df: pd.DataFrame, random_state: int) -> Iterable[tuple[np.ndarray, np.ndarray]]:
    n = len(df)
    if eval_mode == "cv5":
        return KFold(n_splits=5, shuffle=True, random_state=random_state).split(np.arange(n))

    group_col = "canonical_drug_id" if eval_mode == "groupcv" else "scaffold_id"
    groups = df[group_col].fillna(-1).astype(str).to_numpy()
    n_groups = pd.Series(groups).nunique()
    n_splits = min(5, int(n_groups))
    if n_splits < 2:
        raise ValueError(f"{eval_mode} needs at least 2 groups, got {n_groups}")
    return GroupKFold(n_splits=n_splits).split(np.arange(n), groups=groups)


def build_feature_matrix(df: pd.DataFrame, experiment: str, mean_embedding: np.ndarray) -> tuple[np.ndarray, list[str]]:
    base_x = df[BASE_FEATURE_COLS].astype("float32").to_numpy()
    base_names = BASE_FEATURE_COLS[:]

    if experiment == "baseline_no_image":
        return base_x, base_names

    image_x = np.tile(mean_embedding.astype("float32"), (len(df), 1))
    image_names = [f"image_{i:04d}" for i in range(image_x.shape[1])]

    if experiment == "image_only":
        return image_x, image_names
    if experiment == "baseline_plus_image":
        return np.concatenate([base_x, image_x], axis=1), base_names + image_names
    raise ValueError(f"Unknown experiment: {experiment}")


def run_eval(
    df: pd.DataFrame,
    experiment: str,
    eval_mode: str,
    mean_embedding: np.ndarray,
    args: argparse.Namespace,
    image_strategy: str,
) -> EvalResult:
    x, _ = build_feature_matrix(df, experiment, mean_embedding)
    y = df["target"].astype("float32").to_numpy()
    preds = np.zeros(len(df), dtype="float32")
    folds = list(splitter(eval_mode, df, args.random_state))

    # Image-only is constant in this dataset because there is no TCGA-to-GDSC
    # direct match. A mean predictor is the honest lower-bound ablation.
    use_mean_predictor = experiment == "image_only" and np.all(np.nanstd(x, axis=0) == 0)

    for train_idx, test_idx in folds:
        if use_mean_predictor:
            preds[test_idx] = float(np.mean(y[train_idx]))
            continue
        model = make_model(args)
        model.fit(x[train_idx], y[train_idx])
        preds[test_idx] = model.predict(x[test_idx]).astype("float32")

    metrics = metric_bundle(y, preds)
    return EvalResult(
        experiment=experiment,
        eval_mode=eval_mode,
        spearman=metrics["spearman"],
        rmse=metrics["rmse"],
        mae=metrics["mae"],
        r2=metrics["r2"],
        n_train_total=sum(len(train) for train, _ in folds),
        n_test_total=sum(len(test) for _, test in folds),
        n_folds=len(folds),
        model="LightGBMRegressor" if not use_mean_predictor else "MeanPredictor_constant_image_only",
        image_strategy=image_strategy,
    )


def train_final_with_importance(
    df: pd.DataFrame,
    mean_embedding: np.ndarray,
    args: argparse.Namespace,
) -> tuple[lgb.LGBMRegressor, list[str], pd.DataFrame, dict]:
    x, feature_names = build_feature_matrix(df, "baseline_plus_image", mean_embedding)
    y = df["target"].astype("float32").to_numpy()
    model = make_model(args)
    model.fit(x, y)

    importances = np.asarray(model.feature_importances_, dtype="float64")
    imp_df = pd.DataFrame({"feature": feature_names, "importance": importances})
    total = float(importances.sum())
    image_total = float(imp_df.loc[imp_df["feature"].str.startswith("image_"), "importance"].sum())
    base_total = total - image_total
    summary = {
        "total_importance": total,
        "base_feature_importance": base_total,
        "image_feature_importance": image_total,
        "image_feature_importance_ratio": float(image_total / total) if total else 0.0,
        "n_image_features": int(imp_df["feature"].str.startswith("image_").sum()),
        "n_base_features": int((~imp_df["feature"].str.startswith("image_")).sum()),
    }
    return model, feature_names, imp_df.sort_values("importance", ascending=False), summary


def rerank_top30(
    train_df: pd.DataFrame,
    top30_df: pd.DataFrame,
    mean_embedding: np.ndarray,
    args: argparse.Namespace,
) -> pd.DataFrame:
    baseline_x, _ = build_feature_matrix(train_df, "baseline_no_image", mean_embedding)
    with_image_x, _ = build_feature_matrix(train_df, "baseline_plus_image", mean_embedding)
    y = train_df["target"].astype("float32").to_numpy()

    baseline_model = make_model(args).fit(baseline_x, y)
    with_image_model = make_model(args).fit(with_image_x, y)

    top = top30_df.copy()
    top_features = pd.DataFrame(
        {
            "ensemble_pred": top["drug_level_score"].astype("float32"),
            "component_pred_std": top["prediction_std_mean"].astype("float32"),
            "component_pred_mean": top["drug_level_score"].astype("float32"),
        }
    )
    top_base_x = top_features[BASE_FEATURE_COLS].to_numpy(dtype="float32")
    top_img_x = np.concatenate(
        [top_base_x, np.tile(mean_embedding.astype("float32"), (len(top), 1))],
        axis=1,
    )
    top["rerank_score_baseline"] = baseline_model.predict(top_base_x)
    top["rerank_score_with_image"] = with_image_model.predict(top_img_x)
    top["rerank_baseline_rank"] = top["rerank_score_baseline"].rank(ascending=False, method="first").astype(int)
    top["rerank_with_image_rank"] = top["rerank_score_with_image"].rank(ascending=False, method="first").astype(int)
    top["rank_delta_with_image_minus_baseline"] = top["rerank_with_image_rank"] - top["rerank_baseline_rank"]
    return top.sort_values("rerank_with_image_rank")


def write_report(
    output_dir: Path,
    metrics_df: pd.DataFrame,
    mapping_report: dict,
    top30_df: pd.DataFrame,
    feature_summary: dict,
) -> None:
    pivot = metrics_df.pivot(index="eval_mode", columns="experiment", values="spearman")
    delta_lines = []
    if {"baseline_no_image", "baseline_plus_image"}.issubset(pivot.columns):
        deltas = pivot["baseline_plus_image"] - pivot["baseline_no_image"]
        for eval_mode, delta in deltas.items():
            delta_lines.append(f"- {eval_mode}: Spearman delta = {delta:.6f}")

    changed = int((top30_df["rank_delta_with_image_minus_baseline"] != 0).sum())
    top_changed = top30_df.loc[
        top30_df["rank_delta_with_image_minus_baseline"] != 0,
        ["drug_name", "rerank_baseline_rank", "rerank_with_image_rank", "rank_delta_with_image_minus_baseline"],
    ].head(10)

    report = [
        "# BRCA Step 4/5 Local Reranking Report",
        "",
        "## Data Matching",
        "",
        f"- Base unique sample IDs: {mapping_report['base_unique_sample_ids']}",
        f"- TCGA unique case IDs: {mapping_report['tcga_unique_case_ids']}",
        f"- Direct matched patient IDs: {mapping_report['matched_patient_ids']}",
        f"- Matching note: {mapping_report['reason']}",
        "",
        "Because direct TCGA patient to GDSC cell-line row matching is zero, image ablation used the BRCA shard00 mean embedding repeated as a cancer-level representative image vector.",
        "",
        "## Spearman Change",
        "",
        *delta_lines,
        "",
        "## Ablation Metrics",
        "",
        metrics_df.to_markdown(index=False),
        "",
        "## Top 30 Rank Change",
        "",
        f"- Top30 drugs with changed rank after image features: {changed}/30",
        "",
        top_changed.to_markdown(index=False) if not top_changed.empty else "No Top30 rank changes.",
        "",
        "## Feature Importance",
        "",
        f"- Image feature importance ratio: {feature_summary['image_feature_importance_ratio']:.6f}",
        f"- Image importance total: {feature_summary['image_feature_importance']:.3f}",
        f"- Base importance total: {feature_summary['base_feature_importance']:.3f}",
        "",
    ]
    (output_dir / "brca_step4_step5_report_20260430_v1.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    eval_df, top30_df, embeddings, manifest = load_inputs(args)
    if embeddings.ndim != 2 or embeddings.shape[1] != 1536:
        raise ValueError(f"Expected merged image embedding shape (?, 1536), got {embeddings.shape}")
    if np.isnan(embeddings).any() or np.isinf(embeddings).any():
        raise ValueError("Embedding contains NaN or Inf")

    mapping_report = build_mapping_report(eval_df, manifest, embeddings)
    write_json(output_dir / "patient_slide_mapping_report_20260430_v1.json", mapping_report)

    mean_embedding = embeddings.mean(axis=0).astype("float32")
    image_strategy = "brca_shard00_mean_embedding_repeated_due_to_no_tcga_patient_rows"

    metric_rows: list[EvalResult] = []
    for eval_mode in ["cv5", "groupcv", "scaffoldcv"]:
        for experiment in ["baseline_no_image", "baseline_plus_image", "image_only"]:
            print(f"[run] {eval_mode} / {experiment}", flush=True)
            metric_rows.append(
                run_eval(eval_df, experiment, eval_mode, mean_embedding, args, image_strategy)
            )

    metrics_df = pd.DataFrame([row.__dict__ for row in metric_rows])
    metrics_df.to_csv(output_dir / "step4_reranking_metrics_20260430_v1.csv", index=False)
    metrics_df.to_csv(output_dir / "step5_ablation_comparison_20260430_v1.csv", index=False)
    write_json(
        output_dir / "step4_reranking_metrics_20260430_v1.json",
        {"records": metrics_df.to_dict(orient="records")},
    )

    _, _, importance_df, feature_summary = train_final_with_importance(eval_df, mean_embedding, args)
    importance_df.to_csv(output_dir / "feature_importance_full_20260430_v1.csv", index=False)
    write_json(output_dir / "feature_importance_summary_20260430_v1.json", feature_summary)

    top30_reranked = rerank_top30(eval_df, top30_df, mean_embedding, args)
    top30_reranked.to_csv(output_dir / "top30_rerank_comparison_20260430_v1.csv", index=False)

    write_report(output_dir, metrics_df, mapping_report, top30_reranked, feature_summary)

    print("[done] outputs:", output_dir, flush=True)
    print(metrics_df[["experiment", "eval_mode", "spearman", "rmse", "mae", "r2"]].to_string(index=False))
    print(json.dumps(feature_summary, indent=2))


if __name__ == "__main__":
    main()
