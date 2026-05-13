from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.config import settings
from app.pipeline_db import insert_pipeline_artifact, insert_pipeline_event, update_pipeline_run


class PipelineOrchestrator(ABC):
    @abstractmethod
    def submit_run(self, run: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, run_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def cancel_run(self, run_id: str) -> dict:
        raise NotImplementedError


class MockPipelineOrchestrator(PipelineOrchestrator):
    def submit_run(self, run: dict) -> dict:
        run_id = run["run_id"]
        insert_pipeline_event(run_id, "info", "preflight", "mock 권한 사전검사 통과", {"execution_backend": "mock"})
        updated = update_pipeline_run(run_id, status="running", current_step="mock_pipeline", started_at=datetime.now(UTC))
        insert_pipeline_event(run_id, "info", "mock_pipeline", "mock pipeline 실행 상태로 전환")
        insert_pipeline_artifact(
            run_id,
            "s3_prefix",
            "mock_pipeline",
            f"{run['disease_slug']}_mock_output_prefix",
            run["s3_output_prefix"],
        )
        insert_pipeline_artifact(
            run_id,
            "validation",
            "validation",
            f"{run['disease_slug']}_mock_validation_report.md",
            f"{run['s3_output_prefix']}validation/{run['disease_slug']}_mock_validation_report.md",
        )
        return updated or run

    def get_status(self, run_id: str) -> dict:
        return {"run_id": run_id, "execution_backend": "mock"}

    def cancel_run(self, run_id: str) -> dict:
        insert_pipeline_event(run_id, "warning", "cancel", "mock run cancelled by API request")
        return update_pipeline_run(run_id, status="cancelled", current_step="cancelled", ended_at=datetime.now(UTC)) or {}


class LocalAgentPipelineOrchestrator(PipelineOrchestrator):
    def submit_run(self, run: dict) -> dict:
        if not settings.pipeline_enable_local_agent:
            insert_pipeline_event(run["run_id"], "warning", "guardrail", "local_agent backend is disabled by feature flag")
            return update_pipeline_run(run["run_id"], status="blocked", current_step="guardrail", error_message="local_agent backend disabled") or run
        raise NotImplementedError("local_agent execution is intentionally not implemented in this phase")

    def get_status(self, run_id: str) -> dict:
        return {"run_id": run_id, "execution_backend": "local_agent", "enabled": settings.pipeline_enable_local_agent}

    def cancel_run(self, run_id: str) -> dict:
        return update_pipeline_run(run_id, status="cancelled", current_step="cancelled", ended_at=datetime.now(UTC)) or {}


class AwsStepFunctionsOrchestrator(PipelineOrchestrator):
    def submit_run(self, run: dict) -> dict:
        if not settings.pipeline_enable_aws_stepfunctions:
            insert_pipeline_event(run["run_id"], "warning", "guardrail", "aws_stepfunctions backend is disabled by feature flag")
            return update_pipeline_run(run["run_id"], status="blocked", current_step="guardrail", error_message="aws_stepfunctions backend disabled") or run
        raise NotImplementedError("aws_stepfunctions execution is intentionally not implemented in this phase")

    def get_status(self, run_id: str) -> dict:
        return {"run_id": run_id, "execution_backend": "aws_stepfunctions", "enabled": settings.pipeline_enable_aws_stepfunctions}

    def cancel_run(self, run_id: str) -> dict:
        return update_pipeline_run(run_id, status="cancelled", current_step="cancelled", ended_at=datetime.now(UTC)) or {}


def get_orchestrator(execution_backend: str) -> PipelineOrchestrator:
    if execution_backend == "mock":
        return MockPipelineOrchestrator()
    if execution_backend == "local_agent":
        return LocalAgentPipelineOrchestrator()
    if execution_backend == "aws_stepfunctions":
        return AwsStepFunctionsOrchestrator()
    raise ValueError(f"Unsupported execution_backend: {execution_backend}")

