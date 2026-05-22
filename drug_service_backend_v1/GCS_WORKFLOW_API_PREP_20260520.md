# GCS Workflow API Prep - 2026-05-20

## Current GCS Data Root

`gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/`

The migrated workflow-data prefix has already been checked against the original S3 keys:

- S3 files: 13,861
- GCS files: 13,861
- Missing from GCS: 0
- Extra in GCS: 0

## Backend/API Changes Prepared

- Added `gcp_workflows` as a valid pipeline execution backend.
- Added `%` as the UI/API shortcut alias for `gcp_workflows`.
- Added GCS config values:
  - `PIPELINE_ENABLE_GCP_WORKFLOWS`
  - `PIPELINE_DEFAULT_GCS_PREFIX`
  - `WORKFLOW_DATA_GCS_ROOT`
- Existing AWS settings remain intact.
- The pipeline DB schema now updates existing check constraints so old DBs can accept `gcp_workflows`.
- The existing DB column `s3_output_prefix` is kept for compatibility. For `gcp_workflows`, it can contain a `gs://` prefix.
- AlphaFold structure paths now accept `gs://` storage URIs as well as legacy `s3://` URIs.

## Guardrail

`gcp_workflows` is intentionally disabled by default:

```env
PIPELINE_ENABLE_GCP_WORKFLOWS=false
```

Even if enabled, the current `GcpWorkflowsOrchestrator` is a prepared placeholder and does not launch a real GCP workflow yet. This keeps the API ready without accidentally spending compute or starting jobs before VM/Cloud Run/Workflows are designed.

## Next Execution-Readiness Steps

1. Decide the GCP execution target: local runner, Cloud Run Jobs, Workflows, or VM.
2. Implement the real `GcpWorkflowsOrchestrator.start_run`.
3. Add a small dry-run/preflight endpoint or CLI check that validates:
   - `gcloud auth list`
   - active project
   - bucket read access
   - target output prefix write access
4. Flip `PIPELINE_ENABLE_GCP_WORKFLOWS=true` only after the runner is implemented.
