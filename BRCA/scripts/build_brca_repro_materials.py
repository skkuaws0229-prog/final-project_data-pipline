#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


WORKSPACE = Path(__file__).resolve().parent.parent
OUT = WORKSPACE / "20260428_new_BRCA_data"

STEP4_SUMMARY = OUT / "brca_model_performance_summary.csv"
STEP5_VALIDATION = OUT / "brca_directive_ensemble_validation_summary.csv"
STEP5_TOP30 = OUT / "brca_directive_top30_tiered_candidates.csv"
STEP6_TOP15 = OUT / "step6_metabric_validation" / "brca_top15_metabric_validated.csv"
STEP6_TOP30 = OUT / "step6_metabric_validation" / "brca_top30_metabric_scored.csv"
STEP7_TOP30 = OUT / "step7_admet_22assay" / "brca_admet_22assay_top30_detailed.csv"
STEP7_TOP15 = OUT / "step7_admet_22assay" / "brca_final15_after_admet.csv"

PROTOCOL_MD = OUT / "BRCA_reproduction_protocol_20260428_v1.md"
REPORT_MD = OUT / "BRCA_experiment_report_20260428.md"
MANIFEST_JSON = OUT / "BRCA_reproducibility_manifest_20260428.json"
README_MD = OUT / "README.md"


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def build_protocol(
    step5_validation: pd.DataFrame,
    step6_top30: pd.DataFrame,
    step7_top30: pd.DataFrame,
) -> str:
    groupcv_a = step5_validation[(step5_validation["config"] == "A") & (step5_validation["eval_mode"] == "groupcv")]
    scaffold_a = step5_validation[(step5_validation["config"] == "A") & (step5_validation["eval_mode"] == "scaffoldcv")]
    groupcv_text = f"{groupcv_a['spearman'].iloc[0]:.4f}" if not groupcv_a.empty else "n/a"
    scaffold_text = f"{scaffold_a['spearman'].iloc[0]:.4f}" if not scaffold_a.empty else "n/a"
    step7_counts = step7_top30["verdict"].value_counts().to_dict() if not step7_top30.empty else {}
    return f"""# BRCA Reproduction Protocol

- Date: 2026-04-28
- Version: v1
- Scope: reproduce the current BRCA rerun from Step4 summary through Step7 ADMET

## Canonical scope

- Step5 ensemble: directive-based A/B comparison, winner = `A`
- Step6 external validation: `METABRIC Method A/B/C`
- Step6 supplemental interpretation: `ClinicalTrials.gov + manual review`
- Step7 safety gate: `ADMET 22 assay`, `TDC benchmark`, `Tanimoto similarity v1`

## Key inputs

- Step4 summary: `brca_model_performance_summary.csv`
- Step5 top30: `brca_directive_top30_unique_candidates.csv`
- Step5 tier map: `brca_directive_top30_tiered_candidates.csv`
- Step6 METABRIC expression:
  `20260415_preproject_protocol_choi/data/metabric/metabric_expression_basic_clean_20260406.parquet`
- Step6 METABRIC clinical:
  `20260415_preproject_protocol_choi/data/metabric/metabric_clinical_patient_basic_clean_20260406.parquet`
- Step7 ADMET assay dir:
  `20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/curated_data/admet/tdc_admet_group/admet_group`

## Fixed decisions

- Ensemble winner: `A`
- GroupCV Spearman: `{groupcv_text}`
- ScaffoldCV Spearman: `{scaffold_text}`
- Step6 input: current BRCA Top30, not legacy consensus top24
- Step7 input: all 30 drugs from current Top30
- Final candidate cut: top 15 after Step7 ranking

## Reproduction order

1. Step4 summary refresh
   - Command: `python3 scripts/extract_brca_step4_summary.py`
   - Output: `brca_model_performance_summary.csv`, `brca_model_performance_detailed.csv`

2. Step5 ensemble rerun
   - Command: `python3 scripts/run_brca_directive_ensemble.py`
   - Output: `brca_directive_ensemble_validation_summary.csv`, `brca_directive_top30_unique_candidates.csv`

3. Tier classification
   - Command: `python3 scripts/classify_brca_top30_tiers.py`
   - Output: `brca_directive_top30_tiered_candidates.csv`

4. Step6 METABRIC rerun
   - Command: `python3 scripts/run_brca_step6_metabric_adapter.py`
   - Output dir: `step6_metabric_validation/`

5. Step7 ADMET rerun
   - Command: `python3 scripts/run_brca_step7_admet_adapter.py`
   - Output dir: `step7_admet_22assay/`

6. Materials refresh
   - Command: `python3 scripts/build_brca_repro_materials.py`

7. Dashboard
   - Command: `streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py`

## Tier definition

- Tier 1: 유방암 치료제
- Tier 2: 유방암 적응증 확장 연구 치료제
- Tier 3: 유방암 비사용 치료제
- Tier 4: 화합물 또는 미지 약물

## Step6 acceptance view

- Current target-expressed drugs: `{int(step6_top30['target_expressed'].sum()) if not step6_top30.empty else 0}/{len(step6_top30)}`
- Current BRCA-pathway drugs: `{int(step6_top30['brca_pathway'].sum()) if not step6_top30.empty else 0}/{len(step6_top30)}`
- Current survival-significant drugs: `{int(step6_top30['survival_sig'].sum()) if not step6_top30.empty else 0}/{len(step6_top30)}`

## Step7 acceptance view

- PASS: `{int((step7_top30['verdict'] == 'PASS').sum()) if not step7_top30.empty else 0}`
- WARNING: `{int((step7_top30['verdict'] == 'WARNING').sum()) if not step7_top30.empty else 0}`
- FAIL: `{int((step7_top30['verdict'] == 'FAIL').sum()) if not step7_top30.empty else 0}`
- Hard fail: `{int(step7_top30['hard_fail'].sum()) if not step7_top30.empty else 0}`

## Interpretation guide

- Step6 METABRIC is a biological validation layer that helps interpret mechanistic plausibility.
- Step7 ADMET 22 assay is the practical ranking layer that produces the current Final15.
- The current Final15 should be read as a mixed shortlist of breast-cancer drugs, indication-expansion therapies, non-breast therapies, and Tier4 compounds.
- Positive controls, repurposing candidates, and discovery-only compounds should be interpreted as different downstream action classes rather than one homogeneous list.
- Tier4 signals can still be valuable, but should be discussed more cautiously than approved therapies.

## Dashboard view

- Overview tab: final status, Step7 counts, Final15 snapshot
- Step5 tab: A/B validation results, Top30 tiered candidate table
- Step6 tab: METABRIC A/B/C metrics and validation score view
- Step7 tab: ADMET verdict distribution, Final15 tier distribution, full assay table

## Notes

- This rerun intentionally separates Step6 and Step7.
- Step6 does not gate the Top30 input for Step7; all 30 current drugs enter ADMET.
- Current Step7 verdict summary: PASS `{int(step7_counts.get('PASS', 0))}`, WARNING `{int(step7_counts.get('WARNING', 0))}`, FAIL `{int(step7_counts.get('FAIL', 0))}`
"""


def build_report(
    step4_summary: pd.DataFrame,
    step5_validation: pd.DataFrame,
    top30: pd.DataFrame,
    step6_top15: pd.DataFrame,
    step7_top30: pd.DataFrame,
    step7_top15: pd.DataFrame,
) -> str:
    top_group = step4_summary.sort_values("groupcv_spearman", ascending=False).head(5)
    groupcv_a = step5_validation[(step5_validation["config"] == "A") & (step5_validation["eval_mode"] == "groupcv")]
    scaffold_a = step5_validation[(step5_validation["config"] == "A") & (step5_validation["eval_mode"] == "scaffoldcv")]
    holdout_a = step5_validation[(step5_validation["config"] == "A") & (step5_validation["eval_mode"] == "holdout")]
    step7_counts = step7_top30["verdict"].value_counts().to_dict() if not step7_top30.empty else {}
    tier_counts = step7_top15["tier_name"].value_counts().to_dict() if not step7_top15.empty else {}

    lines = [
        "# BRCA Experiment Report",
        "",
        "- Date: 2026-04-28",
        "- Experiment line: Step4 screening -> Step5 directive ensemble -> Step6 METABRIC -> Step7 ADMET 22 assay",
        "",
        "## Executive Summary",
        "",
        f"- Ensemble winner: `A`",
        f"- GroupCV Spearman: `{groupcv_a['spearman'].iloc[0]:.4f}`" if not groupcv_a.empty else "- GroupCV Spearman: n/a",
        f"- ScaffoldCV Spearman: `{scaffold_a['spearman'].iloc[0]:.4f}`" if not scaffold_a.empty else "- ScaffoldCV Spearman: n/a",
        f"- Holdout Spearman: `{holdout_a['spearman'].iloc[0]:.4f}`" if not holdout_a.empty else "- Holdout Spearman: n/a",
        f"- Top30 generated: `{len(top30)}`",
        f"- Step6 Top15 generated: `{len(step6_top15)}`",
        f"- Step7 Final15 generated: `{len(step7_top15)}`",
        "",
        "## Step4 Shortlist Context",
        "",
        "| Phase | Family | Model | GroupCV | ScaffoldCV | Overfit Gap |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in top_group.iterrows():
        lines.append(
            f"| {row['phase']} | {row['family']} | {row['model']} | "
            f"{row['groupcv_spearman']:.4f} | {row['scaffoldcv_spearman']:.4f} | {row['overfit_gap_groupcv']:.4f} |"
        )

    lines += [
        "",
        "## Step5 Top30 Tier Mix",
        "",
        "| Tier | Count |",
        "| --- | ---: |",
    ]
    for tier_name, count in top30["tier_name"].value_counts().items():
        lines.append(f"| {tier_name} | {int(count)} |")

    lines += [
        "",
        "## Step6 Highlights",
        "",
        f"- Target-expressed drugs: `{int(step6_top15['target_expressed'].sum()) if not step6_top15.empty else 0}` within Step6 Top15",
        f"- Survival-significant drugs in Step6 Top15: `{int(step6_top15['survival_sig'].sum()) if not step6_top15.empty else 0}`",
        "",
        "| Step6 Rank | Drug | Tier | Validation Score |",
        "| --- | --- | --- | ---: |",
    ]
    for _, row in step6_top15.head(10).iterrows():
        lines.append(
            f"| {int(row['final_rank'])} | {row['drug_name']} | {row['tier_name']} | {row['validation_score']:.3f} |"
        )

    lines += [
        "",
        "## Step7 Highlights",
        "",
        f"- PASS: `{int(step7_counts.get('PASS', 0))}`",
        f"- WARNING: `{int(step7_counts.get('WARNING', 0))}`",
        f"- FAIL: `{int(step7_counts.get('FAIL', 0))}`",
        f"- Hard fail: `{int(step7_top30['hard_fail'].sum()) if not step7_top30.empty else 0}`",
        "",
        "| Final ADMET Rank | Drug | Tier | Verdict | Safety Score | Assay Matches |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for _, row in step7_top15.iterrows():
        lines.append(
            f"| {int(row['final_admet_rank'])} | {row['drug_name']} | {row['tier_name']} | "
            f"{row['verdict']} | {row['safety_score']:.3f} | {int(row['n_total_matches'])} |"
        )

    lines += [
        "",
        "## Final15 Tier Distribution",
        "",
        "| Tier | Count |",
        "| --- | ---: |",
    ]
    for tier_name, count in tier_counts.items():
        lines.append(f"| {tier_name} | {int(count)} |")

    lines += [
        "",
        "## Interpretation",
        "",
        "- This rerun keeps the full Step5 Top30 through Step7, matching the current agreed scope.",
        "- Step6 METABRIC acts as a biological validation layer, while Step7 ADMET 22 assay is the practical selection layer for the current Final15.",
        "- The current Final15 contains a mix of breast-cancer drugs, indication-expansion therapies, non-breast therapies, and Tier4 compounds, so downstream review should interpret efficacy and developability separately.",
        "- Tier4 compounds remain useful as discovery signals, but they should be handled more cautiously than approved therapies in experimental planning and narrative reporting.",
        "",
    ]
    return "\n".join(lines)


def build_manifest() -> dict:
    return {
        "date": "2026-04-28",
        "dashboard": str(OUT / "brca_repro_dashboard.py"),
        "protocol": str(PROTOCOL_MD),
        "report": str(REPORT_MD),
        "step4_summary": str(STEP4_SUMMARY),
        "step5_validation": str(STEP5_VALIDATION),
        "step5_top30": str(STEP5_TOP30),
        "step6_top15": str(STEP6_TOP15),
        "step6_top30": str(STEP6_TOP30),
        "step7_top30": str(STEP7_TOP30),
        "step7_top15": str(STEP7_TOP15),
        "commands": {
            "step4_summary": "python3 scripts/extract_brca_step4_summary.py",
            "step5_ensemble": "python3 scripts/run_brca_directive_ensemble.py",
            "tier_classification": "python3 scripts/classify_brca_top30_tiers.py",
            "step6_metabric": "python3 scripts/run_brca_step6_metabric_adapter.py",
            "step7_admet": "python3 scripts/run_brca_step7_admet_adapter.py",
            "materials": "python3 scripts/build_brca_repro_materials.py",
            "dashboard": "streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py",
        },
    }


def build_readme() -> str:
    return """# 20260428_new_BRCA_data

This folder is the canonical bundle for the current BRCA rerun.

## Main deliverables

- `BRCA_reproduction_protocol_20260428_v1.md`: step-by-step rerun protocol
- `BRCA_experiment_report_20260428.md`: experiment report from Step4 through Step7
- `BRCA_reproducibility_manifest_20260428.json`: machine-readable path/command manifest
- `brca_repro_dashboard.py`: Streamlit dashboard for this BRCA rerun

## Core data products

- `brca_model_performance_summary.csv`: Step4 model screening summary
- `brca_directive_ensemble_validation_summary.csv`: Step5 ensemble comparison
- `brca_directive_top30_tiered_candidates.csv`: Step5 tiered Top30
- `step6_metabric_validation/brca_top15_metabric_validated.csv`: Step6 METABRIC Top15
- `step7_admet_22assay/brca_final15_after_admet.csv`: Step7 final15 after ADMET 22-assay

## Reproduction commands

1. `python3 scripts/extract_brca_step4_summary.py`
2. `python3 scripts/run_brca_directive_ensemble.py`
3. `python3 scripts/classify_brca_top30_tiers.py`
4. `python3 scripts/run_brca_step6_metabric_adapter.py`
5. `python3 scripts/run_brca_step7_admet_adapter.py`
6. `python3 scripts/build_brca_repro_materials.py`
7. `streamlit run 20260428_new_BRCA_data/brca_repro_dashboard.py`
"""


def main() -> None:
    step4_summary = load_csv(STEP4_SUMMARY)
    step5_validation = load_csv(STEP5_VALIDATION)
    top30 = load_csv(STEP5_TOP30)
    step6_top15 = load_csv(STEP6_TOP15)
    step6_top30 = load_csv(STEP6_TOP30)
    step7_top30 = load_csv(STEP7_TOP30)
    step7_top15 = load_csv(STEP7_TOP15)

    PROTOCOL_MD.write_text(build_protocol(step5_validation, step6_top30, step7_top30), encoding="utf-8")
    REPORT_MD.write_text(
        build_report(step4_summary, step5_validation, top30, step6_top15, step7_top30, step7_top15),
        encoding="utf-8",
    )
    MANIFEST_JSON.write_text(json.dumps(build_manifest(), indent=2, ensure_ascii=False), encoding="utf-8")
    README_MD.write_text(build_readme(), encoding="utf-8")

    print(f"wrote: {PROTOCOL_MD}")
    print(f"wrote: {REPORT_MD}")
    print(f"wrote: {MANIFEST_JSON}")
    print(f"wrote: {README_MD}")


if __name__ == "__main__":
    main()
