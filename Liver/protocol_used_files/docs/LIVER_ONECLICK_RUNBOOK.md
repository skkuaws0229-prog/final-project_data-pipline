# Liver One-Click Runbook

## Purpose
Run LIHC package workflow in one command:
1. Step6 external validation (`CPTAC_EXCLUDED` mode)
2. Step7-1 ADMET 22 assays
3. Step7-2 Top15 selection
4. Tier1/2/3/4 table generation

## Script
- Path: `scripts/run_liver_oneclick.sh`

## S3 Package Location
- Root: `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/`
- Required groups:
  - `raw_source/`
  - `fe_data/`
  - `generated/`
  - `protocol_used_files/`
- Ensemble directive:
  - `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/protocol_used_files/docs/LIHC_ensemble_directive.md`

## Prerequisites
- Python environment with required packages (pandas, numpy, scipy, RDKit)
- Local package root structure preserved (`Liver cancer` folder)
- Input Top30 CSV exists:
  - Recommended(v1): `results/lihc_top30_hcc_anchor3_v1.csv`
  - Or pass absolute path via `--top30-csv`
- ADMET resources available under:
  - `curated_data/admet/tdc_admet_group/admet_group/`
- Drug feature table available:
  - `data/drug_features.parquet`

## Run
```bash
cd "Liver cancer"
bash "scripts/run_liver_oneclick.sh" \
  --top30-csv "/absolute/path/lihc_top30_hcc_anchor3_v1.csv" \
  --result-tag "20260428_liver_step4_cv5_gc_sc"
```

Optional flags:
- `--skip-step6`: skip Step6 and run Step7 only
- env `RESULT_TAG`, `TOP30_CSV`, `SKIP_STEP6` also supported

## Outputs
- Step6 summary:
  - `external_validation/20260428_liver_step4_cv5_gc_sc/external_validation_lihc_cptac_excluded_summary.json`
- Step7 ADMET summary:
  - `results/stad_admet_summary.json`
- Final Top15:
  - `results/lihc_final_top15_v1.csv`
- Tier1/2/3/4:
  - `results/lihc_step7_final_top15_tier4_v1.csv`
  - `results/lihc_step7_final_top15_tier4_summary_v1.json`

## Notes
- This script is for reproducible package execution in the handoff folder.
- CPTAC remains excluded by policy in Step6 outputs.
- Step7 recommendation criterion is HCC approval basis (LIHC), not gastric labels.
- v1 policy uses anchor-mix Top30 input with 3 HCC approved drugs injected for operational reporting.
