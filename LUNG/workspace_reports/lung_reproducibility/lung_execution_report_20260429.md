# LUNG Execution Report

- Date: 2026-04-29
- Scope: current LUNG/LUAD rerun from Step5 to Step7

## Summary

- Step5 directive ensemble rerun completed
- Top30 finalized with `30/30` unique names and `30/30` canonical SMILES
- Step6 external validation rerun completed on the exact finalized package
- Step7 duplicate cleanup, ADMET filtering, and Top15 selection completed

## Step5

- Ensemble source script: `scripts/build_lung_directive_ensemble.py`
- Finalization script: `scripts/finalize_lung_top30.py`
- Current replacement:
  - removed from final Top30: `TAF1_5496`
  - retained as Tier interpretation only: `Tier4 research compound`
  - replacement added to final Top30: `Doramapimod`

## Step6

- Package script: `scripts/prepare_lung_step6_package.py`
- Validation rerun script: `scripts/run_lung_step6_current_package.py`
- Current external validation counts:
  - PRISM matched drugs: `19`
  - ClinicalTrials matched drugs: `10`
  - COSMIC matched drugs: `12`
  - CPTAC expression-supported drugs: `13`

## Step7

- Duplicate removal: completed
- ADMET result:
  - PASS: `28`
  - FAIL: `2`
- Fail drugs:
  - `Venetoclax`
  - `Bleomycin (50 uM)`

## Current final top15

1. Docetaxel
2. Paclitaxel
3. Savolitinib
4. Entinostat
5. Tanespimycin
6. Bortezomib
7. Methotrexate
8. Buparlisib
9. Pictilisib
10. Dactinomycin
11. EPZ004777
12. Teniposide
13. IOX2
14. BI-2536
15. EPZ5676

## Canonical output files

- Step5:
  - `reports/lung_directive_ensemble/`
- Step6 package:
  - `reports/lung_step6_package/`
- Step6 current rerun:
  - `reports/lung_step6_current_package/`
- Step7:
  - `20260416_new_pre_project_biso_Lung/results/lung_drugs_with_admet.csv`
  - `20260416_new_pre_project_biso_Lung/results/lung_final_top15.csv`

## Reproducibility status

- Current rerun can be reproduced if the following are available together:
  - `20260416_new_pre_project_biso_Lung/`
  - current workspace `reports/lung_*`
  - current helper scripts in `scripts/`
  - dependent Step4 LUAD `2C_numeric_smiles_context` outputs from the multicancer rerun source tree
