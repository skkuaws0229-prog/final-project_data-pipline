# LIHC-STAD Operational Protocol (Step4~Step7)

## A. Runtime Context
- Project root:
  - `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260421_new_pre_project_biso_STAD`
- Result tag:
  - `20260428_liver_step4_cv5_gc_sc`
- Data policy:
  - Protocol logic = STAD
  - Input cohort = LIHC (liver)

## B. Step4/5 Execution Rule
- Step4 scripts are STAD-named but configured to read LIHC feature bundle.
- Step5 ensemble uses LIHC directive weights and produces deduplicated Top30.

Required outputs:
- `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble.csv`
- `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble_with_names.csv`
- `results/20260428_liver_step4_cv5_gc_sc/lihc_directive_ensemble_summary.json`

## C. Step6 External Validation Rule (Current Mode)
- Execution mode: `CPTAC_EXCLUDED`
- CPTAC status must remain:
  - `EXCLUDED_BY_REQUEST`

Run command:
- `python3 scripts/step6_ext_lihc_independent_cptac_excluded.py --project-root "<STAD_ROOT>" --result-tag "20260428_liver_step4_cv5_gc_sc"`

Expected summary file:
- `external_validation/20260428_liver_step4_cv5_gc_sc/external_validation_lihc_cptac_excluded_summary.json`

## D. Step7 Rule (Top30 -> ADMET22 -> Top15)
1. Input Top30:
   - `results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble_with_names.csv`
2. ADMET 22 assay:
   - `python3 scripts/step7_1_admet_filtering_stad.py` with `STAD_TOP30_CSV` set to LIHC Top30 file
3. Top15 selection:
   - `python3 scripts/step7_2_select_top15_stad.py`
4. Tier1/2/3/4 output (operational layer for sharing):
   - `results/lihc_step7_final_top15_tier4.csv`

## E. Canonical Deliverables
- External validation table:
  - `external_validation/20260428_liver_step4_cv5_gc_sc/top30_external_validation_lihc_cptac_excluded.csv`
- ADMET scored table:
  - `results/stad_drugs_with_admet.csv`
- Final top15 (base):
  - `results/stad_final_top15.csv`
- Final top15 (tier 1/2/3/4):
  - `results/lihc_step7_final_top15_tier4.csv`

## F. QC Checklist
- [ ] Step6 summary shows `mode=CPTAC_EXCLUDED`
- [ ] Step6 source status is `OK` for PRISM/ClinicalTrials/GEO/OpenTargets/COSMIC
- [ ] Step7 summary shows `total_drugs=30`, `assays_loaded=22`
- [ ] Top15 exists in both base and tier4 files
- [ ] Tier summary file exists: `results/lihc_step7_final_top15_tier4_summary.json`
