from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import WorkflowConfig
from .utils import run_cmd


def upload_auto_loop_outputs(config: WorkflowConfig, output_dir: Path) -> dict[str, Any]:
    if shutil.which("gcloud") is None:
        return {"status": "skipped", "reason": "gcloud_not_available"}
    targets = [
        (output_dir, f"{config.gcs_base}/results/{output_dir.name}/"),
        (config.repo_root / "vm_scripts" / "coad_gcs_4agent_auto_loop.py", f"{config.gcs_base}/code/"),
        (config.repo_root / "vm_scripts" / "COAD_GCS_4AGENT_AUTO_LOOP.md", f"{config.gcs_base}/code/"),
        (config.repo_root / "pdrp_sdk", f"{config.gcs_base}/code/pdrp_sdk/"),
    ]
    uploaded: list[str] = []
    for src, dst in targets:
        cmd = ["gcloud", "storage", "cp"]
        if src.is_dir():
            cmd.append("--recursive")
        cmd.extend([str(src), dst])
        cp = run_cmd(cmd, cwd=config.repo_root, check=False)
        uploaded.append(f"{src} -> {dst} exit={cp.returncode}")
        if cp.returncode != 0:
            return {"status": "failed", "uploaded": uploaded, "stderr": cp.stderr[-1000:]}
    return {"status": "completed", "uploaded": uploaded}
