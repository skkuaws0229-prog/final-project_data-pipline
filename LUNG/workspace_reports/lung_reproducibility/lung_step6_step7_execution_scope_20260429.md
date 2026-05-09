# LUNG Step6-Step7 Execution Scope

- Date: 2026-04-29
- Basis: user-approved execution scope for current LUNG rerun

## Step 6

- Primary external validation:
  - `PRISM`
  - `ClinicalTrials.gov`
  - `COSMIC`
  - `CPTAC`
- Current decision:
  - Re-run Step 6 for the **current directive-ensemble Top30**
  - Treat the current finalized Top30 as the official Step6 input
  - Require `canonical_smiles` completeness before Step7 entry

## Top30 finalization rule before Step6

- Base ranking source: `reports/lung_directive_ensemble/lung_directive_ensemble_top30_by_eval_mode.csv`
- Eval mode: `unseen_drug`
- Selection rule:
  - sort by ensemble mean predicted IC50 ascending
  - deduplicate by normalized drug name
  - exclude candidates with missing `canonical_smiles`
- Current explicit decision:
  - `TAF1_5496` remains a `Tier4` research compound for interpretation
  - It is excluded from the final Top30 because `canonical_smiles` is unavailable
  - `Doramapimod` enters as the next valid candidate

## Step 7

- Scope:
  - `step7_0_remove_duplicates.py`
  - `step7_1_admet_filtering.py`
  - `step7_2_select_top15.py`
- Current decision:
  - Step7 input is the current 30-drug ranking regenerated from Step6 current-package outputs
  - Run Step7 sequentially after Step6 rerun
  - Use the current rerun outputs, not legacy `41-drug` outputs

## Category alignment

- `Tier1`: LUNG 치료제
- `Tier2`: 타암 치료제 + LUNG 적응증 확장 연구
- `Tier3`: LUNG 미사용 치료제
- `Tier4`: 화합물 / 확인 필요 약물

## Implementation note

- Legacy LUNG scripts originally assumed earlier `phase2b/phase2c catboost` files and a larger downstream set.
- Current rerun adapts those scripts to:
  - the current directive-based LUAD ensemble
  - the current deduplicated SMILES-complete Top30
  - the current Step6 rerun ranking
