# LUAD GCP Full Run Plan

## Scope

This plan is for running LUAD from GCS-backed inputs on a GCP VM.

## Confirmed

- Basic pipeline Step1/Step2/Step3 can be configured for GCP VM execution.
- GCS raw/repro inputs are under:
  - `gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/202604_Final_data/LUNG/`
- The SDK LUAD disease profile is registered.
- The previous LUAD run reused existing outputs; it was not a from-scratch model rerun.

## GCP VM Execution Order

1. Start GCP VM.
2. Pull the GitHub repo on the VM.
3. Run Step1/Step2/Step3 from scratch:

```bash
bash vm_scripts/luad_gcp_vm_step1_3_from_scratch.sh
```

4. Run the SDK orchestrator:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease LUAD --run-heavy --vm-status-override RUNNING
```

## Image-Modal Caveat

The current generic `im1` and `im2` modules still launch AWS SageMaker jobs for WSI download, tiling, and UNI2 embedding. They are not yet GCP-native.

For an all-GCP run, IM1/IM2 must be ported to one of:

- GCP VM direct WSI download + tiling + UNI2 embedding
- GCP Batch
- Vertex AI custom job

Until that port is done, the GCP-only safe scope is:

- Basic pipeline Step1/Step2/Step3 from GCS on GCP VM
- ADMET/top15
- Existing LUAD image-modal reuse/remap
- Evidence scaffold
- 4-agent orchestration

## Do Not Do

- Do not let `im1`/`im2` auto-launch while still using AWS SageMaker.
- Do not call the previous LUAD reused-output loop a full from-scratch run.
