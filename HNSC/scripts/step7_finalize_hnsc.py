#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


def bool_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return df[col].fillna(False).astype(bool)
    return pd.Series([False] * len(df), index=df.index)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result_tag = "20260427_hnsc_step4_v1"
    ext_csv = root / "external_validation" / result_tag / "top30_external_validation_independent.csv"
    out_csv = root / "results" / result_tag / "step7_top15_hnsc_provisional.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    if not ext_csv.is_file():
        # Fallback: keep existing provisional file if already prepared manually.
        if out_csv.is_file():
            print(f"[step7] Missing Step6 file, keeping existing provisional output: {out_csv}")
            return 0
        raise FileNotFoundError(f"Missing Step6 external file: {ext_csv}")

    df = pd.read_csv(ext_csv)
    if "rank" not in df.columns or "DRUG_NAME" not in df.columns:
        raise ValueError("Step6 external CSV missing required columns: rank, DRUG_NAME")

    top15 = df.sort_values("rank", ascending=True).head(15).copy()
    top15["step6_external_match"] = (
        bool_series(top15, "prism_any_match")
        | bool_series(top15, "clinical_trial_has_evidence")
        | bool_series(top15, "patient_context_has_evidence")
        | bool_series(top15, "opentargets_has_evidence")
        | bool_series(top15, "cosmic_has_evidence")
    )
    top15["step6_external_match"] = top15["step6_external_match"].map({True: "matched", False: "unmatched"})
    vt = top15.get("validation_evidence_tier", pd.Series(["VT3"] * len(top15), index=top15.index)).astype(str)
    top15["validation_evidence_tier"] = vt
    top15["step7_decision"] = "KEEP_TOP15"
    top15.loc[top15["validation_evidence_tier"].eq("VT4"), "step7_decision"] = "REVIEW"
    top15.loc[top15["step6_external_match"].eq("unmatched"), "step7_decision"] = "REVIEW"
    top15["notes"] = ""

    out = top15[["rank", "DRUG_NAME", "step6_external_match", "validation_evidence_tier", "step7_decision", "notes"]].copy()
    out = out.rename(columns={"DRUG_NAME": "drug_name"})
    out.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
