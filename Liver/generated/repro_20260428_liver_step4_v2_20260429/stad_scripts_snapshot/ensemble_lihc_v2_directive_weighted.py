#!/usr/bin/env python3
"""
LIHC v2 directive weighted ensemble (LIHC_v2_ensemble_directive.md).

Loads six fixed OOF vectors (same eval_mode, e.g. groupcv), applies weights, aggregates
per canonical_drug_id (mean prediction), ranks ascending (lower predicted response = higher priority
when target is IC50 / sensitivity-style; matches Lung directive convention).

Outputs under results/<RESULT_TAG>/ with *v2* in filenames.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Member:
    role: str
    family: str  # ml | dl
    stem: str
    model: str
    weight: float


# LIHC v2 ensemble directive — weights must sum to 1.0
MEMBERS: tuple[Member, ...] = (
    Member("main1", "dl", "stad_numeric_smiles_dl_v1", "DL_MLP_ResidualStyle", 0.25),
    Member("main2", "ml", "stad_numeric_smiles_ml_v1", "CatBoost", 0.25),
    Member("aux1", "dl", "stad_numeric_context_smiles_dl_v1", "DL_MLP_2x512", 0.17),
    Member("aux2", "dl", "stad_numeric_dl_v1", "DL_MLP_3x512", 0.15),
    Member("ml_aux", "ml", "stad_numeric_ml_v1", "XGBoost", 0.12),
    Member("stab", "dl", "stad_numeric_smiles_dl_v1", "DL_MLP_1024_512_256", 0.06),
)


def liver_train_table(project_root: Path) -> Path:
    return (
        project_root.parent.parent
        / "20260427_Liver"
        / "base_data"
        / "20260421_liver"
        / "data"
        / "processed"
        / "slim_inputs"
        / "train_table.parquet"
    )


def load_oof(project_root: Path, result_tag: str, eval_mode: str, m: Member) -> np.ndarray:
    oof_dir = project_root / "results" / result_tag / m.family / f"{m.stem}_{eval_mode}_oof"
    path = oof_dir / f"{m.model}.npy"
    if not path.is_file():
        raise FileNotFoundError(f"Missing OOF: {path}")
    return np.load(path).astype(np.float64)


def main() -> None:
    parser = argparse.ArgumentParser(description="LIHC v2 directive weighted OOF ensemble → Top30 drugs")
    parser.add_argument("--run-id", default="step4_lihc_v2_manual")
    parser.add_argument("--result-tag", default="20260428_liver_step4_v2")
    parser.add_argument("--eval-mode", default="groupcv", help="OOF folder suffix, e.g. groupcv")
    parser.add_argument("--top-k", type=int, default=30)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    tt_path = liver_train_table(project_root)
    if not tt_path.exists():
        raise FileNotFoundError(f"Missing train table: {tt_path}")

    df = pd.read_parquet(tt_path, columns=["sample_id", "canonical_drug_id"])
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)

    y_path = project_root / "data" / args.run_id / "y_train.npy"
    if not y_path.exists():
        raise FileNotFoundError(f"Missing {y_path}")

    wsum = sum(m.weight for m in MEMBERS)
    if abs(wsum - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {wsum}")

    preds_list: list[np.ndarray] = []
    manifest: list[dict[str, Any]] = []
    for m in MEMBERS:
        arr = load_oof(project_root, args.result_tag, args.eval_mode, m)
        if len(arr) != len(df):
            raise ValueError(f"Length mismatch {m.model}: oof={len(arr)} rows={len(df)}")
        preds_list.append(arr)
        manifest.append(
            {
                "role": m.role,
                "family": m.family,
                "stem": m.stem,
                "model": m.model,
                "weight": m.weight,
                "oof_path": str(
                    project_root
                    / "results"
                    / args.result_tag
                    / m.family
                    / f"{m.stem}_{args.eval_mode}_oof"
                    / f"{m.model}.npy"
                ),
            }
        )

    pred_mat = np.column_stack(preds_list)
    weights = np.array([m.weight for m in MEMBERS], dtype=np.float64)
    ensemble_row = pred_mat @ weights
    row_member_std = pred_mat.std(axis=1, ddof=0)

    member_labels = [f"{m.family}:{m.stem}:{m.model}" for m in MEMBERS]
    for i, lab in enumerate(member_labels):
        df[f"p_{i}"] = pred_mat[:, i]

    df["pred_ensemble_row"] = ensemble_row
    df["ensemble_member_std_row"] = row_member_std

    agg_map: dict[str, Any] = {
        "pred_ensemble_mean": ("pred_ensemble_row", "mean"),
        "ensemble_member_std_mean": ("ensemble_member_std_row", "mean"),
        "n_cell_drug_rows": ("pred_ensemble_row", "size"),
    }
    for i in range(len(MEMBERS)):
        agg_map[f"m{i}_mean"] = (f"p_{i}", "mean")

    drug_stats = df.groupby("canonical_drug_id", as_index=False).agg(**agg_map)

    member_cols = [f"m{i}_mean" for i in range(len(MEMBERS))]
    nd = len(drug_stats)
    vote_counts = np.zeros(nd, dtype=int)
    for c in member_cols:
        rk = drug_stats[c].rank(method="average", ascending=True) / float(nd)
        vote_counts += (rk <= 0.10).to_numpy(dtype=int)
    drug_stats["top_model_vote_count"] = vote_counts

    v_low = drug_stats["ensemble_member_std_mean"].quantile(0.33)
    v_mid = drug_stats["ensemble_member_std_mean"].quantile(0.66)

    def row_grade(r: pd.Series) -> str:
        vc = int(r["top_model_vote_count"])
        std = float(r["ensemble_member_std_mean"])
        if vc == len(MEMBERS) and std <= v_low:
            return "A"
        if vc >= 3 and std <= v_mid:
            return "B"
        return "C"

    drug_stats["confidence_grade"] = drug_stats.apply(row_grade, axis=1)

    drug_stats = drug_stats.sort_values("pred_ensemble_mean", ascending=True).reset_index(drop=True)
    drug_stats["rank_lihc_v2_directive"] = np.arange(1, len(drug_stats) + 1)

    drug_features_path = project_root / "data" / args.run_id / "drug_features.parquet"
    if drug_features_path.exists():
        feat = pd.read_parquet(
            drug_features_path,
            columns=["canonical_drug_id", "drug_name_norm", "drug_name"],
        )
        feat["canonical_drug_id"] = feat["canonical_drug_id"].astype(str)
        feat = feat.drop_duplicates("canonical_drug_id")
        drug_stats = drug_stats.merge(feat, on="canonical_drug_id", how="left")
        drug_stats["drug_name_display"] = drug_stats["drug_name"].fillna(drug_stats["drug_name_norm"])
    else:
        drug_stats["drug_name_display"] = ""

    out_dir = project_root / "results" / args.result_tag
    out_dir.mkdir(parents=True, exist_ok=True)

    top = drug_stats.head(int(args.top_k)).copy()

    top_path = out_dir / "lihc_v2_directive_weighted_ensemble_top30.csv"
    all_path = out_dir / "lihc_v2_directive_weighted_ensemble_all_drugs.csv"
    summary_path = out_dir / "lihc_v2_directive_weighted_ensemble_summary.json"

    drug_stats.to_csv(all_path, index=False)
    top.to_csv(top_path, index=False)

    summary = {
        "directive": "LIHC_v2_ensemble_directive.md (weighted average of 6 OOF models)",
        "ensemble_name": "LIHC_directive_weighted_v2",
        "run_id": args.run_id,
        "result_tag": args.result_tag,
        "eval_mode": args.eval_mode,
        "n_train_rows": int(len(df)),
        "n_unique_drugs": int(len(drug_stats)),
        "weights_sum_check": float(wsum),
        "members": manifest,
        "outputs": {
            "top30_csv": str(top_path),
            "all_drugs_csv": str(all_path),
        },
        "quantiles_for_grade": {"variance_low_q33": float(v_low), "variance_mid_q66": float(v_mid)},
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote {top_path}")
    print(f"Wrote {all_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
