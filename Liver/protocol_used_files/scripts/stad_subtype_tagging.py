#!/usr/bin/env python3
"""
Build optional stad_subtype_metadata.parquet from cBioPortal TCGA-STAD patient clinical table.

Reference (Colon analogue):
  20260420_new_pre_project_biso_Colon/scripts/colon_subtype_tagging.py

Input:
  --cbioportal-dir: directory containing data_clinical_patient.txt (Pan-Cancer Atlas style:
  first 4 lines are # metadata; line 5 is column headers starting with PATIENT_ID).

Output:
  --output: data/stad_subtype_metadata.parquet

Output columns (I/O shape):
  (N_patients, 9): patient_id, sample_id, primary_site, lauren_class, msi_status,
  ras_mutation, braf_mutation, ebv_status, cohort_tag
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
    p.add_argument("--cbioportal-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def read_cbio_patient_clinical(path: Path) -> pd.DataFrame:
    """Load PanCan-style data_clinical_patient.txt (4-line preamble + header row)."""
    return pd.read_csv(path, sep="\t", skiprows=4, header=0, low_memory=False)


def main() -> int:
    args = parse_args()
    clin_p = args.cbioportal_dir / "data_clinical_patient.txt"
    if not clin_p.exists():
        log(f"ERROR: missing {clin_p}")
        return 1

    raw = read_cbio_patient_clinical(clin_p)
    log(f"Clinical shape: {raw.shape}; columns (first 12): {list(raw.columns[:12])}")

    patient_col = "PATIENT_ID" if "PATIENT_ID" in raw.columns else raw.columns[0]
    patients = raw[patient_col].astype(str)

    subtype_col = "SUBTYPE" if "SUBTYPE" in raw.columns else None
    subtypes = raw[subtype_col].astype(str) if subtype_col else pd.Series(pd.NA, index=raw.index)

    msi_like = None
    for cand in ("MSI_STATUS", "MSI", "MONOALLELIC_INACTIVATION"):
        if cand in raw.columns:
            msi_like = raw[cand].astype(str)
            break
    if msi_like is None:
        msi_like = pd.Series(pd.NA, index=raw.index)

    out = pd.DataFrame(
        {
            "patient_id": patients,
            "sample_id": patients,
            "primary_site": "Stomach",
            "lauren_class": pd.NA,
            "msi_status": msi_like,
            "ras_mutation": pd.NA,
            "braf_mutation": pd.NA,
            "ebv_status": pd.NA,
            "cohort_tag": subtypes,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)
    log(f"Wrote {args.output} shape={out.shape}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
