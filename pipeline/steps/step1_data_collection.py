from __future__ import annotations

from .step2_basic_pipeline import run_command_step


def run(config: dict, dry_run: bool = False) -> dict:
    return run_command_step(config, "step1_data_collection", dry_run)

