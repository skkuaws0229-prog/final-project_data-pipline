#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result_tag = "20260427_hnsc_step4_v1"
    res_dir = root / "results" / result_tag
    ext_dir = root / "external_validation" / result_tag

    top30_path = res_dir / "top30_tier1234_fixed_hnsc.csv"
    ext_path = ext_dir / "top30_external_validation_independent.csv"

    if not top30_path.is_file():
        raise FileNotFoundError(f"Missing {top30_path}")

    top30 = pd.read_csv(top30_path)
    top30["rank"] = pd.to_numeric(top30["rank"], errors="coerce").astype("Int64")
    top30["drug_name"] = top30["drug_name"].astype(str)

    if ext_path.is_file():
        ext = pd.read_csv(ext_path)
        ext = ext.rename(columns={"DRUG_NAME": "drug_name"})
        keep_cols = [c for c in [
            "rank",
            "drug_name",
            "prism_status",
            "clinical_trial_has_evidence",
            "patient_context_has_evidence",
            "opentargets_has_evidence",
            "cosmic_has_evidence",
        ] if c in ext.columns]
        ext = ext[keep_cols].copy()
        if "rank" in ext.columns:
            ext["rank"] = pd.to_numeric(ext["rank"], errors="coerce").astype("Int64")
        merged = top30.merge(ext, on=["rank", "drug_name"], how="left")
    else:
        merged = top30.copy()

    for c in ("clinical_trial_has_evidence", "patient_context_has_evidence", "opentargets_has_evidence", "cosmic_has_evidence"):
        if c not in merged.columns:
            merged[c] = pd.NA

    bool_cols = ["clinical_trial_has_evidence", "patient_context_has_evidence", "opentargets_has_evidence", "cosmic_has_evidence"]
    merged["external_any_support"] = merged[bool_cols].fillna(False).astype(bool).any(axis=1)
    merged["external_data_status"] = "PARTIAL_OR_UNKNOWN"
    merged.loc[merged[bool_cols].notna().any(axis=1), "external_data_status"] = "HAS_SOURCE_ROWS"
    merged["step7_extended_decision"] = "HOLD_DATA_GAP"

    merged.loc[merged["tier"].eq("Tier4"), "step7_extended_decision"] = "REVIEW"
    merged.loc[merged["external_any_support"] & merged["tier"].eq("Tier1"), "step7_extended_decision"] = "PRIORITY_1"
    merged.loc[merged["external_any_support"] & merged["tier"].eq("Tier2"), "step7_extended_decision"] = "PRIORITY_2"
    merged.loc[merged["external_any_support"] & merged["tier"].eq("Tier3"), "step7_extended_decision"] = "EXPLORE"
    merged.loc[(~merged["external_any_support"]) & (~merged["tier"].eq("Tier4")), "step7_extended_decision"] = "REVIEW"

    merged = merged.sort_values("rank").reset_index(drop=True)

    out_full = res_dir / "step7_top30_hnsc_extended.csv"
    merged.to_csv(out_full, index=False)

    top15 = merged.head(15).copy()
    out15 = res_dir / "step7_top15_hnsc_extended.csv"
    top15.to_csv(out15, index=False)

    print(f"Wrote {out_full}")
    print(f"Wrote {out15}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
