# LIHC External Validation Data Readiness (Updated)

- Result tag: `20260428_liver_step4_cv5_gc_sc`

## Checks
- clinicaltrials_pages_001_006_present: True
- clinicaltrials_summary_present: True
- opentargets_full_direct_table_present: True
- opentargets_direct_part_count: 200
- cosmic_actionability_tar_present: True
- cosmic_cgc_tar_present: True
- cosmic_classification_tar_present: True
- cosmic_mutant_census_tar_present: True
- cptac_manifest_file_count: 0
- cptac_actual_files_ready: False

## Remaining gap
- CPTAC actual files: manifest_file_count=0 (metadata only).

## Execution mode
- external_validation_run: `COMPLETED`
- cptac_mode: `EXCLUDED_BY_REQUEST`
- run_summary_json: `external_validation/20260428_liver_step4_cv5_gc_sc/external_validation_lihc_cptac_excluded_summary.json`

## Notes
- GSE14520 ready and staged.
- ADMET intentionally skipped (Step7).
- COSMIC tar payloads staged from `Liver_raw` (PDAC folder had no cosmic tar payload).