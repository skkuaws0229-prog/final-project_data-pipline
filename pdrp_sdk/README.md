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
- `db.py`: DB status placeholder. No Postgres load is performed in v0.1.
- `config.py`: disease profiles. v0.2 ships with COAD and is ready for additional profiles.

## Current Scope

- COAD profile included.
- Other diseases can use the same SDK by registering a `DiseaseProfile` with paths/scripts/output names.
- Resume-safe default mode.
- Optional heavy rerun via CLI `--run-heavy`.
- DB loading is intentionally left for a later DB Load Agent.

## Adding Another Disease

Add a new profile in `pdrp_sdk/config.py`:

```python
DISEASE_PROFILES["LUAD"] = DiseaseProfile(
    disease="LUAD",
    disease_folder="LUNG",
    image_modal_dirname="0.Image_modal_LUAD",
    artifact_slug="luad_gcs",
    runtime_root=Path("/path/to/luad/runtime"),
    local_step3_fallback=Path("/path/to/luad/admet_filtered_top15.csv"),
    step_scripts=(
        "vm_scripts/luad_gcs_basic_step1_preflight.sh",
        "vm_scripts/luad_gcs_basic_step2_preflight.sh",
        "vm_scripts/luad_gcs_basic_step3_preflight.sh",
    ),
    im4c_remap_script="vm_scripts/luad_gcs_basic_top15_im4c_remap.py",
    evidence_agent_script="vm_scripts/luad_gcs_basic_top15_evidence_agent.py",
)
```
