#!/usr/bin/env python3
"""
Filter stomach adenocarcinoma (GDSC TCGA_DESC == STAD) cell lines and generate labels.

Adapted from:
  20260420_new_pre_project_biso_Colon/scripts/filter_colon_cell_lines.py

Process:
  1. Filter GDSC2-dataset for TCGA_DESC == 'STAD'
  2. Match with DepMap cell lines (2-stage name normalization)
  3. Write labels.parquet (sample_id, canonical_drug_id, ic50, binary_label)
  4. Matched cells CSV + JSON report

Output labels schema:
  - sample_id          : str (DepMap StrippedCellLineName)
  - canonical_drug_id  : str (GDSC DRUG_ID)
  - ic50               : float (LN_IC50)
  - binary_label       : int (1 = sensitive vs quantile threshold)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def normalize_strict(name: str) -> str:
    return (
        str(name)
        .lower()
        .replace("-", "")
        .replace("/", "")
        .replace(" ", "")
        .replace("_", "")
        .replace(":", "")
    )


def normalize_fallback(name: str) -> str:
    s = normalize_strict(name)
    s = s.replace(".", "").replace(",", "").replace(";", "")
    s = s.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    return re.sub(r"[^a-z0-9]", "", s)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gdsc-ic50", required=True, type=Path, help="GDSC2-dataset.parquet")
    p.add_argument("--gdsc-annotation", required=True, type=Path, help="Compounds-annotation.parquet")
    p.add_argument("--depmap-model", required=True, type=Path, help="Model.parquet")
    p.add_argument("--depmap-long", required=True, type=Path, help="depmap_crispr_long_stad.parquet")
    p.add_argument("--output-labels", required=True, type=Path, help="labels.parquet")
    p.add_argument("--output-cells", required=True, type=Path, help="matched cell lines CSV")
    p.add_argument("--output-report", required=True, type=Path, help="matching report JSON")
    p.add_argument("--quantile", type=float, default=0.3, help="IC50 quantile for binary_label")
    return p.parse_args()


def build_depmap_lookup(
    model_df: pd.DataFrame, long_df: pd.DataFrame
) -> dict[str, dict[str, dict]]:
    cells_with_crispr = set(long_df["cell_line_name"].unique())
    strict_lookup: dict[str, dict] = {}
    fallback_lookup: dict[str, dict] = {}
    for _, row in model_df.iterrows():
        model_id = row.get("ModelID")
        stripped = row.get("StrippedCellLineName")
        cell_name = row.get("CellLineName")
        if pd.isna(stripped):
            continue
        has_crispr = stripped in cells_with_crispr
        info = {
            "model_id": model_id,
            "stripped_name": stripped,
            "cell_name": cell_name,
            "has_crispr": has_crispr,
        }
        ks = normalize_strict(str(stripped))
        if ks and ks not in strict_lookup:
            strict_lookup[ks] = info
        kf = normalize_fallback(str(stripped))
        if kf and kf not in fallback_lookup:
            fallback_lookup[kf] = info
    return {"strict": strict_lookup, "fallback": fallback_lookup}


def match_cell_lines(
    gdsc_cells: list[str], depmap_lookup: dict[str, dict[str, dict]]
) -> tuple[dict, list[str], list[dict]]:
    matched: dict[str, dict] = {}
    match_log: list[dict] = []
    unmatched: list[str] = []
    for gdsc_name in gdsc_cells:
        key = normalize_strict(gdsc_name)
        if key in depmap_lookup["strict"]:
            info = depmap_lookup["strict"][key]
            matched[gdsc_name] = info
            match_log.append(
                {
                    "gdsc_name": gdsc_name,
                    "normalized": key,
                    "stage": "strict",
                    "depmap_stripped": info["stripped_name"],
                    "depmap_model_id": info["model_id"],
                    "has_crispr": info["has_crispr"],
                }
            )
        else:
            unmatched.append(gdsc_name)
    log(f"Stage 1 (strict): matched {len(matched)}/{len(gdsc_cells)}")
    still_unmatched: list[str] = []
    for gdsc_name in unmatched:
        key = normalize_fallback(gdsc_name)
        if key in depmap_lookup["fallback"]:
            info = depmap_lookup["fallback"][key]
            matched[gdsc_name] = info
            match_log.append(
                {
                    "gdsc_name": gdsc_name,
                    "normalized": key,
                    "stage": "fallback",
                    "depmap_stripped": info["stripped_name"],
                    "depmap_model_id": info["model_id"],
                    "has_crispr": info["has_crispr"],
                }
            )
        else:
            still_unmatched.append(gdsc_name)
    log(f"Stage 2 (fallback): +{len(unmatched) - len(still_unmatched)}")
    log(f"Total matched: {len(matched)}/{len(gdsc_cells)}")
    return matched, still_unmatched, match_log


def main() -> int:
    args = parse_args()
    log("=" * 70)
    log("Step 2-4 (STAD): Filter STAD GDSC lines + labels")
    log("=" * 70)

    gdsc = pd.read_parquet(args.gdsc_ic50)
    model = pd.read_parquet(args.depmap_model)
    long_df = pd.read_parquet(args.depmap_long)
    log(f"GDSC rows: {len(gdsc):,}; DepMap long cells: {long_df['cell_line_name'].nunique():,}")

    stad = gdsc[gdsc["TCGA_DESC"] == "STAD"].copy()
    gdsc_stad_cells = sorted(stad["CELL_LINE_NAME"].unique())
    log(f"STAD rows: {len(stad):,}; STAD GDSC cell lines: {len(gdsc_stad_cells)}")

    depmap_lookup = build_depmap_lookup(model, long_df)
    matched, unmatched, match_log = match_cell_lines(gdsc_stad_cells, depmap_lookup)

    matched_names = set(matched.keys())
    stad_matched = stad[stad["CELL_LINE_NAME"].isin(matched_names)].copy()
    stad_matched["sample_id"] = stad_matched["CELL_LINE_NAME"].map(
        lambda x: matched[x]["stripped_name"] if x in matched else None
    )
    labels = stad_matched[["sample_id", "DRUG_ID", "LN_IC50"]].rename(
        columns={"DRUG_ID": "canonical_drug_id", "LN_IC50": "ic50"}
    )
    labels["canonical_drug_id"] = labels["canonical_drug_id"].astype(str)
    before = len(labels)
    labels = labels.dropna(subset=["ic50"])
    log(f"Dropped NaN ic50: {before - len(labels)}")
    thr = float(labels["ic50"].quantile(args.quantile))
    labels["binary_label"] = (labels["ic50"] < thr).astype(int)
    log(f"Binary threshold q={args.quantile}: {thr:.4f}")
    labels = labels[["sample_id", "canonical_drug_id", "ic50", "binary_label"]]

    args.output_labels.parent.mkdir(parents=True, exist_ok=True)
    args.output_cells.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    labels.to_parquet(args.output_labels, index=False)
    match_df = pd.DataFrame(match_log)
    n_drugs = stad_matched.groupby("CELL_LINE_NAME")["DRUG_ID"].nunique().to_dict()
    match_df["n_drugs_measured"] = match_df["gdsc_name"].map(n_drugs).fillna(0).astype(int)
    match_df.to_csv(args.output_cells, index=False)

    report = {
        "timestamp": datetime.now().isoformat(),
        "tcga_desc_filter": "STAD",
        "matching": {
            "total_matched": len(matched),
            "unmatched": len(unmatched),
            "match_rate": len(matched) / len(gdsc_stad_cells) if gdsc_stad_cells else 0.0,
        },
        "labels": {
            "rows": int(len(labels)),
            "cells": int(labels["sample_id"].nunique()),
            "drugs": int(labels["canonical_drug_id"].nunique()),
        },
        "unmatched_cells": unmatched,
    }
    with open(args.output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"Wrote {args.output_labels} shape={labels.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
