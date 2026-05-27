# VM COAD GCS Test Plan - 2026-05-27

## Scope

Prepare a single-disease COAD/Colon test on the GCP VM without launching the real workflow yet.

Current VM:

- Name: `sobi2026-gcs-api-test-vm`
- Zone: `asia-northeast3-a`
- Machine: `e2-standard-2`
- Purpose: API/preflight/dry-run only

## GCS Inputs

- Workflow root: `gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso`
- Colon root: `gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/202604_Final_data/Colon`
- Image-modal evidence: `.../Colon/0.Image_modal_COAD/`
- Basic pipeline outputs: `.../Colon/20260428_colon_v2/`
- Shared inputs: `.../Colon/shared_inputs/`

## Prepared Files

- `vm_configs/04_coad_gcs_dryrun.yaml`
- `vm_scripts/coad_gcs_preflight.sh`

The config is intentionally conservative:

- `skip_download: true`
- `auto_provision_raw: false`
- `image_modal.auto_launch: false`
- `image_modal.disable_auto_launch: true`
- `execution.steps`: image-modal downstream dry-run path only

## Commands On The VM

```bash
cd ~/sobi2026/final-project_data-pipline
./vm_scripts/coad_gcs_preflight.sh
```

This checks:

1. GCS Colon prefix is readable.
2. API pipeline preflight returns `gcp_workflows` as disabled, not executed.
3. Pipeline dry-run can parse and plan the COAD config.

## Machine Choice

Keep `e2-standard-2` for now. It is enough for API checks, GCS listing, and dry-run.

Before real execution, choose one:

- `e2-standard-4`: safer small CPU test for one disease.
- `e2-standard-8`: better if downloading/extracting larger intermediate files.
- GPU VM: only if regenerating image embeddings or model-heavy steps.

Do not enable `PIPELINE_ENABLE_GCP_WORKFLOWS=true` until the actual GCP runner is implemented.
