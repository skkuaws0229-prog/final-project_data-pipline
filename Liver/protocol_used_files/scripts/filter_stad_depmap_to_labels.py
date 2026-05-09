#!/usr/bin/env python3
"""
Refilter STAD DepMap long table to labels sample IDs.

This script is STAD-specific and performs a post-Step2 alignment:
1) Resolve labels sample_id to DepMap model entries (StrippedCellLineName/CellLineName).
2) Filter depmap_crispr_long_stad.parquet to matched DepMap cell lines with CRISPR rows.
3) Rewrite filtered depmap_long cell_line_name to labels sample_id for exact FE joins.
4) Rewrite FE GDSC file cell_line_name to labels sample_id format.
5) Emit JSON report with match details and failures.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


def log(msg: str) -> None:
    """Timestamped log line."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def normalize_strict(name: str) -> str:
    """Stage 1 normalization: remove common delimiters."""
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
    """Stage 2 normalization: strict + broad punctuation removal."""
    s = normalize_strict(name)
    s = s.replace(".", "").replace(",", "").replace(";", "")
    s = s.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
    return re.sub(r"[^a-z0-9]", "", s)


@dataclass
class LabelToDepMapMatch:
    """Resolved mapping from labels sample_id to DepMap cell line."""

    label_sample_id: str
    depmap_cell_line_name: str
    depmap_stripped_name: str
    model_id: str
    match_type: str
    has_crispr: bool


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--labels-uri", required=True, type=Path)
    p.add_argument("--depmap-long-uri", required=True, type=Path)
    p.add_argument("--depmap-model-uri", required=True, type=Path)
    p.add_argument("--output-depmap-long", required=True, type=Path)
    p.add_argument("--output-gdsc-fe", required=True, type=Path)
    p.add_argument("--output-report", required=True, type=Path)
    return p.parse_args()


def _choose_one(rows: pd.DataFrame) -> pd.Series | None:
    """Choose deterministic single row from candidate matches."""
    if rows.empty:
        return None
    rows = rows.sort_values(
        by=["ModelID", "CellLineName", "StrippedCellLineName"], kind="stable"
    )
    return rows.iloc[0]


def _resolve_label_sample(
    sample_id: str,
    model_df: pd.DataFrame,
    depmap_cells_with_crispr: set[str],
) -> tuple[LabelToDepMapMatch | None, str | None]:
    """
    Resolve one labels sample_id into DepMap model row.

    Returns:
      - LabelToDepMapMatch if resolved
      - failure reason if not resolved
    """
    sid = str(sample_id)

    exact_stripped = model_df[model_df["StrippedCellLineName"] == sid]
    row = _choose_one(exact_stripped)
    if row is not None:
        depmap_name = str(row["CellLineName"])
        return (
            LabelToDepMapMatch(
                label_sample_id=sid,
                depmap_cell_line_name=depmap_name,
                depmap_stripped_name=str(row["StrippedCellLineName"]),
                model_id=str(row["ModelID"]),
                match_type="exact_stripped",
                has_crispr=depmap_name in depmap_cells_with_crispr,
            ),
            None,
        )

    exact_cell = model_df[model_df["CellLineName"] == sid]
    row = _choose_one(exact_cell)
    if row is not None:
        depmap_name = str(row["CellLineName"])
        return (
            LabelToDepMapMatch(
                label_sample_id=sid,
                depmap_cell_line_name=depmap_name,
                depmap_stripped_name=str(row["StrippedCellLineName"]),
                model_id=str(row["ModelID"]),
                match_type="exact_cellline",
                has_crispr=depmap_name in depmap_cells_with_crispr,
            ),
            None,
        )

    key_strict = normalize_strict(sid)
    strict_hits = model_df[
        (model_df["_strict_stripped"] == key_strict)
        | (model_df["_strict_cellline"] == key_strict)
    ]
    row = _choose_one(strict_hits)
    if row is not None:
        depmap_name = str(row["CellLineName"])
        return (
            LabelToDepMapMatch(
                label_sample_id=sid,
                depmap_cell_line_name=depmap_name,
                depmap_stripped_name=str(row["StrippedCellLineName"]),
                model_id=str(row["ModelID"]),
                match_type="strict_norm",
                has_crispr=depmap_name in depmap_cells_with_crispr,
            ),
            None,
        )

    key_fallback = normalize_fallback(sid)
    fallback_hits = model_df[
        (model_df["_fallback_stripped"] == key_fallback)
        | (model_df["_fallback_cellline"] == key_fallback)
    ]
    row = _choose_one(fallback_hits)
    if row is not None:
        depmap_name = str(row["CellLineName"])
        return (
            LabelToDepMapMatch(
                label_sample_id=sid,
                depmap_cell_line_name=depmap_name,
                depmap_stripped_name=str(row["StrippedCellLineName"]),
                model_id=str(row["ModelID"]),
                match_type="fallback_norm",
                has_crispr=depmap_name in depmap_cells_with_crispr,
            ),
            None,
        )

    return None, "no_model_match"


def _build_gdsc_label_map(gdsc_cells: list[str], label_samples: list[str]) -> dict[str, str]:
    """
    Build mapping gdsc cell_line_name -> labels sample_id by fallback normalization.

    Only unique normalization keys are auto-mapped.
    """
    label_by_norm: dict[str, str] = {}
    ambiguous_norms: set[str] = set()

    for sid in label_samples:
        key = normalize_fallback(sid)
        if key in label_by_norm and label_by_norm[key] != sid:
            ambiguous_norms.add(key)
        else:
            label_by_norm[key] = sid

    for key in ambiguous_norms:
        label_by_norm.pop(key, None)

    out: dict[str, str] = {}
    for cell in gdsc_cells:
        key = normalize_fallback(cell)
        if key in label_by_norm:
            out[cell] = label_by_norm[key]
    return out


def main() -> int:
    args = parse_args()

    log(f"I/O read labels: {args.labels_uri}")
    labels_df = pd.read_parquet(args.labels_uri)
    if "sample_id" not in labels_df.columns:
        raise ValueError(f"labels missing required column 'sample_id': {args.labels_uri}")
    label_samples = sorted(labels_df["sample_id"].astype(str).str.strip().unique().tolist())
    log(f"labels unique sample_id: {len(label_samples)}")

    log(f"I/O read depmap long: {args.depmap_long_uri}")
    depmap_long_df = pd.read_parquet(args.depmap_long_uri)
    required_long_cols = {"cell_line_name", "gene_name", "dependency"}
    missing_long = required_long_cols - set(depmap_long_df.columns)
    if missing_long:
        raise ValueError(f"depmap long missing columns {sorted(missing_long)}: {args.depmap_long_uri}")
    depmap_cells_with_crispr = set(depmap_long_df["cell_line_name"].astype(str).unique())
    log(f"depmap long unique cells: {len(depmap_cells_with_crispr)}")

    log(f"I/O read depmap model: {args.depmap_model_uri}")
    model_df = pd.read_parquet(args.depmap_model_uri)
    required_model_cols = {"ModelID", "CellLineName", "StrippedCellLineName"}
    missing_model = required_model_cols - set(model_df.columns)
    if missing_model:
        raise ValueError(f"model missing columns {sorted(missing_model)}: {args.depmap_model_uri}")

    model_df = model_df.copy()
    model_df["CellLineName"] = model_df["CellLineName"].astype(str).str.strip()
    model_df["StrippedCellLineName"] = model_df["StrippedCellLineName"].astype(str).str.strip()
    model_df["ModelID"] = model_df["ModelID"].astype(str).str.strip()
    model_df["_strict_stripped"] = model_df["StrippedCellLineName"].apply(normalize_strict)
    model_df["_strict_cellline"] = model_df["CellLineName"].apply(normalize_strict)
    model_df["_fallback_stripped"] = model_df["StrippedCellLineName"].apply(normalize_fallback)
    model_df["_fallback_cellline"] = model_df["CellLineName"].apply(normalize_fallback)

    matched: list[LabelToDepMapMatch] = []
    unmatched: list[dict[str, str]] = []

    for sid in label_samples:
        resolved, reason = _resolve_label_sample(sid, model_df, depmap_cells_with_crispr)
        if resolved is None:
            unmatched.append({"label_sample_id": sid, "reason": str(reason)})
        else:
            matched.append(resolved)

    matched_with_crispr = [m for m in matched if m.has_crispr]
    unmatched_crispr = [
        {"label_sample_id": m.label_sample_id, "reason": "no_crispr_rows_in_depmap_long"}
        for m in matched
        if not m.has_crispr
    ]

    keep_depmap_cells = {m.depmap_cell_line_name for m in matched_with_crispr}
    depmap_to_label = {m.depmap_cell_line_name: m.label_sample_id for m in matched_with_crispr}

    depmap_filtered = depmap_long_df[
        depmap_long_df["cell_line_name"].astype(str).isin(keep_depmap_cells)
    ].copy()
    depmap_filtered["cell_line_name"] = depmap_filtered["cell_line_name"].astype(str).map(depmap_to_label)

    args.output_depmap_long.parent.mkdir(parents=True, exist_ok=True)
    log(f"I/O write filtered depmap long: {args.output_depmap_long}")
    depmap_filtered.to_parquet(args.output_depmap_long, index=False)
    log(
        "filtered depmap long rows="
        f"{len(depmap_filtered):,}, unique_cells={depmap_filtered['cell_line_name'].nunique()}"
    )

    log(f"I/O read FE GDSC: {args.output_gdsc_fe}")
    gdsc_df = pd.read_parquet(args.output_gdsc_fe)
    if "cell_line_name" not in gdsc_df.columns:
        raise ValueError(f"FE GDSC missing 'cell_line_name': {args.output_gdsc_fe}")

    gdsc_df = gdsc_df.copy()
    gdsc_df["cell_line_name"] = gdsc_df["cell_line_name"].astype(str).str.strip()
    gdsc_unique_cells = sorted(gdsc_df["cell_line_name"].unique().tolist())
    gdsc_map = _build_gdsc_label_map(gdsc_unique_cells, label_samples)
    gdsc_df["cell_line_name"] = gdsc_df["cell_line_name"].map(lambda x: gdsc_map.get(x, x))

    log(f"I/O write synchronized FE GDSC: {args.output_gdsc_fe}")
    gdsc_df.to_parquet(args.output_gdsc_fe, index=False)

    gdsc_unmapped = sorted([c for c in gdsc_unique_cells if c not in gdsc_map])
    gdsc_remapped = sorted([{"from": k, "to": v} for k, v in gdsc_map.items()], key=lambda x: x["from"])

    report = {
        "generated_at": datetime.now().isoformat(),
        "inputs": {
            "labels_uri": str(args.labels_uri),
            "depmap_long_uri": str(args.depmap_long_uri),
            "depmap_model_uri": str(args.depmap_model_uri),
            "gdsc_fe_uri": str(args.output_gdsc_fe),
        },
        "labels_unique_cells": len(label_samples),
        "matched_cells": [
            {
                "label_sample_id": m.label_sample_id,
                "depmap_cell_line_name": m.depmap_cell_line_name,
                "depmap_stripped_name": m.depmap_stripped_name,
                "model_id": m.model_id,
                "match_type": m.match_type,
                "has_crispr": m.has_crispr,
            }
            for m in matched
        ],
        "unmatched_model": unmatched,
        "unmatched_crispr": unmatched_crispr,
        "summary": {
            "matched_total": len(matched),
            "matched_with_crispr": len(matched_with_crispr),
            "unmatched_model_count": len(unmatched),
            "unmatched_crispr_count": len(unmatched_crispr),
            "output_depmap_rows": int(len(depmap_filtered)),
            "output_depmap_cells": int(depmap_filtered["cell_line_name"].nunique())
            if not depmap_filtered.empty
            else 0,
            "gdsc_unique_cells_before_sync": len(gdsc_unique_cells),
            "gdsc_cells_remapped_count": len(gdsc_map),
            "gdsc_cells_unmapped_count": len(gdsc_unmapped),
        },
        "gdsc_cell_line_sync": {
            "remapped": gdsc_remapped,
            "unmapped": gdsc_unmapped,
        },
    }

    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    log(f"I/O write report: {args.output_report}")
    with open(args.output_report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

