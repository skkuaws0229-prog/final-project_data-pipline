from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .agents import EvidenceReportAgent, ImageModalAgent, PipelineAgent, PreflightQAAgent
from . import compute
from .config import WorkflowConfig
from .db import db_status
from .storage import upload_auto_loop_outputs
from .utils import now_iso, write_json


class FourAgentWorkflow:
    """Small internal SDK wrapper around a disease 4-agent loop."""

    def __init__(self, config: WorkflowConfig):
        self.config = config

    def run(
        self,
        *,
        run_heavy: bool = False,
        upload_gcs: bool = False,
        vm_status_override: str | None = None,
        manage_vm: bool = False,
        image_mode: str = "reuse-existing",
        allow_image_full: bool = False,
    ) -> dict[str, Any]:
        output_dir = self.config.auto_loop_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        started = now_iso()
        results = []
        vm_lifecycle: list[dict[str, Any]] = []
        status = "failed"

        try:
            if manage_vm:
                vm_lifecycle.append(compute.start_vm(self.config))
                vm_status_override = "RUNNING"

            preflight = PreflightQAAgent().run(self.config, vm_status_override)
            results.append(preflight)
            if preflight.status != "completed":
                upload_gcs = False
                return self._finalize(
                    started,
                    results,
                    status,
                    upload_gcs=upload_gcs,
                    vm_lifecycle=vm_lifecycle,
                    manage_vm=manage_vm,
                    image_mode=image_mode,
                )

            pipeline = PipelineAgent().run(self.config, run_heavy)
            results.append(pipeline)
            if pipeline.status != "completed":
                upload_gcs = False
                return self._finalize(
                    started,
                    results,
                    status,
                    upload_gcs=upload_gcs,
                    vm_lifecycle=vm_lifecycle,
                    manage_vm=manage_vm,
                    image_mode=image_mode,
                )

            image = ImageModalAgent().run(self.config, image_mode=image_mode, allow_image_full=allow_image_full)
            results.append(image)
            if image.status != "completed":
                upload_gcs = False
                return self._finalize(
                    started,
                    results,
                    status,
                    upload_gcs=upload_gcs,
                    vm_lifecycle=vm_lifecycle,
                    manage_vm=manage_vm,
                    image_mode=image_mode,
                )

            vm_status = str(preflight.checks.get("vm_status", "unknown"))
            evidence = EvidenceReportAgent().run(self.config, vm_status)
            results.append(evidence)
            if evidence.status != "completed":
                upload_gcs = False
                return self._finalize(
                    started,
                    results,
                    status,
                    upload_gcs=upload_gcs,
                    vm_lifecycle=vm_lifecycle,
                    manage_vm=manage_vm,
                    image_mode=image_mode,
                )

            status = "completed"
            return self._finalize(
                started,
                results,
                status,
                upload_gcs=upload_gcs,
                vm_lifecycle=vm_lifecycle,
                manage_vm=manage_vm,
                image_mode=image_mode,
            )
        except Exception:
            if manage_vm:
                vm_lifecycle.append(compute.stop_vm(self.config))
            raise

    def _finalize(
        self,
        started: str,
        results: list[Any],
        status: str,
        *,
        upload_gcs: bool,
        vm_lifecycle: list[dict[str, Any]],
        manage_vm: bool,
        image_mode: str,
    ) -> dict[str, Any]:
        if manage_vm:
            vm_lifecycle.append(compute.stop_vm(self.config))
        return self._write_master(
            started,
            results,
            status,
            upload_gcs=upload_gcs,
            vm_lifecycle=vm_lifecycle,
            image_mode=image_mode,
        )

    def _write_master(
        self,
        started: str,
        results: list[Any],
        status: str,
        *,
        upload_gcs: bool,
        vm_lifecycle: list[dict[str, Any]] | None = None,
        image_mode: str = "reuse-existing",
    ) -> dict[str, Any]:
        output_dir = self.config.auto_loop_output_dir
        payload = {
            "workflow": f"{self.config.disease.lower()}_gcs_4agent_auto_loop",
            "disease": self.config.disease.upper(),
            "sdk": "pdrp_sdk.v0.2",
            "status": status,
            "started_at": started,
            "completed_at": now_iso(),
            "agents": [asdict(result) for result in results],
            "db_status": db_status(),
            "vm_lifecycle": vm_lifecycle or [],
            "image_modal_mode": image_mode,
        }
        if upload_gcs:
            payload["gcs_upload"] = upload_auto_loop_outputs(self.config, output_dir)
        profile = self.config.disease_profile
        write_json(output_dir / profile.auto_loop_summary_filename, payload)
        self._write_report(output_dir / profile.auto_loop_report_filename, payload)
        return payload

    def _write_report(self, path, payload: dict[str, Any]) -> None:
        lines = [
            f"# {payload['disease']} GCS 4-Agent Auto Loop",
            "",
            f"- SDK: {payload['sdk']}",
            f"- Status: {payload['status']}",
            f"- Started: {payload['started_at']}",
            f"- Completed: {payload['completed_at']}",
            f"- Image mode: {payload['image_modal_mode']}",
            "",
            "## VM Lifecycle",
            "",
        ]
        if payload.get("vm_lifecycle"):
            for event in payload["vm_lifecycle"]:
                lines.append(
                    f"- {event.get('action')}: {event.get('status')} "
                    f"({event.get('vm_status_after', 'unknown')})"
                )
        else:
            lines.append("- not managed by this run")
        lines.extend(
            [
                "",
                "## Agents",
                "",
            ]
        )
        for agent in payload["agents"]:
            lines.append(f"### {agent['agent']}")
            lines.append("")
            lines.append(f"- status: {agent['status']}")
            for action in agent.get("actions", []):
                lines.append(f"- action: {action}")
            for warning in agent.get("warnings", []):
                lines.append(f"- warning: {warning}")
            for key, value in agent.get("outputs", {}).items():
                lines.append(f"- output {key}: `{value}`")
            lines.append("")
        lines.extend(
            [
                "## DB Status",
                "",
                "- loaded_to_postgres: false",
                "- note: DB loading has not been executed yet. Add a separate DB Load Agent when the service schema target is finalized.",
            ]
        )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
