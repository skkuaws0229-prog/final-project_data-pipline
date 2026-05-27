# PDRP SDK v0.1

Small internal SDK for the Precision Drug Repurposing Platform workflow.

The first version wraps the COAD GCS 4-agent loop:

```python
from pathlib import Path
from pdrp_sdk import FourAgentWorkflow, WorkflowConfig

config = WorkflowConfig.from_repo_root(Path("."))
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

## Current Scope

- COAD only.
- Resume-safe default mode.
- Optional heavy rerun via CLI `--run-heavy`.
- DB loading is intentionally left for a later DB Load Agent.
