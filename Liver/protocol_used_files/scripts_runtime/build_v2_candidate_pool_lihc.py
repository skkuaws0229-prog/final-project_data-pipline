#!/usr/bin/env python3
"""
v2 formal-start: build LIHC candidate pool from full liver processed tables.

This is a pre-Step4 artifact to guarantee HCC approved drugs are present in the
candidate universe before model scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HCC_APPROVED = {
    "sorafenib",
    "lenvatinib",
    "regorafenib",
    "cabozantinib",
    "ramucirumab",
    "nivolumab",
    "pembrolizumab",
    "atezolizumab",
    "bevacizumab",
    "durvalumab",
    "tremelimumab",
    "ipilimumab",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    liver_proc = (
        root.parents[0]
        / "20260427_Liver"
        / "base_data"
        / "20260421_liver"
        / "data"
        / "processed"
    )
    train_path = liver_proc / "slim_inputs" / "train_table.parquet"
    drug_master_path = liver_proc / "standardized" / "drug_master.parquet"

    if not train_path.is_file():
        raise FileNotFoundError(f"Missing {train_path}")
    if not drug_master_path.is_file():
        raise FileNotFoundError(f"Missing {drug_master_path}")

    train = pd.read_parquet(train_path, columns=["canonical_drug_id", "drug_name", "label_regression", "canonical_smiles"])
    train["canonical_drug_id"] = train["canonical_drug_id"].astype(str)
    train["drug_name"] = train["drug_name"].astype(str)
    train["drug_name_norm"] = train["drug_name"].str.strip().str.lower()

    agg = (
        train.groupby(["canonical_drug_id", "drug_name", "drug_name_norm"], as_index=False)
        .agg(
            n_pairs=("canonical_drug_id", "size"),
            li_hc_label_mean=("label_regression", "mean"),
            li_hc_label_median=("label_regression", "median"),
            canonical_smiles=("canonical_smiles", "first"),
        )
    )
    agg["hcc_approved"] = agg["drug_name_norm"].isin(HCC_APPROVED)

    # "formal-start" proxy ranking before Step4 re-scoring:
    # lower response label (proxy IC50 axis in this project) gets higher priority.
    agg = agg.sort_values(["li_hc_label_mean", "li_hc_label_median"], ascending=[True, True]).reset_index(drop=True)
    agg["rank_proxy_v2"] = range(1, len(agg) + 1)

    res = root / "results"
    res.mkdir(parents=True, exist_ok=True)
    pool_csv = res / "lihc_candidate_pool_v2.csv"
    agg.to_csv(pool_csv, index=False)

    top50 = agg.head(50).copy()
    top50["in_top50_v2"] = True
    top50_csv = res / "lihc_top50_candidate_pre_step4_v2.csv"
    top50.to_csv(top50_csv, index=False)

    sorafenib_row = agg.loc[agg["drug_name_norm"].eq("sorafenib"), ["rank_proxy_v2", "canonical_drug_id", "drug_name"]]
    summary = {
        "version": "v2",
        "stage": "formal_candidate_pool_expansion_start",
        "input_train_table": str(train_path),
        "input_drug_master": str(drug_master_path),
        "candidate_pool_size": int(len(agg)),
        "hcc_approved_in_pool": int(agg["hcc_approved"].sum()),
        "hcc_approved_in_top50_proxy": int(top50["hcc_approved"].sum()),
        "sorafenib_in_pool": bool(not sorafenib_row.empty),
        "sorafenib_proxy_rank": (None if sorafenib_row.empty else int(sorafenib_row.iloc[0]["rank_proxy_v2"])),
        "outputs": {
            "candidate_pool_csv": str(pool_csv),
            "top50_proxy_csv": str(top50_csv),
        },
        "note": "This v2 artifact is pre-Step4 proxy ranking; run Step4/5 after wiring this pool into protocol scripts for final model ranking.",
    }
    (res / "lihc_v2_candidate_pool_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
