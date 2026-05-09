from __future__ import annotations

import subprocess
from typing import Any


def run_command_step(config: dict, key: str, dry_run: bool = False) -> dict[str, Any]:
    command = config.get("commands", {}).get(key)
    if not command:
        return {"status": "skipped", "reason": f"no command configured for {key}"}
    if dry_run:
        return {"status": "dry_run", "command": command}
    completed = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
    return {"status": "completed", "stdout": completed.stdout, "stderr": completed.stderr}


def run(config: dict, dry_run: bool = False) -> dict:
    return run_command_step(config, "step2_basic_pipeline", dry_run)

