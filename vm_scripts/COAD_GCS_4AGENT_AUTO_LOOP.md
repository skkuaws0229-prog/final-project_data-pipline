# GCS 4-Agent Auto Loop

Agents:

- Master Orchestrator
- Preflight/QA Agent
- Pipeline Agent
- Image-Modal Agent
- Evidence/Report Agent

Safe resume run:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease COAD
```

Safe resume run when VM status was already checked externally:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease COAD --vm-status-override TERMINATED
```

Heavy rerun:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease COAD --run-heavy
```

GCS upload:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease COAD --upload-gcs
```

Outputs:

```text
Colon/0.Image_modal_COAD/step_gcs_basic_top15_4agent_auto_loop/
  coad_gcs_4agent_auto_loop_summary.json
  coad_gcs_4agent_auto_loop_report.md
```

DB status:

- CSV/JSON/Markdown artifacts: done
- GitHub/GCS artifact preservation: done
- Postgres/service DB load: not yet done

Add a separate DB Load Agent after the backend target schema and canonical import path are finalized.

SDK v0.2 keeps COAD as the default profile and supports adding more diseases by registering a `DiseaseProfile` in `pdrp_sdk/config.py`.
