from __future__ import annotations

import shutil
from typing import Any

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
                "--project",
                config.vm_project,
                "--format=value(status)",
            ],
            cwd=config.repo_root,
            check=False,
        )
        return cp.stdout.strip() or "unknown"
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"check_failed:{exc}"


def _instance_command(config: WorkflowConfig, action: str) -> dict[str, Any]:
    if not gcloud_available():
        return {"action": action, "status": "skipped", "reason": "gcloud_not_available"}
    cp = run_cmd(
        [
            "gcloud",
            "compute",
            "instances",
            action,
            config.vm_name,
            "--zone",
            config.vm_zone,
            "--project",
            config.vm_project,
        ],
        cwd=config.repo_root,
        check=False,
    )
    return {
        "action": action,
        "status": "completed" if cp.returncode == 0 else "failed",
        "returncode": cp.returncode,
        "stdout_tail": cp.stdout[-1200:],
        "stderr_tail": cp.stderr[-1200:],
        "vm_status_after": get_vm_status(config),
    }


def start_vm(config: WorkflowConfig) -> dict[str, Any]:
    status = get_vm_status(config)
    if status == "RUNNING":
        return {"action": "start", "status": "skipped", "reason": "already_running", "vm_status_after": status}
    return _instance_command(config, "start")


def stop_vm(config: WorkflowConfig) -> dict[str, Any]:
    status = get_vm_status(config)
    if status == "TERMINATED":
        return {"action": "stop", "status": "skipped", "reason": "already_terminated", "vm_status_after": status}
    return _instance_command(config, "stop")
