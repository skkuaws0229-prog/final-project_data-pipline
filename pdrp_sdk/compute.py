from __future__ import annotations

import shutil

from .config import WorkflowConfig
from .utils import run_cmd


def gcloud_available() -> bool:
    return shutil.which("gcloud") is not None


def get_vm_status(config: WorkflowConfig) -> str:
    if not gcloud_available():
        return "unknown"
    try:
        cp = run_cmd(
            [
                "gcloud",
                "compute",
                "instances",
                "describe",
                config.vm_name,
                "--zone",
                config.vm_zone,
                "--format=value(status)",
            ],
            cwd=config.repo_root,
            check=False,
        )
        return cp.stdout.strip() or "unknown"
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"check_failed:{exc}"
