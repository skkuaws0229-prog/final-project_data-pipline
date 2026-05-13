from __future__ import annotations

from pathlib import Path
from typing import Any

from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor


def submit_im_cpu_job(disease_name: str, config: dict[str, Any], embedding_s3_path: str, wait: bool = False) -> str:
    """Submit IM3~IM5 CPU-only image-modal postprocessing as SageMaker Processing."""
    source_dir = str(Path(config.get("source_dir", "/Users/skku_aws2_14/pipeline")).resolve())
    s3_output = config["s3_output_path"].rstrip("/")
    disease_slug = config.get("disease_slug") or _slug(disease_name)

    processor = ScriptProcessor(
        role=config["sagemaker_role"],
        image_uri=config["pipeline_image_uri"],
        instance_count=int(config.get("im_cpu_instance_count", 1)),
        instance_type=config.get("im_cpu_instance_type", "ml.m5.xlarge"),
        command=["python3"],
        base_job_name=f"im-cpu-{disease_slug}",
        env={
            "DISEASE_NAME": disease_name,
            "DISEASE_SLUG": disease_slug,
            "SM_PROCESSING_INPUT": "true",
            "RANDOM_SEED": str(config.get("random_seed", 42)),
        },
    )

    processor.run(
        code="sagemaker/run_image_modal_cpu.py",
        source_dir=source_dir,
        inputs=[
            ProcessingInput(
                source=embedding_s3_path,
                destination="/opt/ml/processing/input/embeddings",
            ),
            ProcessingInput(
                source=f"{s3_output}/{disease_slug}/basic_pipeline/",
                destination="/opt/ml/processing/input/basic_results",
            ),
        ],
        outputs=[
            ProcessingOutput(
                source="/opt/ml/processing/output",
                destination=f"{s3_output}/{disease_slug}/image_modal/",
            )
        ],
        wait=wait,
    )
    return processor.latest_processing_job.name


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "disease"
