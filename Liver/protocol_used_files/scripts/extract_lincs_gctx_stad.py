#!/usr/bin/env python3
"""
Extract LINCS L1000 signatures for STAD cell lines from Level 5 gctx.

Adapted from:
  20260420_new_pre_project_biso_Colon/scripts/extract_lincs_gctx.py

Cell IDs are read from JSON (see configs/stad_lincs_cell_ids.json).

Input:
  - gctx.gz (e.g. GSE92742 Level5 COMPZ.MODZ)
  - sig_info.txt.gz

Output:
  - lincs_stad.parquet — same wide schema as Lung/Colon (sig_id + genes + metadata cols)
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gctx-uri", required=True, type=Path)
    p.add_argument("--sig-info-uri", required=True, type=Path)
    p.add_argument("--cell-ids-json", required=True, type=Path, help="JSON with key cell_ids: list[str]")
    p.add_argument("--output-uri", required=True, type=Path)
    p.add_argument("--report-uri", required=True, type=Path)
    p.add_argument("--chunk-size", type=int, default=2000)
    p.add_argument("--tmp-dir", type=Path, default=None)
    return p.parse_args()


def load_cell_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data.get("cell_ids")
    if not isinstance(cells, list) or not cells:
        raise ValueError(f"cell_ids must be a non-empty list in {path}")
    return [str(c) for c in cells]


def decompress_gctx(gctx_gz_path: Path, output_dir: Path) -> Path:
    output_path = Path(output_dir) / gctx_gz_path.name.replace(".gz", "")
    log(f"Decompressing {gctx_gz_path.name} -> {output_path.name}")
    with gzip.open(gctx_gz_path, "rb") as f_in:
        with open(output_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024 * 1024 * 64)
    log(f"  Decompressed size GB: {output_path.stat().st_size / 1024**3:.2f}")
    return output_path


def filter_sig_info(
    sig_info_path: Path, cells: list[str], pert_type: str = "trt_cp"
) -> tuple[pd.DataFrame, str]:
    log(f"Loading sig_info: {sig_info_path.name}")
    sig_info = pd.read_csv(sig_info_path, sep="\t", compression="gzip", low_memory=False)
    cell_col = "cell_id" if "cell_id" in sig_info.columns else "cell_iname"
    mask = (sig_info["pert_type"] == pert_type) & (sig_info[cell_col].isin(cells))
    filtered = sig_info[mask].copy()
    log(f"  Filtered trt_cp + STAD cells: {len(filtered):,}; cols={filtered.columns.tolist()[:8]}...")
    log(f"  Cells present: {sorted(filtered[cell_col].unique().tolist())}")
    return filtered, cell_col


def extract_gctx_chunked(gctx_path: Path, sig_ids: list[str], chunk_size: int) -> pd.DataFrame:
    from cmapPy.pandasGEXpress.parse import parse

    total = len(sig_ids)
    log(f"Extracting {total:,} signatures, chunk_size={chunk_size}")
    chunks: list[pd.DataFrame] = []
    n_chunks = (total + chunk_size - 1) // chunk_size
    for i in range(0, total, chunk_size):
        chunk_ids = sig_ids[i : i + chunk_size]
        chunk_num = (i // chunk_size) + 1
        log(f"  Chunk {chunk_num}/{n_chunks} ({len(chunk_ids)} sigs)")
        gctoo = parse(str(gctx_path), cid=chunk_ids)
        chunk_df = gctoo.data_df.T
        chunks.append(chunk_df)
        del gctoo
    gene_matrix = pd.concat(chunks, axis=0)
    log(f"  Gene matrix shape: {gene_matrix.shape}")
    return gene_matrix


def build_final_df(
    gene_matrix: pd.DataFrame, sig_info_filtered: pd.DataFrame, cell_col: str
) -> pd.DataFrame:
    gene_matrix.index.name = "sig_id"
    gene_matrix = gene_matrix.reset_index()
    gene_cols = [c for c in gene_matrix.columns if c != "sig_id"]
    gene_matrix[gene_cols] = gene_matrix[gene_cols].astype("float32")
    required_meta = [
        "sig_id",
        "pert_id",
        "pert_iname",
        "pert_dose",
        "pert_dose_unit",
        "pert_time",
        "pert_time_unit",
    ]
    for c in required_meta:
        if c not in sig_info_filtered.columns:
            sig_info_filtered[c] = None
    meta = sig_info_filtered[required_meta + [cell_col]].copy()
    if cell_col != "cell_id":
        meta = meta.rename(columns={cell_col: "cell_id"})
    meta["pert_time"] = pd.to_numeric(meta["pert_time"], errors="coerce").astype("Int64")
    result = gene_matrix.merge(
        meta[
            [
                "sig_id",
                "pert_id",
                "pert_iname",
                "pert_dose",
                "pert_dose_unit",
                "pert_time",
                "pert_time_unit",
                "cell_id",
            ]
        ],
        on="sig_id",
        how="left",
    )
    final_cols = ["sig_id"] + gene_cols + [
        "pert_id",
        "pert_iname",
        "pert_dose",
        "pert_dose_unit",
        "pert_time",
        "pert_time_unit",
        "cell_id",
    ]
    return result[final_cols]


def main() -> int:
    args = parse_args()
    cells = load_cell_ids(args.cell_ids_json)
    log("=" * 70)
    log(f"LINCS extract STAD — {len(cells)} cell line(s) configured")
    log("=" * 70)
    for path, label in [(args.gctx_uri, "gctx"), (args.sig_info_uri, "sig_info")]:
        if not path.exists():
            log(f"ERROR missing {label}: {path}")
            return 1
    filtered, cell_col = filter_sig_info(args.sig_info_uri, cells)
    if len(filtered) == 0:
        log("ERROR: no signatures after filter — check cell_ids vs sig_info")
        return 1
    sig_ids = filtered["sig_id"].tolist()
    tmp_path = Path(args.tmp_dir or tempfile.mkdtemp(prefix="lincs_stad_"))
    tmp_path.mkdir(parents=True, exist_ok=True)
    try:
        gctx_path = decompress_gctx(args.gctx_uri, tmp_path)
        gene_matrix = extract_gctx_chunked(gctx_path, sig_ids, args.chunk_size)
        final_df = build_final_df(gene_matrix, filtered, cell_col)
        args.output_uri.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_parquet(args.output_uri, index=False, engine="pyarrow")
        rep = {
            "timestamp": datetime.now().isoformat(),
            "cells": cells,
            "output_shape": list(final_df.shape),
            "output_path": str(args.output_uri),
        }
        args.report_uri.parent.mkdir(parents=True, exist_ok=True)
        args.report_uri.write_text(json.dumps(rep, indent=2), encoding="utf-8")
        log(f"Saved {args.output_uri} ({final_df.shape})")
    finally:
        if args.tmp_dir is None and tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
