from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiseaseProfile:
    disease: str = "COAD"
    disease_folder: str = "Colon"
    image_modal_dirname: str = "0.Image_modal_COAD"
    artifact_slug: str = "coad_gcs"
    runtime_root: Path | None = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
    local_step3_fallback: Path | None = Path("/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
    step_scripts: tuple[str, str, str] = (
        "vm_scripts/coad_gcs_basic_step1_preflight.sh",
        "vm_scripts/coad_gcs_basic_step2_preflight.sh",
        "vm_scripts/coad_gcs_basic_step3_preflight.sh",
    )
    im4c_remap_script: str = "vm_scripts/coad_gcs_basic_top15_im4c_remap.py"
    evidence_agent_script: str = "vm_scripts/coad_gcs_basic_top15_evidence_agent.py"
    im4c_output_dirname: str = "step_gcs_basic_top15_im4c_remap"
    evidence_output_dirname: str = "step_gcs_basic_top15_evidence_agent"
    auto_loop_output_dirname: str = "step_gcs_basic_top15_4agent_auto_loop"
    im4c_summary_filename: str = "coad_gcs_basic_top15_im4c_summary.json"
    im4c_drug_summary_filename: str = "coad_gcs_basic_top15_im4c_drug_summary.csv"
    evidence_verified_filename: str = "coad_gcs_basic_top15_evidence_verified_tiers.csv"
    evidence_report_filename: str = "coad_gcs_basic_top15_evidence_report.md"
    evidence_summary_filename: str = "coad_gcs_basic_top15_evidence_summary.json"
    auto_loop_summary_filename: str = "coad_gcs_4agent_auto_loop_summary.json"
    auto_loop_report_filename: str = "coad_gcs_4agent_auto_loop_report.md"

    @property
    def image_modal_required_files(self) -> dict[str, Path]:
        root = Path(self.disease_folder) / self.image_modal_dirname
        return {
            "im2_embedding_qc": root / "step_im2" / "embedding_qc.json",
            "im3_patient_clusters": root / "step_im3" / "patient_clusters.csv",
            "im4b_cluster_profiles": root / "step_im4b" / f"{self.disease.lower()}_cluster_pathway_profiles.csv",
        }


DISEASE_PROFILES: dict[str, DiseaseProfile] = {
    "COAD": DiseaseProfile(),
}


@dataclass(frozen=True)
class WorkflowConfig:
    repo_root: Path
    disease: str = "COAD"
    profile: DiseaseProfile | None = None
    runtime_root: Path | None = None
    local_step3_fallback: Path | None = None
    vm_name: str = "sobi2026-gcs-api-test-vm"
    vm_zone: str = "asia-northeast3-a"
    gcs_base: str = (
        "gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/"
        "20260408_new_pre_project_biso/migration-artifacts/20260527/"
        "basic_pipeline_step8_internal_sdk"
    )

    @property
    def disease_profile(self) -> DiseaseProfile:
        if self.profile is not None:
            return self.profile
        try:
            return DISEASE_PROFILES[self.disease.upper()]
        except KeyError as exc:
            supported = ", ".join(sorted(DISEASE_PROFILES))
            raise ValueError(f"No disease profile registered for {self.disease!r}. Supported profiles: {supported}") from exc

    @property
    def effective_runtime_root(self) -> Path:
        value = self.runtime_root or self.disease_profile.runtime_root
        if value is None:
            raise ValueError(f"No runtime_root configured for {self.disease}")
        return Path(value)

    @property
    def effective_local_step3_fallback(self) -> Path:
        value = self.local_step3_fallback or self.disease_profile.local_step3_fallback
        if value is None:
            raise ValueError(f"No local_step3_fallback configured for {self.disease}")
        return Path(value)

    @property
    def image_modal_root(self) -> Path:
        profile = self.disease_profile
        return self.repo_root / profile.disease_folder / profile.image_modal_dirname

    @property
    def auto_loop_output_dir(self) -> Path:
        return self.image_modal_root / self.disease_profile.auto_loop_output_dirname

    @property
    def im4c_output_dir(self) -> Path:
        return self.image_modal_root / self.disease_profile.im4c_output_dirname

    @property
    def evidence_output_dir(self) -> Path:
        return self.image_modal_root / self.disease_profile.evidence_output_dirname

    @classmethod
    def from_repo_root(cls, repo_root: Path | str, **kwargs) -> "WorkflowConfig":
        return cls(repo_root=Path(repo_root).resolve(), **kwargs)
