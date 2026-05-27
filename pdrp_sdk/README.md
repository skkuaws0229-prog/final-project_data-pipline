# PDRP SDK v0.2

Small internal SDK for the Precision Drug Repurposing Platform workflow.

This version wraps the GCS 4-agent loop behind disease profiles.

```python
from pathlib import Path
from pdrp_sdk import FourAgentWorkflow, WorkflowConfig

config = WorkflowConfig.from_repo_root(Path("."), disease="COAD")
workflow = FourAgentWorkflow(config)
result = workflow.run(vm_status_override="TERMINATED")
```

## Modules

- `config.py`: workflow paths and cloud settings.
- `compute.py`: VM status helpers.
- `storage.py`: GCS upload helpers.
- `agents.py`: Preflight/QA, Pipeline, Image-Modal, Evidence/Report agents.
- `workflow.py`: Master Orchestrator.
- `db.py`: DB status placeholder. No Postgres load is performed in v0.2.
- `config.py`: disease profiles. v0.2 ships with COAD and LUAD.

## Current Scope

- COAD and LUAD profiles included.
- Other diseases can use the same SDK by registering a `DiseaseProfile` with paths/scripts/output names.
- Resume-safe default mode.
- Optional heavy rerun via CLI `--run-heavy`.
- Optional VM lifecycle control via CLI `--manage-vm`.
- Image-modal mode control via CLI `--image-mode`:
  `reuse-existing`, `smoke-1`, `smoke-3`, or guarded `full`.
- DB loading is intentionally left for a later DB Load Agent.

## LUAD Smoke Test

Prepare the LUAD top15 resume input from the existing deduplicated lung ranking:

```bash
python3 vm_scripts/luad_gcs_basic_prepare_top15.py
```

Run the 4-agent loop without heavy recompute:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease LUAD --vm-status-override TERMINATED
```

Run the 4-agent loop on the GCP VM while automatically starting and stopping
the VM from the local controller:

```bash
python3 vm_scripts/run_gcp_4agent_orchestration_with_vm_lifecycle.py --disease LUAD --upload-gcs
```

The controller always attempts to stop the VM in a `finally` block unless
`--no-stop` is passed for debugging.

Image-modal defaults to the conservative reuse path:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease LUAD --image-mode reuse-existing
```

Verified LUAD GCP UNI2 smoke artifacts can be required before remapping:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease LUAD --image-mode smoke-3
```

Full image-modal recompute remains guarded. `--image-mode full` fails unless
`--allow-image-full` is passed, and the SDK currently records it as not wired
for automatic full recompute yet.

The current LUAD evidence agent is a scaffold. It preserves the existing LUAD
4-tier labels and marks rows for refreshed source retrieval plus human
clinical/scientific signoff before DB loading or final use.

## Adding Another Disease

Add a new profile in `pdrp_sdk/config.py`:

```python
DISEASE_PROFILES["STAD"] = DiseaseProfile(
    disease="STAD",
    disease_folder="STAD",
    image_modal_dirname="0.Image_modal_STAD",
    artifact_slug="stad_gcs",
    runtime_root=Path("/path/to/stad/runtime"),
    local_step3_fallback=Path("/path/to/stad/admet_filtered_top15.csv"),
    step_scripts=(
        "vm_scripts/stad_gcs_basic_step1_preflight.sh",
        "vm_scripts/stad_gcs_basic_step2_preflight.sh",
        "vm_scripts/stad_gcs_basic_step3_preflight.sh",
    ),
    im4c_remap_script="vm_scripts/stad_gcs_basic_top15_im4c_remap.py",
    evidence_agent_script="vm_scripts/stad_gcs_basic_top15_evidence_agent.py",
)
```
