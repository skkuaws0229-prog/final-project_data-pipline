#!/usr/bin/env python3
"""
LIHC Step7-2: build final Top15 and tier1/2/3/4 using HCC approval criteria.
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


def _norm(text: object) -> str:
    return str(text or "").strip().lower()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    results = root / "results"
    ext_csv = root / "external_validation" / "20260428_liver_step4_cv5_gc_sc" / "top30_external_validation_lihc_cptac_excluded.csv"
    admet_csv = results / "stad_drugs_with_admet.csv"
    if not admet_csv.is_file():
        raise FileNotFoundError(f"Missing ADMET input: {admet_csv}")
    if not ext_csv.is_file():
        raise FileNotFoundError(f"Missing external validation input: {ext_csv}")

    admet = pd.read_csv(admet_csv)
    ext = pd.read_csv(ext_csv)
    admet["canonical_drug_id"] = admet["canonical_drug_id"].astype(str)
    ext["canonical_drug_id"] = ext["canonical_drug_id"].astype(str)
    merge_cols = [
        "canonical_drug_id",
        "clinical_trial_mention_count",
        "prism_has_evidence",
        "clinical_trials_has_evidence",
        "geo_has_evidence",
        "opentargets_has_evidence",
        "cosmic_has_evidence",
    ]
    df = admet.merge(ext[merge_cols], on="canonical_drug_id", how="left")
    for col in [
        "prism_has_evidence",
        "clinical_trials_has_evidence",
        "geo_has_evidence",
        "opentargets_has_evidence",
        "cosmic_has_evidence",
    ]:
        df[col] = df[col].fillna(False).astype(bool)
    df["clinical_trial_mention_count"] = pd.to_numeric(df["clinical_trial_mention_count"], errors="coerce").fillna(0).astype(int)
    df["external_support_count"] = df[
        [
            "prism_has_evidence",
            "clinical_trials_has_evidence",
            "geo_has_evidence",
            "opentargets_has_evidence",
            "cosmic_has_evidence",
        ]
    ].sum(axis=1)

    # Step7 gate: PASS/WARNING only
    df = df[df["verdict"].isin(["PASS", "WARNING"])].copy()
    df = df.sort_values(["safety_score", "pred_ic50_mean"], ascending=[False, True]).head(15).reset_index(drop=True)

    def classify(row: pd.Series) -> tuple[str, bool]:
        nm = _norm(row.get("drug_name"))
        approved = nm in HCC_APPROVED
        if approved:
            return "FDA_APPROVED_HCC", True
        if int(row.get("clinical_trial_mention_count", 0)) > 0:
            return "CLINICAL_TRIAL_EVIDENCE", False
        return "REPURPOSING_CANDIDATE", False

    categories = df.apply(classify, axis=1)
    df["usage_category"] = categories.map(lambda x: x[0])
    df["hcc_approved"] = categories.map(lambda x: bool(x[1]))

    def tier(row: pd.Series) -> tuple[str, str]:
        verdict = str(row.get("verdict", "")).upper()
        support = int(row.get("external_support_count", 0))
        if verdict == "PASS" and bool(row.get("hcc_approved", False)):
            return ("tier1", "HCC-approved and ADMET PASS")
        if verdict == "PASS":
            return ("tier2", "ADMET PASS but not HCC-approved")
        if verdict == "WARNING" and support >= 2:
            return ("tier3", "ADMET WARNING with multi-source support")
        return ("tier4", "ADMET WARNING with limited support")

    assigned = df.apply(tier, axis=1)
    df["tier"] = assigned.map(lambda x: x[0])
    df["tier_note"] = assigned.map(lambda x: x[1])
    df["tier_rank"] = df["tier"].map({"tier1": 1, "tier2": 2, "tier3": 3, "tier4": 4})
    df = df.sort_values(["tier_rank", "safety_score", "pred_ic50_mean"], ascending=[True, False, True]).reset_index(drop=True)
    df["tier_order_rank"] = range(1, len(df) + 1)

    keep = [
        "tier_order_rank",
        "drug_name",
        "canonical_drug_id",
        "verdict",
        "safety_score",
        "pred_ic50_mean",
        "usage_category",
        "hcc_approved",
        "clinical_trial_mention_count",
        "external_support_count",
        "tier",
        "tier_note",
    ]
    out_tier = results / "lihc_step7_final_top15_tier4.csv"
    df[keep].to_csv(out_tier, index=False)

    out_top15 = results / "lihc_final_top15.csv"
    df.to_csv(out_top15, index=False)
    # Compatibility overwrite for legacy viewers.
    (results / "stad_final_top15.csv").write_text(out_top15.read_text(encoding="utf-8"), encoding="utf-8")

    summary = {
        "disease_axis": "LIHC / HCC",
        "rule_basis": "HCC approval list + ADMET + external support",
        "hcc_approved_in_top15": int(df["hcc_approved"].sum()),
        "tier_counts": df["tier"].value_counts().to_dict(),
        "output_top15_csv": str(out_top15),
        "output_tier_csv": str(out_tier),
    }
    (results / "lihc_final_top15_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (results / "lihc_step7_final_top15_tier4_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
