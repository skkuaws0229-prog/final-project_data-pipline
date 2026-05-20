# GCS Workflow Prep - 2026-05-20

## Current GCS Data Root

`gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/`

This repository is now prepared to accept GCS inputs in the local pipeline path without launching any workflow.

## What Changed

- Added `pipeline/utils/cloud_storage.py`.
  - Supports `s3://` through `aws s3`.
  - Supports `gs://` through `gcloud storage`.
  - Provides shared `cp`, `sync`, `object_exists`, `list_objects`, and `object_count` helpers.
- Kept legacy `pipeline/utils/s3_utils.py` function names, but routed transfers through the generic cloud helper.
- Updated Step 1 data collection so `raw_storage_root` or `gcs_raw_root` can point to GCS.
- Updated image-modal preflight/count/cache code so configured `gs://` roots can be listed or synced.
- Added GCS LUNG scripts:
  - `LUNG/workspace_scripts/bootstrap_lung_repro_from_gcs.sh`
  - `LUNG/workspace_scripts/bootstrap_lung_step0_raw_from_gcs.sh`
  - `LUNG/workspace_scripts/sync_lung_repro_to_gcs.sh`
- Existing AWS/SageMaker scripts remain unchanged.

## Important Guardrail

No pipeline execution was run during this prep. The new scripts are ready to run later, but were not executed.

## Example GCS Inputs For Later

```zsh
export GCS_WORKFLOW_ROOT="gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso"
export RAW_STORAGE_ROOT="$GCS_WORKFLOW_ROOT/202604_Final_data/LUNG/raw_source_snapshot/Lung_raw"
export GCS_RAW_WSI_ROOT="$GCS_WORKFLOW_ROOT/202604_Final_data/LUNG/0.Image_modal_LUAD"
```

For an actual LUNG reproducibility restore later:

```zsh
./LUNG/workspace_scripts/bootstrap_lung_repro_from_gcs.sh /path/to/workspace
./LUNG/workspace_scripts/bootstrap_lung_step0_raw_from_gcs.sh /path/to/workspace
```

## Remaining Before Real GCP Execution

1. Choose the actual runner: local machine, VM, Cloud Run Jobs, or Workflows.
2. Map each disease config to its exact GCS prefix.
3. Run only preflight/dry-run first.
4. Start real execution only after output prefixes and cost controls are confirmed.
