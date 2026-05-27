#!/usr/bin/env python3
"""COAD GCS 4-agent automatic loop.

Agents:
1. Preflight/QA Agent
2. Pipeline Agent
3. Image-Modal Agent
4. Evidence/Report Agent

Default mode is safe resume mode: completed outputs are verified and skipped.
Use --run-heavy only when Step1/Step2/Step3 should actually be rerun.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
COAD_ROOT = REPO_ROOT / "Colon" / "0.Image_modal_COAD"
RUNTIME_ROOT_DEFAULT = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
LOCAL_STEP3_FALLBACK = Path("/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
GCS_BASE = (
    "gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/"
    "20260408_new_pre_project_biso/migration-artifacts/20260527/"
    "basic_pipeline_step7_4agent_auto_loop"
)


@dataclass
class AgentResult:
    agent: str
    status: str
    started_at: str
    completed_at: str
    checks: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_cmd(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True, check=check)


def file_status(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def resolve_admet_top15(runtime_root: Path) -> Path:
    target = runtime_root / "outputs" / "final_selection" / "admet_filtered_top15.csv"
    if target.exists():
        return target
    if LOCAL_STEP3_FALLBACK.exists():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LOCAL_STEP3_FALLBACK, target)
            return target
        except OSError:
            return LOCAL_STEP3_FALLBACK
    raise FileNotFoundError(f"Missing ADMET top15: {target} and {LOCAL_STEP3_FALLBACK}")


class PreflightQAAgent:
    name = "preflight_qa_agent"

    def run(self, runtime_root: Path, vm_status_override: str | None = None) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        warnings: list[str] = []

        checks["repo_root"] = str(REPO_ROOT)
        checks["git_repo"] = (REPO_ROOT / ".git").exists()
        checks["gcloud_available"] = shutil.which("gcloud") is not None

        vm_status = vm_status_override or "unknown"
        if vm_status_override:
            checks["vm_status_source"] = "override"
        elif checks["gcloud_available"]:
            checks["vm_status_source"] = "gcloud"
            try:
                cp = run_cmd(
                    [
                        "gcloud",
                        "compute",
                        "instances",
                        "describe",
                        "sobi2026-gcs-api-test-vm",
                        "--zone",
                        "asia-northeast3-a",
                        "--format=value(status)",
                    ],
                    check=False,
                )
                vm_status = cp.stdout.strip() or "unknown"
            except Exception as exc:  # pragma: no cover - environment dependent
                vm_status = f"check_failed:{exc}"
        checks["vm_status"] = vm_status
        if vm_status != "TERMINATED":
            warnings.append("VM is not confirmed TERMINATED; verify cost controls before heavy reruns.")

        required = {
            "im2_embedding_qc": COAD_ROOT / "step_im2" / "embedding_qc.json",
            "im3_patient_clusters": COAD_ROOT / "step_im3" / "patient_clusters.csv",
            "im4b_cluster_profiles": COAD_ROOT / "step_im4b" / "coad_cluster_pathway_profiles.csv",
            "im4c_remap_script": REPO_ROOT / "vm_scripts" / "coad_gcs_basic_top15_im4c_remap.py",
            "evidence_agent_script": REPO_ROOT / "vm_scripts" / "coad_gcs_basic_top15_evidence_agent.py",
        }
        checks["required_files"] = {key: file_status(path) for key, path in required.items()}
        missing = [key for key, meta in checks["required_files"].items() if not meta["exists"]]
        if missing:
            return AgentResult(self.name, "failed", started, now_iso(), checks, warnings=warnings + [f"Missing files: {missing}"])

        try:
            admet = resolve_admet_top15(runtime_root)
            checks["admet_top15"] = file_status(admet)
            df = pd.read_csv(admet)
            name_key = df["drug_name"].fillna("").astype(str).str.lower().str.strip()
            checks["top15_rows"] = int(len(df))
            checks["top15_unique_names"] = int(name_key.nunique())
            checks["top15_duplicate_name_rows"] = int(name_key.duplicated().sum())
            if len(df) != 15 or checks["top15_duplicate_name_rows"]:
                return AgentResult(self.name, "failed", started, now_iso(), checks, warnings=warnings + ["Top15 uniqueness check failed."])
        except Exception as exc:
            return AgentResult(self.name, "failed", started, now_iso(), checks, warnings=warnings + [str(exc)])

        return AgentResult(self.name, "completed", started, now_iso(), checks, actions=["verified_inputs_and_cost_state"], warnings=warnings)


class PipelineAgent:
    name = "pipeline_agent"

    def run(self, runtime_root: Path, run_heavy: bool) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        final_selection = runtime_root / "outputs" / "final_selection"
        expected = {
            "selected_top_n": final_selection / "selected_drugs_top_n.csv",
            "admet_candidate_gate": final_selection / "admet_candidate_gate.csv",
            "admet_top15": final_selection / "admet_filtered_top15.csv",
            "admet_summary": final_selection / "admet_summary.json",
        }
        checks["expected_outputs_before"] = {key: file_status(path) for key, path in expected.items()}

        if not run_heavy:
            resolve_admet_top15(runtime_root)
            actions.append("resume_mode_verified_existing_admet_top15")
        else:
            for script in [
                "vm_scripts/coad_gcs_basic_step1_preflight.sh",
                "vm_scripts/coad_gcs_basic_step2_preflight.sh",
                "vm_scripts/coad_gcs_basic_step3_preflight.sh",
            ]:
                cp = run_cmd(["bash", script], check=False)
                actions.append(f"ran {script} exit={cp.returncode}")
                if cp.returncode != 0:
                    warnings.append(cp.stderr[-1000:])
                    return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=warnings)

        checks["expected_outputs_after"] = {key: file_status(path) for key, path in expected.items()}
        admet_top15 = resolve_admet_top15(runtime_root)
        if not admet_top15.exists():
            return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=warnings + ["ADMET top15 missing after Pipeline Agent."])
        df = pd.read_csv(admet_top15)
        checks["admet_top15_rows"] = int(len(df))
        checks["admet_top15_drugs"] = df["drug_name"].tolist()
        return AgentResult(self.name, "completed", started, now_iso(), checks, actions, outputs={"admet_top15": str(admet_top15)}, warnings=warnings)


class ImageModalAgent:
    name = "image_modal_agent"

    def run(self, runtime_root: Path) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        admet_top15 = resolve_admet_top15(runtime_root)
        script = REPO_ROOT / "vm_scripts" / "coad_gcs_basic_top15_im4c_remap.py"
        out_dir = COAD_ROOT / "step_gcs_basic_top15_im4c_remap"
        cp = run_cmd(
            [
                sys.executable,
                str(script),
                "--admet-top15",
                str(admet_top15),
                "--output-dir",
                str(out_dir),
            ],
            check=False,
        )
        actions.append(f"ran image remap exit={cp.returncode}")
        if cp.returncode != 0:
            return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=[cp.stderr[-1000:]])

        summary_path = out_dir / "coad_gcs_basic_top15_im4c_summary.json"
        drug_summary = out_dir / "coad_gcs_basic_top15_im4c_drug_summary.csv"
        checks["summary"] = file_status(summary_path)
        checks["drug_summary"] = file_status(drug_summary)
        if drug_summary.exists():
            df = pd.read_csv(drug_summary)
            checks["drug_summary_rows"] = int(len(df))
            checks["tier_counts"] = df["crc_4tier"].value_counts().sort_index().to_dict()
        return AgentResult(
            self.name,
            "completed",
            started,
            now_iso(),
            checks,
            actions,
            outputs={"im4c_drug_summary": str(drug_summary), "im4c_summary": str(summary_path)},
            warnings=warnings,
        )


class EvidenceReportAgent:
    name = "evidence_report_agent"

    def run(self, vm_status: str) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        script = REPO_ROOT / "vm_scripts" / "coad_gcs_basic_top15_evidence_agent.py"
        out_dir = COAD_ROOT / "step_gcs_basic_top15_evidence_agent"
        cp = run_cmd(
            [
                sys.executable,
                str(script),
                "--vm-status-at-start",
                vm_status,
                "--output-dir",
                str(out_dir),
            ],
            check=False,
        )
        actions.append(f"ran evidence agent exit={cp.returncode}")
        if cp.returncode != 0:
            return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=[cp.stderr[-1000:]])

        verified = out_dir / "coad_gcs_basic_top15_evidence_verified_tiers.csv"
        report = out_dir / "coad_gcs_basic_top15_evidence_report.md"
        summary = out_dir / "coad_gcs_basic_top15_evidence_summary.json"
        checks["verified_tiers"] = file_status(verified)
        checks["report"] = file_status(report)
        checks["summary"] = file_status(summary)
        if verified.exists():
            df = pd.read_csv(verified)
            checks["final_tier_counts"] = df["evidence_agent_final_tier"].value_counts().sort_index().to_dict()
            checks["tier_changes"] = df[df["tier_change"] != "unchanged"][["drug_name", "tier_change"]].to_dict("records")
        return AgentResult(
            self.name,
            "completed",
            started,
            now_iso(),
            checks,
            actions,
            outputs={"verified_tiers": str(verified), "report": str(report), "summary": str(summary)},
        )


def upload_outputs(output_dir: Path) -> dict[str, Any]:
    if shutil.which("gcloud") is None:
        return {"status": "skipped", "reason": "gcloud_not_available"}
    targets = [
        (output_dir, f"{GCS_BASE}/results/{output_dir.name}/"),
        (REPO_ROOT / "vm_scripts" / "coad_gcs_4agent_auto_loop.py", f"{GCS_BASE}/code/"),
    ]
    uploaded: list[str] = []
    for src, dst in targets:
        cmd = ["gcloud", "storage", "cp"]
        if src.is_dir():
            cmd.append("--recursive")
        cmd.extend([str(src), dst])
        cp = run_cmd(cmd, check=False)
        uploaded.append(f"{src} -> {dst} exit={cp.returncode}")
        if cp.returncode != 0:
            return {"status": "failed", "uploaded": uploaded, "stderr": cp.stderr[-1000:]}
    return {"status": "completed", "uploaded": uploaded}


def run_loop(args: argparse.Namespace) -> dict[str, Any]:
    runtime_root = Path(args.runtime_root)
    output_dir = COAD_ROOT / "step_gcs_basic_top15_4agent_auto_loop"
    output_dir.mkdir(parents=True, exist_ok=True)

    master_started = now_iso()
    results: list[AgentResult] = []

    preflight = PreflightQAAgent().run(runtime_root, args.vm_status_override)
    results.append(preflight)
    if preflight.status != "completed":
        return write_master(output_dir, master_started, results, "failed")

    pipeline = PipelineAgent().run(runtime_root, args.run_heavy)
    results.append(pipeline)
    if pipeline.status != "completed":
        return write_master(output_dir, master_started, results, "failed")

    image = ImageModalAgent().run(runtime_root)
    results.append(image)
    if image.status != "completed":
        return write_master(output_dir, master_started, results, "failed")

    vm_status = str(preflight.checks.get("vm_status", "unknown"))
    evidence = EvidenceReportAgent().run(vm_status)
    results.append(evidence)
    if evidence.status != "completed":
        return write_master(output_dir, master_started, results, "failed")

    return write_master(output_dir, master_started, results, "completed", upload=args.upload_gcs)


def write_master(
    output_dir: Path,
    master_started: str,
    results: list[AgentResult],
    status: str,
    *,
    upload: bool = False,
) -> dict[str, Any]:
    payload = {
        "workflow": "coad_gcs_4agent_auto_loop",
        "status": status,
        "started_at": master_started,
        "completed_at": now_iso(),
        "agents": [result.__dict__ for result in results],
        "db_status": {
            "loaded_to_postgres": False,
            "note": "This loop writes CSV/JSON/Markdown artifacts only. DB loading is intentionally left as a separate db_load agent/stage.",
        },
    }
    if upload:
        payload["gcs_upload"] = upload_outputs(output_dir)
    write_json(output_dir / "coad_gcs_4agent_auto_loop_summary.json", payload)
    write_report(output_dir / "coad_gcs_4agent_auto_loop_report.md", payload)
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# COAD GCS 4-Agent Auto Loop",
        "",
        f"- Status: {payload['status']}",
        f"- Started: {payload['started_at']}",
        f"- Completed: {payload['completed_at']}",
        "",
        "## Agents",
        "",
    ]
    for agent in payload["agents"]:
        lines.append(f"### {agent['agent']}")
        lines.append("")
        lines.append(f"- status: {agent['status']}")
        if agent.get("actions"):
            for action in agent["actions"]:
                lines.append(f"- action: {action}")
        if agent.get("warnings"):
            for warning in agent["warnings"]:
                lines.append(f"- warning: {warning}")
        if agent.get("outputs"):
            for key, value in agent["outputs"].items():
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", default=str(RUNTIME_ROOT_DEFAULT))
    parser.add_argument("--run-heavy", action="store_true", help="Actually run Step1/Step2/Step3 scripts instead of resume verification.")
    parser.add_argument("--upload-gcs", action="store_true", help="Upload auto-loop report/code to GCS after completion.")
    parser.add_argument("--vm-status-override", choices=["TERMINATED", "RUNNING", "STOPPING", "UNKNOWN"], help="Use a known VM status when local gcloud checks are sandbox-limited.")
    args = parser.parse_args()
    print(json.dumps(run_loop(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
