# LIHC Data + STAD Protocol Execution Report

## 1) Scope
- Protocol: STAD workflow scripts (`20260421_new_pre_project_biso_STAD`)
- Data cohort: LIHC (Liver) features and staged external validation bundle
- Result tag: `20260428_liver_step4_cv5_gc_sc`
- Exclusion policy: CPTAC excluded in external validation (`EXCLUDED_BY_REQUEST`)

## 2) Step4/Step5 Highlights
- Ensemble name: `LIHC_directive_weighted_v1`
- OOF eval mode: `groupcv_oof`
- OOF Spearman vs y_train: `0.5753716199682973`
- Top30 output:
  - `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble.csv`
  - `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble_with_names.csv`
  - `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_tier4_table.csv`

## 3) Step6 External Validation (CPTAC Excluded)
- Run summary:
  - `external_validation/20260428_liver_step4_cv5_gc_sc/external_validation_lihc_cptac_excluded_summary.json`
  - `external_validation/20260428_liver_step4_cv5_gc_sc/reports/external_validation_run_lihc_cptac_excluded.md`
- Source status:
  - PRISM: `OK`
  - ClinicalTrials: `OK`
  - GEO: `OK`
  - OpenTargets: `OK`
  - COSMIC: `OK`
  - CPTAC: `EXCLUDED_BY_REQUEST`
- Supported rows in Top30:
  - PRISM: `30`
  - ClinicalTrials: `17`
  - GEO: `7`
  - OpenTargets: `13`
  - COSMIC: `8`
  - CPTAC: `0`

## 4) Step7 ADMET Gate and Final Top15
- Step7-1 summary: `results/stad_admet_summary.json`
  - Total input drugs: `30`
  - Assays loaded: `22`
  - Verdict counts: `PASS=5`, `WARNING=22`, `FAIL=3`
- Step7-2 outputs:
  - `results/stad_final_top15.csv`
  - `results/stad_final_top15_summary.json`
  - `results/stad_step7_three_stage_summary.json`

## 5) Tier 1/2/3/4 for Top15
- File: `results/lihc_step7_final_top15_tier4.csv`
- Summary: `results/lihc_step7_final_top15_tier4_summary.json`
- Tier counts:
  - `tier1=3`
  - `tier2=2`
  - `tier3=8`
  - `tier4=2`

## 6) Key Files by Stage
- Step4/5 metrics and ensemble:
  - `results/20260428_liver_step4_cv5_gc_sc/step5_gate_eval_spearman_table.json`
  - `results/20260428_liver_step4_cv5_gc_sc/lihc_directive_ensemble_summary.json`
- Step6 external table:
  - `external_validation/20260428_liver_step4_cv5_gc_sc/top30_external_validation_lihc_cptac_excluded.csv`
- Step7 ranking tables:
  - `results/stad_drugs_with_admet.csv`
  - `results/stad_final_top15.csv`
  - `results/lihc_step7_final_top15_tier4.csv`
