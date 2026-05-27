#!/usr/bin/env python3
"""Run the 4-agent workflow on a GCP VM with start/stop lifecycle control."""
from __future__ import annotations

import argparse
import subprocess
import time


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, text=True, check=check)


def instance_action(action: str, vm_name: str, project: str, zone: str) -> list[str]:
    return [
        "gcloud",
        "compute",
        "instances",
        action,
        vm_name,
        "--project",
        project,
        "--zone",
        zone,
    ]


def instance_status(vm_name: str, project: str, zone: str) -> str:
    cp = subprocess.run(
        [
            "gcloud",
            "compute",
            "instances",
            "describe",
            vm_name,
            "--project",
            project,
            "--zone",
            zone,
            "--format=value(status)",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return cp.stdout.strip() or f"unknown:{cp.returncode}"


def wait_for_ssh(vm_name: str, project: str, zone: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        cp = subprocess.run(
            [
                "gcloud",
                "compute",
                "ssh",
                vm_name,
                "--project",
                project,
                "--zone",
                zone,
                "--command",
                "hostname",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        if cp.returncode == 0:
            print(cp.stdout.strip(), flush=True)
            return
        time.sleep(5)
    raise TimeoutError(f"SSH did not become ready within {timeout_seconds}s")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disease", default="LUAD")
    parser.add_argument("--vm-name", default="sobi2026-gcs-api-test-vm")
    parser.add_argument("--project", default="project-b2fa1551-26f6-4422-8f0")
    parser.add_argument("--zone", default="asia-northeast3-a")
    parser.add_argument("--vm-repo", default="/home/skku_aws2_14/sobi2026/final-project_data-pipline-gcp-run")
    parser.add_argument("--run-heavy", action="store_true")
    parser.add_argument("--upload-gcs", action="store_true")
    parser.add_argument("--pull", action="store_true", help="Run git pull --ff-only in the VM repo before orchestration.")
    parser.add_argument(
        "--image-mode",
        choices=["reuse-existing", "smoke-1", "smoke-3", "full"],
        default="reuse-existing",
    )
    parser.add_argument("--allow-image-full", action="store_true")
    parser.add_argument("--ssh-timeout-seconds", type=int, default=180)
    parser.add_argument("--no-stop", action="store_true", help="Debug only: leave the VM running after the workflow.")
    args = parser.parse_args()

    started_here = instance_status(args.vm_name, args.project, args.zone) != "RUNNING"
    exit_code = 0
    try:
        if started_here:
            run(instance_action("start", args.vm_name, args.project, args.zone))
        else:
            print(f"VM already running: {args.vm_name}", flush=True)
        wait_for_ssh(args.vm_name, args.project, args.zone, args.ssh_timeout_seconds)

        workflow_parts = [
            '"${PDRP_PYTHON}" vm_scripts/coad_gcs_4agent_auto_loop.py',
            f"--disease {shell_quote(args.disease)}",
            "--vm-status-override RUNNING",
            f"--image-mode {shell_quote(args.image_mode)}",
        ]
        if args.run_heavy:
            workflow_parts.append("--run-heavy")
        if args.upload_gcs:
            workflow_parts.append("--upload-gcs")
        if args.allow_image_full:
            workflow_parts.append("--allow-image-full")
        pull_part = "&& git pull --ff-only " if args.pull else ""
        remote_command = (
            f"cd {shell_quote(args.vm_repo)} "
            '&& PDRP_PYTHON=python3 '
            '&& if [ -x .venv/bin/python ]; then PDRP_PYTHON=.venv/bin/python; fi '
            f"{pull_part}"
            f"&& {' '.join(workflow_parts)}"
        )
        cp = run(
            [
                "gcloud",
                "compute",
                "ssh",
                args.vm_name,
                "--project",
                args.project,
                "--zone",
                args.zone,
                "--command",
                remote_command,
            ],
            check=False,
        )
        exit_code = cp.returncode
    finally:
        if not args.no_stop:
            run(instance_action("stop", args.vm_name, args.project, args.zone), check=False)
            print(f"Final VM status: {instance_status(args.vm_name, args.project, args.zone)}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
