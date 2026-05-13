from __future__ import annotations

from pathlib import Path
from typing import Any

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor


def submit_basic_pipeline_job(disease_name: str, config: dict[str, Any], wait: bool = False) -> str:
    """Submit the existing Agentic AI basic/full pipeline as one SageMaker Processing job.

    The Claude config generation remains inside run_disease_pipeline.py. This wrapper only
    provides the container, env vars, input/output mounts, and SageMaker job metadata.
    """
    source_dir = str(Path(config.get("source_dir", "/Users/skku_aws2_14/pipeline")).resolve())
    s3_output = config["s3_output_path"].rstrip("/")
    disease_slug = config.get("disease_slug") or _slug(disease_name)

    processor = ScriptProcessor(
        role=config["sagemaker_role"],
        image_uri=config["pipeline_image_uri"],
        instance_count=int(config.get("basic_instance_count", 1)),
        instance_type=config.get("basic_instance_type", "ml.m5.4xlarge"),
        command=["python3"],
        base_job_name=f"basic-pipeline-{disease_slug}",
        env={
            "ANTHROPIC_SECRET_ID": config.get("anthropic_secret_id", config.get("anthropic_secret_name", "drug-repurposing/anthropic")),
            "DISEASE_NAME": disease_name,
            "PIPELINE_MODE": config.get("mode", "full"),
            "SM_PROCESSING_INPUT": "true",
            "S3_OUTPUT": s3_output,
            "RANDOM_SEED": str(config.get("random_seed", 42)),
        },
    )

    inputs = []
    if config.get("s3_data_path"):
        inputs.append(
            ProcessingInput(
                source=config["s3_data_path"],
                destination="/opt/ml/processing/input/data",
            )
        )

    processor.run(
        code="run_disease_pipeline.py",
        source_dir=source_dir,
        inputs=inputs,
        outputs=[
            ProcessingOutput(
                source="/opt/ml/processing/output",
                destination=f"{s3_output}/{disease_slug}/basic_pipeline/",
            )
        ],
        arguments=["--disease", disease_name, "--mode", config.get("mode", "full")],
        wait=wait,
    )
    return processor.latest_processing_job.name


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "disease"
