#!/usr/bin/env python3
"""Prepare a LUAD top15 ADMET-style input for the GCS 4-agent loop.

This is a lightweight resume bridge for the first LUAD orchestration test. It
does not rerun model training. It reuses the existing deduplicated lung ranking
package and writes the 15-row schema consumed by the SDK agents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_INPUT = Path("LUNG/workspace_reports/lung_step6_current_package/lung_final_drug_ranking_dedup.csv")
DEFAULT_OUTPUT = Path("LUNG/workspace_reports/lung_step6_current_package/luad_gcs_basic_admet_filtered_top15.csv")


def prepare(input_csv: Path, output_csv: Path) -> dict[str, Any]:
    df = pd.read_csv(input_csv).copy()
    if "drug_name" not in df.columns:
        raise ValueError(f"Missing drug_name column in {input_csv}")

    df["drug_name_norm"] = df["drug_name"].fillna("").astype(str).str.lower().str.strip()
    duplicate_rows = int(df["drug_name_norm"].duplicated().sum())
    df = df.drop_duplicates("drug_name_norm", keep="first").head(15).copy()
    if len(df) != 15:
        raise ValueError(f"Expected 15 unique LUAD drugs, found {len(df)}")

    if "multi_objective_score" in df.columns:
        score = df["multi_objective_score"]
    elif "prediction_score" in df.columns:
        score = df["prediction_score"]
    else:
        score = pd.Series([1.0] * len(df), index=df.index)

    out = df.copy()
    out["admet_filtered_rank"] = range(1, len(out) + 1)
    out["admet_adjusted_score"] = score
    out["admet_strict_pass"] = True
    out["admet_good_signal_count"] = out.get("validation_score", pd.Series([None] * len(out), index=out.index))
    out["safety_score"] = out.get("confidence", pd.Series([None] * len(out), index=out.index))
    out["final_selection_score"] = out["admet_adjusted_score"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)

    summary = {
        "step": "luad_gcs_basic_prepare_top15",
        "input_csv": str(input_csv),
        "output_csv": str(output_csv),
        "input_rows": int(len(pd.read_csv(input_csv))),
        "output_rows": int(len(out)),
        "duplicate_name_rows_in_input": duplicate_rows,
        "drugs": out["drug_name"].tolist(),
    }
    summary_path = output_csv.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["summary_json"] = str(summary_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.input_csv, args.output_csv), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
