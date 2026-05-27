from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from . import compute
from .config import WorkflowConfig
from .utils import file_status, now_iso, run_cmd


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


def resolve_admet_top15(config: WorkflowConfig) -> Path:
    target = config.runtime_root / "outputs" / "final_selection" / "admet_filtered_top15.csv"
    if target.exists():
        return target
    if config.local_step3_fallback.exists():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config.local_step3_fallback, target)
            return target
        except OSError:
            return config.local_step3_fallback
    raise FileNotFoundError(f"Missing ADMET top15: {target} and {config.local_step3_fallback}")


class PreflightQAAgent:
    name = "preflight_qa_agent"

    def run(self, config: WorkflowConfig, vm_status_override: str | None = None) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        warnings: list[str] = []

        checks["repo_root"] = str(config.repo_root)
        checks["git_repo"] = (config.repo_root / ".git").exists()
        checks["gcloud_available"] = compute.gcloud_available()
        checks["vm_status_source"] = "override" if vm_status_override else "gcloud"
        vm_status = vm_status_override or compute.get_vm_status(config)
        checks["vm_status"] = vm_status
        if vm_status != "TERMINATED":
            warnings.append("VM is not confirmed TERMINATED; verify cost controls before heavy reruns.")

        required = {
            "im2_embedding_qc": config.coad_root / "step_im2" / "embedding_qc.json",
            "im3_patient_clusters": config.coad_root / "step_im3" / "patient_clusters.csv",
            "im4b_cluster_profiles": config.coad_root / "step_im4b" / "coad_cluster_pathway_profiles.csv",
            "im4c_remap_script": config.repo_root / "vm_scripts" / "coad_gcs_basic_top15_im4c_remap.py",
            "evidence_agent_script": config.repo_root / "vm_scripts" / "coad_gcs_basic_top15_evidence_agent.py",
        }
        checks["required_files"] = {key: file_status(path) for key, path in required.items()}
        missing = [key for key, meta in checks["required_files"].items() if not meta["exists"]]
        if missing:
            return AgentResult(self.name, "failed", started, now_iso(), checks, warnings=warnings + [f"Missing files: {missing}"])

        try:
            admet = resolve_admet_top15(config)
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

    def run(self, config: WorkflowConfig, run_heavy: bool) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        warnings: list[str] = []

        final_selection = config.runtime_root / "outputs" / "final_selection"
        expected = {
            "selected_top_n": final_selection / "selected_drugs_top_n.csv",
            "admet_candidate_gate": final_selection / "admet_candidate_gate.csv",
            "admet_top15": final_selection / "admet_filtered_top15.csv",
            "admet_summary": final_selection / "admet_summary.json",
        }
        checks["expected_outputs_before"] = {key: file_status(path) for key, path in expected.items()}

        if not run_heavy:
            resolve_admet_top15(config)
            actions.append("resume_mode_verified_existing_admet_top15")
        else:
            for script in [
                "vm_scripts/coad_gcs_basic_step1_preflight.sh",
                "vm_scripts/coad_gcs_basic_step2_preflight.sh",
                "vm_scripts/coad_gcs_basic_step3_preflight.sh",
            ]:
                cp = run_cmd(["bash", script], cwd=config.repo_root, check=False)
                actions.append(f"ran {script} exit={cp.returncode}")
                if cp.returncode != 0:
                    warnings.append(cp.stderr[-1000:])
                    return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=warnings)

        checks["expected_outputs_after"] = {key: file_status(path) for key, path in expected.items()}
        admet_top15 = resolve_admet_top15(config)
        df = pd.read_csv(admet_top15)
        checks["admet_top15_rows"] = int(len(df))
        checks["admet_top15_drugs"] = df["drug_name"].tolist()
        return AgentResult(self.name, "completed", started, now_iso(), checks, actions, outputs={"admet_top15": str(admet_top15)}, warnings=warnings)


class ImageModalAgent:
    name = "image_modal_agent"

    def run(self, config: WorkflowConfig) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        admet_top15 = resolve_admet_top15(config)
        script = config.repo_root / "vm_scripts" / "coad_gcs_basic_top15_im4c_remap.py"
        cp = run_cmd(
            [
                sys.executable,
                str(script),
                "--admet-top15",
                str(admet_top15),
                "--output-dir",
                str(config.im4c_output_dir),
            ],
            cwd=config.repo_root,
            check=False,
        )
        actions.append(f"ran image remap exit={cp.returncode}")
        if cp.returncode != 0:
            return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=[cp.stderr[-1000:]])

        summary_path = config.im4c_output_dir / "coad_gcs_basic_top15_im4c_summary.json"
        drug_summary = config.im4c_output_dir / "coad_gcs_basic_top15_im4c_drug_summary.csv"
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
        )


class EvidenceReportAgent:
    name = "evidence_report_agent"

    def run(self, config: WorkflowConfig, vm_status: str) -> AgentResult:
        started = now_iso()
        checks: dict[str, Any] = {}
        actions: list[str] = []
        script = config.repo_root / "vm_scripts" / "coad_gcs_basic_top15_evidence_agent.py"
        cp = run_cmd(
            [
                sys.executable,
                str(script),
                "--vm-status-at-start",
                vm_status,
                "--output-dir",
                str(config.evidence_output_dir),
            ],
            cwd=config.repo_root,
            check=False,
        )
        actions.append(f"ran evidence agent exit={cp.returncode}")
        if cp.returncode != 0:
            return AgentResult(self.name, "failed", started, now_iso(), checks, actions, warnings=[cp.stderr[-1000:]])

        verified = config.evidence_output_dir / "coad_gcs_basic_top15_evidence_verified_tiers.csv"
        report = config.evidence_output_dir / "coad_gcs_basic_top15_evidence_report.md"
        summary = config.evidence_output_dir / "coad_gcs_basic_top15_evidence_summary.json"
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
