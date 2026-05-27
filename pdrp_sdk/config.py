from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkflowConfig:
    repo_root: Path
    disease: str = "COAD"
    runtime_root: Path = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
    local_step3_fallback: Path = Path("/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
    vm_name: str = "sobi2026-gcs-api-test-vm"
    vm_zone: str = "asia-northeast3-a"
    gcs_base: str = (
        "gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/"
        "20260408_new_pre_project_biso/migration-artifacts/20260527/"
        "basic_pipeline_step7_4agent_auto_loop"
    )

    @property
    def coad_root(self) -> Path:
        return self.repo_root / "Colon" / "0.Image_modal_COAD"

    @property
    def auto_loop_output_dir(self) -> Path:
        return self.coad_root / "step_gcs_basic_top15_4agent_auto_loop"

    @property
    def im4c_output_dir(self) -> Path:
        return self.coad_root / "step_gcs_basic_top15_im4c_remap"

    @property
    def evidence_output_dir(self) -> Path:
        return self.coad_root / "step_gcs_basic_top15_evidence_agent"

    @classmethod
    def from_repo_root(cls, repo_root: Path | str, **kwargs) -> "WorkflowConfig":
        return cls(repo_root=Path(repo_root).resolve(), **kwargs)
