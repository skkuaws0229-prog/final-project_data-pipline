#!/usr/bin/env python3
"""
Export GDSC rows (TCGA_DESC == STAD) to a parquet that satisfies prepare_fe_inputs.py:
  required columns: cell_line_name, DRUG_ID, ln_IC50, drug_name

Input:
  curated_data/processed/gdsc/GDSC2-dataset.parquet (uppercase GDSC columns)

Output:
  data/GDSC2-dataset.parquet (for S3 sync + Nextflow label-uri)

Shape:
  Rows: filtered STAD measurements; Columns: cell_line_name, DRUG_ID, ln_IC50, drug_name
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gdsc-parquet", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    df = pd.read_parquet(args.gdsc_parquet)
    sub = df[df["TCGA_DESC"] == "STAD"].copy()
    out = pd.DataFrame(
        {
            "cell_line_name": sub["CELL_LINE_NAME"].astype(str),
            "DRUG_ID": sub["DRUG_ID"],
            "ln_IC50": sub["LN_IC50"],
            "drug_name": sub["DRUG_NAME"].astype(str),
        }
    )
    out = out.dropna(subset=["ln_IC50"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)
    log(f"Wrote {args.output} shape={out.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
