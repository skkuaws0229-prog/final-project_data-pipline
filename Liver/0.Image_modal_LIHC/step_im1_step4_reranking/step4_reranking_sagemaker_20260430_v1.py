#!/usr/bin/env python3
"""Stage-2 LightGBM re-ranking with four evaluation modes for SageMaker."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from scripts.sagemaker_common_20260430_v1 import (
    PIPELINE_TAG,
    attach_patient_embeddings,
    embedding_columns,
    evaluate_regressor,
    ensure_processing_output_dirs,
    make_lgbm,
    patient_embedding_table,
    save_json,
    setup_logging,
    smiles_to_scaffold,
    load_slide_embeddings,
)

EVAL_MODES = ["holdout", "cv5", "groupcv", "scaffoldcv"]


def find_existing_files(existing_dir: Path) -> tuple[Path, Path]:
    top30 = next(existing_dir.rglob("*top30*tiered*candidates*.csv"), None)
    holdout = next(existing_dir.rglob("*holdout*predictions*.csv"), None)
    if top30 is None:
        raise FileNotFoundError(f"Top30 candidate CSV not found under {existing_dir}")
    if holdout is None:
        raise FileNotFoundError(f"Holdout prediction CSV not found under {existing_dir}")
    return top30, holdout


def feature_frame(df: pd.DataFrame, emb_cols: list[str], include_image: bool = True) -> pd.DataFrame:
    cols = [c for c in ["ensemble_pred", "component_pred_std", "ensemble_member_std"] if c in df.columns]
    if include_image:
        cols += emb_cols
    if not cols:
        raise ValueError("No feature columns available")
    return df[cols].astype(np.float32)


def eval_groups(df: pd.DataFrame, mode: str) -> pd.Series | None:
    if mode == "groupcv":
        return df["canonical_drug_id"].astype(str)
    if mode == "scaffoldcv":
        if "canonical_smiles" in df.columns:
            return df["canonical_smiles"].map(smiles_to_scaffold).replace("", np.nan).fillna(df["canonical_drug_id"].astype(str))
        return df["canonical_drug_id"].astype(str)
    return None


def rerank_top30(top30: pd.DataFrame, patient_embeddings: pd.DataFrame, model, feature_cols: list[str], emb_cols: list[str]) -> pd.DataFrame:
    rows = []
    patients = patient_embeddings["patient_barcode"].tolist()
    for _, drug in top30.iterrows():
        for _, emb in patient_embeddings.iterrows():
            row = drug.to_dict()
            row["patient_barcode"] = emb["patient_barcode"]
            for col in emb_cols:
                row[col] = float(emb[col])
            row["ensemble_pred"] = float(drug.get("drug_level_score", drug.get("pred_ic50_weighted_mean", drug.get("ensemble_pred", 0.0))))
            row["component_pred_std"] = float(drug.get("prediction_std_mean", drug.get("ensemble_member_std_mean", 0.0)))
            row["ensemble_member_std"] = row["component_pred_std"]
            rows.append(row)
    expanded = pd.DataFrame(rows)
    preds = model.predict(expanded[feature_cols].astype(np.float32))
    expanded["stage2_pred"] = preds
    agg = expanded.groupby("canonical_drug_id", as_index=False).agg(
        stage2_pred_mean=("stage2_pred", "mean"),
        stage2_pred_std=("stage2_pred", "std"),
        n_patients=("patient_barcode", "nunique"),
    )
    out = top30.merge(agg, on="canonical_drug_id", how="left")
    out["rerank_score"] = -out["stage2_pred_mean"]
    out["reranked_rank"] = out["rerank_score"].rank(ascending=False, method="first").astype(int)
    return out.sort_values("reranked_rank")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing-dir", type=Path, default=Path("/opt/ml/processing/input/existing"))
    parser.add_argument("--embedding-path", type=Path, default=Path("/opt/ml/processing/input/embeddings/slide_embeddings"))
    parser.add_argument("--output-dir", type=Path, default=Path("/opt/ml/processing/output/results/reranking"))
    parser.add_argument("--processing-output-base", type=Path, default=None)
    parser.add_argument("--log-dir", type=Path, default=None)
    args = parser.parse_args()

    output_base = args.processing_output_base or args.output_dir.parents[1]
    ensure_processing_output_dirs(output_base)
    logger = setup_logging(args.log_dir or output_base / "logs", "step4_reranking_sagemaker")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    top30_path, holdout_path = find_existing_files(args.existing_dir)
    top30 = pd.read_csv(top30_path)
    holdout = pd.read_csv(holdout_path)
    logger.info("Loaded top30=%d holdout=%d", len(top30), len(holdout))

    slide_embeddings = load_slide_embeddings(args.embedding_path)
    patient_embeddings = patient_embedding_table(slide_embeddings)
    logger.info("Loaded patient embeddings: patients=%d", len(patient_embeddings))
    train_df = attach_patient_embeddings(holdout, patient_embeddings, id_col="sample_id")
    if "canonical_smiles" not in train_df.columns and "canonical_smiles" in top30.columns:
        train_df = train_df.merge(top30[["canonical_drug_id", "canonical_smiles"]].drop_duplicates(), on="canonical_drug_id", how="left")

    emb_cols = embedding_columns(patient_embeddings)
    X = feature_frame(train_df, emb_cols, include_image=True)
    target_col = "target" if "target" in train_df.columns else "y_true"
    if target_col not in train_df.columns:
        raise KeyError("Expected a target column named 'target' or 'y_true'")
    y = train_df[target_col].values.astype(np.float32)
    comparison = []
    for mode in EVAL_MODES:
        metrics, _ = evaluate_regressor(X, y, mode, eval_groups(train_df, mode))
        payload = {"eval_mode": mode, **metrics, "n_features": int(X.shape[1]), "image_embedding": "patient_level_zero_for_unmapped_gdsc"}
        save_json(args.output_dir / f"reranking_{mode}_{PIPELINE_TAG}.json", payload)
        comparison.append(payload)
        logger.info("[%s] spearman=%.4f rmse=%.4f r2=%.4f", mode, metrics["spearman"], metrics["rmse"], metrics["r2"])

        final_model = make_lgbm()
        final_model.fit(X, y)
        reranked = rerank_top30(top30, patient_embeddings, final_model, list(X.columns), emb_cols)
        reranked.to_csv(args.output_dir / f"reranked_top30_{mode}_{PIPELINE_TAG}.csv", index=False)

    pd.DataFrame(comparison).to_csv(args.output_dir / f"reranking_comparison_{PIPELINE_TAG}.csv", index=False)
    final_model = make_lgbm()
    final_model.fit(X, y)
    with (args.output_dir / f"reranking_model_{PIPELINE_TAG}.pkl").open("wb") as f:
        pickle.dump({"model": final_model, "feature_cols": list(X.columns)}, f)
    logger.info("Step 4 complete: outputs=%s", args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
