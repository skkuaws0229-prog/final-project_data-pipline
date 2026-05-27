# COAD GCS 4-Agent Auto Loop

Agents:

- Master Orchestrator
- Preflight/QA Agent
- Pipeline Agent
- Image-Modal Agent
- Evidence/Report Agent

Safe resume run:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py
```

Safe resume run when VM status was already checked externally:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --vm-status-override TERMINATED
```

Heavy rerun:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --run-heavy
```

GCS upload:

```bash
python3 vm_scripts/coad_gcs_4agent_auto_loop.py --upload-gcs
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
