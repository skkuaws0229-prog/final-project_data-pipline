#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


WORKSPACE = Path(__file__).resolve().parent.parent
OUT_DIR = WORKSPACE / "reports" / "lung_step6_package"
TOP30_CSV = WORKSPACE / "reports" / "lung_directive_ensemble" / "lung_directive_ensemble_top30_unseen_drug_finalized.csv"
LUNG_ROOT = WORKSPACE / "20260416_new_pre_project_biso_Lung"

DRUG_FEATURES = LUNG_ROOT / "data" / "drug_features.parquet"
GDSC_ANNOT = LUNG_ROOT / "curated_data" / "processed" / "gdsc_annotation.parquet"
CT_MATCHED = LUNG_ROOT / "results" / "lung_clinical_trials_matched_drugs.csv"
PRISM_MATCHED = LUNG_ROOT / "results" / "lung_prism_matched_drugs.csv"
COSMIC_MATCHED = LUNG_ROOT / "results" / "lung_cosmic_matched_drugs.csv"
CPTAC_STATS = LUNG_ROOT / "results" / "lung_cptac_target_expression_stats.csv"


TIER_DEFINITIONS = {
    1: {
        "tier_code": "Tier1",
        "tier_name": "LUNG 치료제",
        "validation_goal": "폐암 치료 맥락의 positive control 및 현재 치료 relevance 확인",
    },
    2: {
        "tier_code": "Tier2",
        "tier_name": "타암 치료제 + LUNG 적응증 확장 연구",
        "validation_goal": "타 적응증 승인 치료제의 lung 확장 가능성 확인",
    },
    3: {
        "tier_code": "Tier3",
        "tier_name": "LUNG 미사용 치료제",
        "validation_goal": "비-lung 치료제의 신규 repurposing 가능성 탐색",
    },
    4: {
        "tier_code": "Tier4",
        "tier_name": "화합물 / 확인 필요 약물",
        "validation_goal": "비승인 화합물, 개발 코드명, probe compound 분리",
    },
}


TIER_MAP = {
    "Dactinomycin": (
        3,
        "승인 항암제이지만 현재 lung 표준 치료제로 보기 어렵고 로컬 lung trial exact match도 확인되지 않아 Tier3로 분류",
    ),
    "Docetaxel": (
        1,
        "폐암 특히 NSCLC에서 실제 사용되는 taxane 계열 치료제로 현재 lung 치료 맥락의 positive control 역할 가능",
    ),
    "Paclitaxel": (
        1,
        "폐암 치료에 사용되는 taxane 계열 약물로 lung 치료제 기준에 부합",
    ),
    "Tanespimycin": (
        4,
        "lung trial 흔적은 있으나 승인 치료제로 정착되지 않은 HSP90 억제제 개발 후보이므로 화합물/확인 필요군으로 분리",
    ),
    "Teniposide": (
        3,
        "승인 치료제이지만 주 적응증은 혈액암 계열이며 현재 lung 직접 사용 근거가 부족",
    ),
    "BX795": (
        4,
        "승인 치료제가 아닌 연구용 kinase inhibitor 화합물",
    ),
    "Pictilisib": (
        4,
        "개발 코드명 기반 PI3K 억제제 후보로 승인 치료제군으로 보기 어려움",
    ),
    "Sinularin": (
        4,
        "천연물/연구용 후보 성격이 강해 임상 사용 약물군과 분리 필요",
    ),
    "BI-2536": (
        4,
        "승인 치료제가 아닌 PLK 억제제 개발 화합물",
    ),
    "EPZ004777": (
        4,
        "Preclinical 단계로 표기되는 DOT1L 억제제 화합물",
    ),
    "Bleomycin (50 uM)": (
        4,
        "승인 약물명에 실험 농도 표기가 섞여 있어 현재 후보 식별자 확인이 필요하므로 Tier4로 분리",
    ),
    "Entinostat": (
        4,
        "lung trial exact match는 있으나 승인 치료제로 사용 중이라고 보기 어려운 investigational 후보",
    ),
    "EPZ5676": (
        4,
        "개발 코드명 기반 후보로 승인 치료제군과 분리",
    ),
    "UNC0379": (
        4,
        "연구용 chemical probe 성격의 화합물",
    ),
    "SGC-CBP30": (
        4,
        "SGC 계열 probe compound로 임상 치료제보다는 연구용 화합물",
    ),
    "TAF1_5496": (
        4,
        "연구용 bromodomain/TAF1 관련 화합물로 확인 필요",
    ),
    "Doramapimod": (
        4,
        "승인 폐암 치료제가 아닌 p38/JNK 계열 investigational compound로 신규 탐색/비승인 실험용 후보에 해당",
    ),
    "AZD8055": (
        4,
        "개발 코드명 기반 mTOR 억제제 후보로 승인 치료제로 보기 어려움",
    ),
    "Buparlisib": (
        4,
        "개발 단계 PI3K 억제제 후보로 현재 승인 치료제군에 속하지 않음",
    ),
    "Elesclomol": (
        4,
        "개발/재평가 단계 후보로 현재 임상 표준 치료제로 보기 어려움",
    ),
    "Venetoclax": (
        2,
        "혈액암에서 사용 중인 승인 치료제이며 로컬 lung clinical trials 원문에서 NSCLC 포함 확장 코호트 흔적이 확인되어 Tier2로 분류",
    ),
    "Methotrexate": (
        3,
        "광범위 승인 치료제이지만 lung 직접 사용 근거가 현재 후보군 내에서 제한적",
    ),
    "OF-1": (
        4,
        "승인 치료제가 아닌 epigenetic probe compound",
    ),
    "GSK343": (
        4,
        "승인 치료제가 아닌 EZH 관련 연구용 화합물",
    ),
    "Bortezomib": (
        2,
        "다발골수종 등에서 사용 중인 승인 치료제이며 로컬 lung clinical trials 원문에 NSCLC 대상 bortezomib 연구가 확인되어 Tier2로 분류",
    ),
    "Savolitinib": (
        1,
        "MET exon 14 skipping NSCLC 맥락에서 lung-targeted therapy로 사용되는 약물로 Tier1에 해당",
    ),
    "PFI3": (
        4,
        "연구용 bromodomain inhibitor/probe 성격의 화합물",
    ),
    "IOX2": (
        4,
        "실험용 HIF pathway 화합물로 승인 치료제군과 분리",
    ),
    "NVP-ADW742": (
        4,
        "개발 코드명 기반 IGF1R 억제제 후보",
    ),
    "KU-55933": (
        4,
        "ATM inhibitor 연구용 화합물",
    ),
    "Piperlongumine": (
        4,
        "천연물/실험 후보로 승인 치료제 분류가 어려움",
    ),
}


def build_top30_table() -> pd.DataFrame:
    top = pd.read_csv(TOP30_CSV)
    top["canonical_drug_id"] = top["canonical_drug_id"].astype(str)

    feature_cols = ["canonical_drug_id", "canonical_smiles", "canonical_smiles_raw", "drug_name_norm", "has_smiles"]
    missing_feature_cols = [c for c in feature_cols if c not in top.columns]
    features = pd.read_parquet(DRUG_FEATURES)[["canonical_drug_id", *[c for c in missing_feature_cols if c != "canonical_drug_id"]]].copy()
    features["canonical_drug_id"] = features["canonical_drug_id"].astype(str)

    gdsc_needed = [c for c in ["DRUG_NAME", "TARGET", "TARGET_PATHWAY"] if c not in top.columns]
    gdsc = pd.read_parquet(GDSC_ANNOT)[["DRUG_ID", *gdsc_needed]].copy()
    gdsc["canonical_drug_id"] = gdsc["DRUG_ID"].astype(str)
    gdsc = gdsc.drop(columns=["DRUG_ID"]).drop_duplicates(subset=["canonical_drug_id"])

    ct = pd.read_csv(CT_MATCHED)
    ct["canonical_drug_id"] = ct["canonical_drug_id"].astype(str)
    ct_agg = (
        ct.groupby("canonical_drug_id", as_index=False)
        .agg(
            ct_match_count=("nct_id", "nunique"),
            ct_statuses=("ct_status", lambda s: "|".join(sorted(s.dropna().astype(str).unique()))),
        )
    )

    prism = pd.read_csv(PRISM_MATCHED)
    prism["canonical_drug_id"] = prism["canonical_drug_id"].astype(str)
    prism_agg = (
        prism.groupby("canonical_drug_id", as_index=False)
        .agg(
            prism_match_count=("prism_broad_id", "nunique"),
            prism_phase=("prism_phase", lambda s: "|".join(sorted(s.dropna().astype(str).unique()))),
            prism_moa=("prism_moa", lambda s: "|".join(sorted(s.dropna().astype(str).unique()[:3]))),
        )
    )

    cosmic = pd.read_csv(COSMIC_MATCHED, low_memory=False)
    cosmic["canonical_drug_id"] = cosmic["canonical_drug_id"].astype(str)
    cosmic_agg = (
        cosmic.groupby("canonical_drug_id", as_index=False)
        .agg(
            cosmic_match_count=("GENOMIC_MUTATION_ID", "size"),
            cosmic_trial_count=("TRIAL_ID", "nunique"),
        )
    )

    cptac = pd.read_csv(CPTAC_STATS)
    cptac["canonical_drug_id"] = cptac["canonical_drug_id"].astype(str)
    cptac_agg = (
        cptac.groupby("canonical_drug_id", as_index=False)
        .agg(
            cptac_target_count=("target", "nunique"),
            cptac_dataset_count=("dataset", "nunique"),
        )
    )

    df = top.copy()
    if len(features.columns) > 1:
        df = df.merge(features, on="canonical_drug_id", how="left")
    if len(gdsc.columns) > 1:
        df = df.merge(gdsc, on="canonical_drug_id", how="left")
    df = (
        df.merge(ct_agg, on="canonical_drug_id", how="left")
        .merge(prism_agg, on="canonical_drug_id", how="left")
        .merge(cosmic_agg, on="canonical_drug_id", how="left")
        .merge(cptac_agg, on="canonical_drug_id", how="left")
    )

    fill_zero_cols = ["ct_match_count", "prism_match_count", "cosmic_match_count", "cosmic_trial_count", "cptac_target_count", "cptac_dataset_count"]
    for col in fill_zero_cols:
        df[col] = df[col].fillna(0).astype(int)
    for col in ["ct_statuses", "prism_phase", "prism_moa"]:
        df[col] = df[col].fillna("")

    tiers = df["drug_name_display"].map(lambda x: TIER_MAP.get(x, (4, "수동 분류 근거가 부족해 Tier4로 임시 분류")))
    df["tier"] = [t[0] for t in tiers]
    df["tier_rationale"] = [t[1] for t in tiers]
    df["tier_code"] = df["tier"].map(lambda t: TIER_DEFINITIONS[t]["tier_code"])
    df["tier_name"] = df["tier"].map(lambda t: TIER_DEFINITIONS[t]["tier_name"])
    df["tier_validation_goal"] = df["tier"].map(lambda t: TIER_DEFINITIONS[t]["validation_goal"])
    df["classification_status"] = "lung_manual_tiering_20260429"
    df["has_any_external_evidence"] = (
        (df["ct_match_count"] > 0)
        | (df["prism_match_count"] > 0)
        | (df["cosmic_match_count"] > 0)
        | (df["cptac_target_count"] > 0)
    )

    return df


def first_existing(patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(LUNG_ROOT.glob(pattern))
        if matches:
            return matches[0]
    return None


def readiness_checks(top30: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    required = {
        "top30_dedup_csv": TOP30_CSV,
        "drug_features_parquet": DRUG_FEATURES,
        "gdsc_annotation_parquet": GDSC_ANNOT,
        "clinicaltrials_all_studies_json": LUNG_ROOT / "curated_data" / "validation" / "clinicaltrials" / "clinicaltrials_lung_cancer_all_studies.json",
        "clinicaltrials_summary_json": LUNG_ROOT / "curated_data" / "validation" / "clinicaltrials" / "clinicaltrials_lung_cancer_summary.json",
        "prism_treatment_info_csv": LUNG_ROOT / "curated_data" / "validation" / "prism" / "prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv",
        "prism_cell_line_info_csv": LUNG_ROOT / "curated_data" / "validation" / "prism" / "prism-repurposing-20q2-primary-screen-cell-line-info.csv",
        "cosmic_actionability_tar": LUNG_ROOT / "curated_data" / "validation" / "cosmic" / "Actionability_AllData_Tsv_v19_GRCh37.tar",
        "cosmic_cgc_tar": LUNG_ROOT / "curated_data" / "validation" / "cosmic" / "Cosmic_CancerGeneCensus_Tsv_v103_GRCh38.tar",
        "cptac_mrna_file": first_existing(["curated_data/cptac/*/data_mrna_seq_fpkm.txt"]),
        "cptac_clinical_patient_file": first_existing(["curated_data/cptac/*/data_clinical_patient.txt"]),
        "prior_ct_results_json": LUNG_ROOT / "results" / "lung_clinical_trials_validation_results.json",
        "prior_prism_results_json": LUNG_ROOT / "results" / "lung_prism_validation_results.json",
        "prior_cosmic_results_json": LUNG_ROOT / "results" / "lung_cosmic_validation_results.json",
        "prior_cptac_results_json": LUNG_ROOT / "results" / "lung_cptac_validation_results.json",
    }

    rows = []
    all_ok = True
    for key, path in required.items():
        exists = path is not None and path.exists()
        all_ok = all_ok and exists
        size = path.stat().st_size if exists and path.is_file() else None
        rows.append(
            {
                "check_id": key,
                "exists": bool(exists),
                "path": str(path) if path is not None else "",
                "size_bytes": size,
            }
        )
    checks_df = pd.DataFrame(rows)

    summary = {
        "top30_candidate_count": int(len(top30)),
        "unique_drug_name_count": int(top30["drug_name_display"].nunique()),
        "canonical_smiles_coverage": int(top30["canonical_smiles"].notna().sum()),
        "gdsc_target_coverage": int(top30["TARGET"].notna().sum()),
        "tier_coverage": int(top30["tier"].notna().sum()),
        "ct_evidence_drug_count": int((top30["ct_match_count"] > 0).sum()),
        "prism_evidence_drug_count": int((top30["prism_match_count"] > 0).sum()),
        "cosmic_evidence_drug_count": int((top30["cosmic_match_count"] > 0).sum()),
        "cptac_evidence_drug_count": int((top30["cptac_target_count"] > 0).sum()),
        "ready_to_start_step6_external_validation": bool(
            all_ok
            and len(top30) == 30
            and top30["drug_name_display"].nunique() == 30
            and top30["canonical_smiles"].notna().sum() == 30
            and top30["tier"].notna().sum() == 30
        ),
        "ready_to_enter_step7_now": False,
        "step7_blocker": "Current Top30 has been deduped and tiered, but Step6 external validation has not yet been rerun on this exact package.",
    }
    return checks_df, summary


def build_summary_md(top30: pd.DataFrame, checks_df: pd.DataFrame, summary: dict[str, object]) -> str:
    tier_counts = top30["tier_name"].value_counts()
    lines = [
        "# LUNG Step6 Package",
        "",
        "- Status date: 2026-04-29",
        f"- Ensemble source: `{TOP30_CSV.relative_to(WORKSPACE)}`",
        "- Scope: deduped 30-drug package before Step6 external validation / Step7 ADMET",
        "",
        "## Candidate Summary",
        "",
        f"- Candidate count: `{summary['top30_candidate_count']}`",
        f"- Unique drug names: `{summary['unique_drug_name_count']}`",
        f"- Canonical SMILES coverage: `{summary['canonical_smiles_coverage']}/30`",
        f"- Tier coverage: `{summary['tier_coverage']}/30`",
        "",
        "## Tier Count",
        "",
        "| Tier | Count |",
        "| --- | ---: |",
    ]
    for tier in [1, 2, 3, 4]:
        lines.append(f"| {TIER_DEFINITIONS[tier]['tier_name']} | {int(tier_counts.get(TIER_DEFINITIONS[tier]['tier_name'], 0))} |")

    lines += [
        "",
        "## Top30 Tiered Candidates",
        "",
        top30[
            [
                "dedup_rank",
                "tier_code",
                "drug_name_display",
                "pred_ic50_weighted_mean",
                "confidence_grade",
                "ct_match_count",
                "prism_phase",
            ]
        ]
        .rename(columns={"dedup_rank": "rank"})
        .round(4)
        .to_markdown(index=False),
        "",
        "## External Validation Asset Checks",
        "",
        checks_df.to_markdown(index=False),
        "",
        "## Decision",
        "",
        f"- ready_to_start_step6_external_validation: **{summary['ready_to_start_step6_external_validation']}**",
        f"- ready_to_enter_step7_now: **{summary['ready_to_enter_step7_now']}**",
        f"- blocker: {summary['step7_blocker']}",
        "",
        "## Tier Notes",
        "",
        "- Tier1: 현재 lung 치료 맥락에 직접 연결되는 약물",
        "- Tier2: 다른 암종 치료제로 사용 중이며 lung 적응증 확장/연구 흔적이 있는 약물",
        "- Tier3: 승인 치료제지만 lung 직접 사용 근거가 현재 패키지 기준 제한적인 약물",
        "- Tier4: 비승인 화합물, probe compound, 개발 코드명, 또는 추가 확인이 필요한 약물",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top30 = build_top30_table()
    checks_df, summary = readiness_checks(top30)

    ordered_cols = [
        "dedup_rank",
        "raw_rank",
        "tier",
        "tier_code",
        "tier_name",
        "tier_validation_goal",
        "canonical_drug_id",
        "drug_name_display",
        "DRUG_NAME",
        "TARGET",
        "TARGET_PATHWAY",
        "pred_ic50_weighted_mean",
        "ensemble_member_std_mean",
        "top_model_vote_count",
        "confidence_grade",
        "canonical_smiles",
        "drug_name_norm",
        "ct_match_count",
        "ct_statuses",
        "prism_match_count",
        "prism_phase",
        "prism_moa",
        "cosmic_match_count",
        "cosmic_trial_count",
        "cptac_target_count",
        "cptac_dataset_count",
        "has_any_external_evidence",
        "tier_rationale",
        "classification_status",
    ]
    top30 = top30[ordered_cols].copy()

    tiered_csv = OUT_DIR / "lung_step6_top30_tiered_candidates.csv"
    tiered_json = OUT_DIR / "lung_step6_top30_tiered_candidates.json"
    checks_csv = OUT_DIR / "lung_step6_external_validation_readiness_checks.csv"
    readiness_json = OUT_DIR / "lung_step6_external_validation_readiness_summary.json"
    summary_md = OUT_DIR / "lung_step6_package_summary.md"

    top30.to_csv(tiered_csv, index=False)
    tiered_json.write_text(top30.to_json(orient="records", indent=2, force_ascii=False), encoding="utf-8")
    checks_df.to_csv(checks_csv, index=False)
    readiness_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_md.write_text(build_summary_md(top30, checks_df, summary), encoding="utf-8")

    print(f"wrote: {tiered_csv}")
    print(f"wrote: {tiered_json}")
    print(f"wrote: {checks_csv}")
    print(f"wrote: {readiness_json}")
    print(f"wrote: {summary_md}")


if __name__ == "__main__":
    main()
