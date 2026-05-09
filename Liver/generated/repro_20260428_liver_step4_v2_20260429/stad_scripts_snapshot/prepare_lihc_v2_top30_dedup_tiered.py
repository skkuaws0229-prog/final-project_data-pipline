#!/usr/bin/env python3
"""
De-duplicate LIHC v2 ensemble ranking by parent drug name, keep Top30 unique parents,
assign clinical Tier 1–4 (KO labels), emit Step6-ready CSV.

Tier meanings (operator-adjustable via configs/lihc_v2_clinical_tier_overrides.tsv):
  1 = 간세포암(HCC) 적응 승인 약물
  2 = 다른 암종 승인·간암 적응증 확장/재포지셔닝 임상 후보(연구·승인 진행 중 포함)
  3 = 간암 표준 적응 외, 타 적응 위주 항암제(HCC에서 미확립)
  4 = 연구용 화합물·선별 화합물·추가 확인 필요

Outputs (result-tag folder, all filenames carry v2):
  - lihc_v2_top30_dedup_tiered.csv
  - lihc_top30_directive_ensemble_with_names.csv  (columns for Liver/scripts/step6_ext_lihc_independent_cptac_excluded.py)

Optional: prepend Tier-1 (HCC-approved) anchors from configs/lihc_v2_hcc_approved_anchors.tsv so that
external validation always includes a positive regulatory control **when those drug IDs exist in drug_features**.

Step6:
  python3 Liver\\ cancer/scripts/step6_ext_lihc_independent_cptac_excluded.py \\
    --project-root \"<Liver cancer folder>\" --result-tag <RESULT_TAG>
  (expects results/<tag>/lihc_top30_directive_ensemble_with_names.csv under project-root)
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def liver_drug_features_path(project_root: Path) -> Path:
    return (
        project_root.parent.parent
        / "20260427_Liver"
        / "base_data"
        / "20260421_liver"
        / "data"
        / "processed"
        / "model_inputs"
        / "drug_features.parquet"
    )


def parent_drug_key(display_name: str) -> str:
    """Normalize display name to dedupe concentrations/salt variants."""
    s = str(display_name or "").strip()
    s = re.sub(r"\s*\([^)]*\bu[mM]\b[^)]*\)", "", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return re.sub(r"[^a-z0-9]+", "", s)


TIER_LABEL_KO: dict[int, str] = {
    1: "Tier1: 간세포암(HCC) 적응 승인 약물",
    2: "Tier2: 타암종 승인·간암 적응증 확장/재포지셔닝 연구 후보",
    3: "Tier3: 간암 표준 적응 외(타 적응 위주) 항암제",
    4: "Tier4: 연구용·선별 화합물·추가 확인 필요",
}


# Initial rule-based map (parent_key_norm -> tier). Overrides TSV takes precedence.
DEFAULT_TIER_BY_PARENT: dict[str, int] = {
    # Tier 2: marketed agents with documented HCC/combination clinical exploration (operator-curated baseline)
    "docetaxel": 2,
    "paclitaxel": 2,
    "irinotecan": 2,
    "temsirolimus": 2,
    "rapamycin": 2,
    "epirubicin": 2,
    "tanespimycin": 2,
    "bosutinib": 2,
    # Tier 3: conventional oncology drugs without HCC as primary indication in this list context
    "bleomycin": 3,
    "elesclomol": 3,
    "bortezomib": 3,
    "topotecan": 3,
    "dactinomycin": 3,
    "vinblastine": 3,
    "camptothecin": 3,
    "teniposide": 3,
    "mitoxantrone": 3,
    "vinorelbine": 3,
    "pevonedistat": 3,
    # Tier 4: tool / kinase-screen / confirm
    "lestaurtinib": 4,
    "cct018159": 4,
    "mg132": 4,
    "bx795": 4,
    "sl0101": 4,
    "staurosporine": 4,
    "tozasertib": 4,
    "bi2536": 4,
    "azd5582": 4,
    "tw37": 4,
    "alisertib": 4,
}


def load_tier_overrides(path: Path) -> dict[str, tuple[int, str]]:
    """Parse TSV with columns parent_key_norm, tier, rationale_ko."""
    if not path.is_file():
        return {}
    df = pd.read_csv(path, sep="\t", comment="#")
    df.columns = [c.strip() for c in df.columns]
    if "parent_key_norm" not in df.columns or "tier" not in df.columns:
        return {}
    out: dict[str, tuple[int, str]] = {}
    for r in df.itertuples(index=False):
        key = str(getattr(r, "parent_key_norm", "") or "").strip().lower()
        if not key:
            continue
        tier_raw = getattr(r, "tier", np.nan)
        if pd.isna(tier_raw) or str(tier_raw).strip() == "":
            continue
        tier = int(float(tier_raw))
        if tier not in (1, 2, 3, 4):
            continue
        note = ""
        if hasattr(r, "rationale_ko"):
            note = str(getattr(r, "rationale_ko") or "").strip()
        out[key] = (tier, note)
    return out


def resolve_tier(parent_key_norm: str, overrides: dict[str, tuple[int, str]]) -> tuple[int, str]:
    if parent_key_norm in overrides:
        t, note = overrides[parent_key_norm]
        return t, note
    t = DEFAULT_TIER_BY_PARENT.get(parent_key_norm, 3)
    return t, ""


def pick_target_column(row: pd.Series) -> str:
    for c in ("drug__target_list", "putative_target", "target", "target_pathway"):
        if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
            return str(row[c]).strip()
    return ""


def load_hcc_anchor_ids(path: Path) -> list[tuple[str, str]]:
    """Return [(canonical_drug_id, note_ko), ...] from TSV."""
    if not path.is_file():
        return []
    df = pd.read_csv(path, sep="\t", comment="#")
    df.columns = [str(c).strip() for c in df.columns]
    if "canonical_drug_id" not in df.columns:
        return []
    out: list[tuple[str, str]] = []
    for r in df.itertuples(index=False):
        raw_id = getattr(r, "canonical_drug_id", None)
        if pd.isna(raw_id) or str(raw_id).strip() == "":
            continue
        cid = str(int(float(raw_id))) if str(raw_id).replace(".", "").isdigit() else str(raw_id).strip()
        note = ""
        if "note_ko" in df.columns:
            note = str(getattr(r, "note_ko", "") or "").strip()
        out.append((cid, note))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result-tag", default="20260428_liver_step4_v2")
    ap.add_argument("--run-id", default="step4_lihc_v2_manual")
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument(
        "--all-drugs-csv",
        type=Path,
        default=None,
        help="Default: results/<tag>/lihc_v2_directive_weighted_ensemble_all_drugs.csv",
    )
    ap.add_argument(
        "--inject-hcc-approved-tsv",
        type=Path,
        default=None,
        help="Optional TSV (canonical_drug_id, note_ko) — Tier1 anchors prepended; default configs/lihc_v2_hcc_approved_anchors.tsv",
    )
    ap.add_argument(
        "--no-inject-hcc-approved",
        action="store_true",
        help="Disable anchor injection even if default TSV exists.",
    )
    args = ap.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    tag = args.result_tag
    all_csv = args.all_drugs_csv or (project_root / "results" / tag / "lihc_v2_directive_weighted_ensemble_all_drugs.csv")
    if not all_csv.is_file():
        raise FileNotFoundError(f"Missing {all_csv} — run ensemble_lihc_v2_directive_weighted.py first.")

    overrides_path = project_root / "configs" / "lihc_v2_clinical_tier_overrides.tsv"
    overrides = load_tier_overrides(overrides_path)

    anchor_tsv = args.inject_hcc_approved_tsv  # --inject-hcc-approved-tsv
    if anchor_tsv is None and not args.no_inject_hcc_approved:
        anchor_tsv = project_root / "configs" / "lihc_v2_hcc_approved_anchors.tsv"
    anchor_specs = load_hcc_anchor_ids(anchor_tsv) if anchor_tsv and not args.no_inject_hcc_approved else []

    df = pd.read_csv(all_csv)
    df = df.sort_values("rank_lihc_v2_directive", ascending=True)
    df["parent_key_norm"] = df["drug_name_display"].map(parent_drug_key)
    pred_by_cid = df.set_index(df["canonical_drug_id"].astype(str))["pred_ensemble_mean"].to_dict()

    feat_path = liver_drug_features_path(project_root)
    if not feat_path.exists():
        raise FileNotFoundError(f"Missing drug features: {feat_path}")
    feat = pd.read_parquet(feat_path)
    feat["canonical_drug_id"] = feat["canonical_drug_id"].astype(str)
    feat_ids = set(feat["canonical_drug_id"].tolist())

    anchor_rows: list[pd.Series] = []
    anchor_seen_parents: set[str] = set()
    anchor_seen_cids: set[str] = set()
    for cid, note_anchor in anchor_specs:
        if cid not in feat_ids:
            print(f"[prepare_lihc_v2_top30] SKIP anchor id={cid} (not in drug_features.parquet)", flush=True)
            continue
        row_feat = feat.loc[feat["canonical_drug_id"] == cid].iloc[0]
        dn = str(row_feat.get("drug_name") or row_feat.get("drug_name_norm") or cid)
        pk = parent_drug_key(dn)
        if pk in anchor_seen_parents or cid in anchor_seen_cids:
            continue
        anchor_seen_parents.add(pk)
        anchor_seen_cids.add(cid)
        pred = pred_by_cid.get(cid, np.nan)
        ser = pd.Series(
            {
                "canonical_drug_id": cid,
                "pred_ensemble_mean": pred,
                "ensemble_member_std_mean": np.nan,
                "n_cell_drug_rows": np.nan,
                "drug_name_display": dn,
                "parent_key_norm": pk,
                "rank_lihc_v2_directive": np.nan,
                "confidence_grade": "",
                "top_model_vote_count": np.nan,
                "is_hcc_approved_anchor": True,
                "anchor_note_ko": note_anchor,
            }
        )
        anchor_rows.append(ser)

    need_ensemble = max(0, int(args.top_k) - len(anchor_rows))

    seen: set[str] = set(anchor_seen_parents)
    seen_cid: set[str] = set(anchor_seen_cids)
    picked: list[pd.Series] = []
    for _, row in df.iterrows():
        cid = str(row["canonical_drug_id"])
        k = str(row["parent_key_norm"])
        if cid in seen_cid or k in seen:
            continue
        seen.add(k)
        seen_cid.add(cid)
        row = row.copy()
        row["is_hcc_approved_anchor"] = False
        row["anchor_note_ko"] = ""
        picked.append(row)
        if len(picked) >= need_ensemble:
            break

    if len(picked) < need_ensemble:
        raise RuntimeError(
            f"Only {len(picked)} ensemble unique parents available (need {need_ensemble} after {len(anchor_rows)} anchors)."
        )

    slim_parts = [pd.DataFrame(anchor_rows)] if anchor_rows else []
    if picked:
        slim_parts.append(pd.DataFrame(picked))
    slim = pd.concat(slim_parts, ignore_index=True)
    slim["rank"] = np.arange(1, len(slim) + 1)

    tier_rows: list[dict[str, Any]] = []
    for _, row in slim.iterrows():
        if bool(row.get("is_hcc_approved_anchor")):
            note_a = str(row.get("anchor_note_ko") or "").strip()
            tier_rows.append(
                {
                    "clinical_tier": 1,
                    "clinical_tier_label_ko": TIER_LABEL_KO[1],
                    "tier_rationale_ko": note_a or "HCC 적응 승인 약물 앵커(외부검증 통제)",
                }
            )
            continue
        pk = str(row["parent_key_norm"])
        tier, note_ov = resolve_tier(pk, overrides)
        rationale = note_ov or ""
        tier_rows.append(
            {
                "clinical_tier": tier,
                "clinical_tier_label_ko": TIER_LABEL_KO[tier],
                "tier_rationale_ko": rationale,
            }
        )
    tier_df = pd.DataFrame(tier_rows)
    out = pd.concat([slim, tier_df], axis=1)

    # feat already loaded for anchors
    subcols = [c for c in feat.columns if c in {"canonical_drug_id", "drug_name", "drug_name_norm", "drug__target_list", "putative_target", "target", "target_pathway"}]
    feat_sub = feat[subcols].drop_duplicates("canonical_drug_id")
    out["canonical_drug_id"] = out["canonical_drug_id"].astype(str)
    out = out.merge(feat_sub, on="canonical_drug_id", how="left", suffixes=("", "_feat"))

    def row_target(r: pd.Series) -> str:
        return pick_target_column(r)

    out["TARGET"] = out.apply(row_target, axis=1)
    out["DRUG_NAME"] = out["drug_name"].fillna(out["drug_name_display"]).fillna(out.get("drug_name_norm", ""))
    out["pred_ic50_mean"] = out["pred_ensemble_mean"]

    out_dir = project_root / "results" / tag
    out_dir.mkdir(parents=True, exist_ok=True)

    tiered_path = out_dir / "lihc_v2_top30_dedup_tiered.csv"
    out.to_csv(tiered_path, index=False)

    step6_cols = [
        "rank",
        "canonical_drug_id",
        "DRUG_NAME",
        "TARGET",
        "pred_ic50_mean",
        "clinical_tier",
        "clinical_tier_label_ko",
        "tier_rationale_ko",
        "parent_key_norm",
        "pred_ensemble_mean",
        "ensemble_member_std_mean",
        "confidence_grade",
        "n_cell_drug_rows",
        "is_hcc_approved_anchor",
        "anchor_note_ko",
    ]
    step6_cols = [c for c in step6_cols if c in out.columns]
    step6_path = out_dir / "lihc_top30_directive_ensemble_with_names.csv"
    out[step6_cols].to_csv(step6_path, index=False)

    summary = {
        "result_tag": tag,
        "ensemble": "LIHC v2 directive weighted + parent-drug dedup",
        "n_hcc_approved_anchors": int(out["is_hcc_approved_anchor"].fillna(False).astype(bool).sum()) if "is_hcc_approved_anchor" in out.columns else 0,
        "n_unique_parents": int(len(out)),
        "tier_counts": out["clinical_tier"].value_counts().sort_index().to_dict(),
        "outputs": {
            "tiered_csv": str(tiered_path.relative_to(project_root)),
            "step6_top30_csv": str(step6_path.relative_to(project_root)),
        },
        "step6_command_hint": (
            "python3 scripts/../Liver cancer/scripts/step6_ext_lihc_independent_cptac_excluded.py "
            f'--project-root "<Liver cancer bundle>" --result-tag {tag}'
        ),
    }
    summary_path = out_dir / "lihc_v2_top30_dedup_tier_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Optional handoff copy under Liver cancer/results/<tag>/ when folder exists
    liver_pkg = project_root.parent.parent / "Liver cancer"
    liver_res = liver_pkg / "results" / tag
    if liver_pkg.is_dir():
        liver_res.mkdir(parents=True, exist_ok=True)
        handoff = liver_res / "lihc_top30_directive_ensemble_with_names.csv"
        out[step6_cols].to_csv(handoff, index=False)
        tiered_copy = liver_res / "lihc_v2_top30_dedup_tiered.csv"
        out.to_csv(tiered_copy, index=False)
        summary["outputs"]["liver_handoff_step6_csv"] = str(handoff)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
