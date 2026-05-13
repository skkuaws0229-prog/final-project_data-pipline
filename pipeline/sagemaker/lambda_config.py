from __future__ import annotations

import os
import re

import boto3


def handler(event, context):
    disease_name = event["disease_name"]
    region = os.environ.get("AWS_REGION", "ap-northeast-2")
    account = os.environ.get("AWS_ACCOUNT_ID") or boto3.client("sts").get_caller_identity()["Account"]
    secret_id = os.environ.get("ANTHROPIC_SECRET_ID", "drug-repurposing/anthropic")
    disease_slug = event.get("disease_slug") or _slug(disease_name)

    return {
        "disease_name": disease_name,
        "disease_slug": disease_slug,
        "anthropic_secret_id": secret_id,
        "sagemaker_role": os.environ.get(
            "SAGEMAKER_ROLE_ARN",
            f"arn:aws:iam::{account}:role/SKKU-SageMaker-Processing-Execution-Role",
        ),
        "pipeline_image_uri": os.environ.get(
            "PIPELINE_IMAGE_URI",
            f"{account}.dkr.ecr.{region}.amazonaws.com/drug-repurposing-basic:latest",
        ),
        "im_gpu_image_uri": os.environ.get(
            "IM_GPU_IMAGE_URI",
            f"{account}.dkr.ecr.{region}.amazonaws.com/drug-repurposing-im-gpu:latest",
        ),
        "s3_data_path": os.environ.get("S3_DATA_PATH", "s3://say2-4team/"),
        "s3_output_path": os.environ.get("S3_OUTPUT_PATH", "s3://say2-4team/pipeline_results"),
        "random_seed": 42,
        "image_modal_policy": {
            "wsi_default_limit": int(os.environ.get("WSI_DEFAULT_LIMIT", "100")),
            "wsi_max_limit": int(os.environ.get("WSI_MAX_LIMIT", "200")),
            "wsi_smoke_count": int(os.environ.get("WSI_SMOKE_COUNT", "1")),
            "wsi_parallel_downloads": int(os.environ.get("WSI_PARALLEL_DOWNLOADS", "4")),
            "embedding_parallel_parts": int(os.environ.get("EMBEDDING_PARALLEL_PARTS", "4")),
            "launch_order": [
                "permission_preflight",
                "data_preflight",
                "wsi_smoke_1",
                "wsi_main_4_parallel_downloads",
                "tile_preprocessing",
                "embedding_4_parallel_parts",
                "im_cpu_postprocessing",
            ],
        },
    }


def _slug(value: str) -> str:
    known = {
        "난소암": "ov",
        "ov": "ov",
        "ovarian cancer": "ov",
        "위암": "stad",
        "stad": "stad",
        "stomach adenocarcinoma": "stad",
        "췌장암": "pdac",
        "pdac": "pdac",
        "paad": "pdac",
        "pancreatic cancer": "pdac",
        "두경부암": "hnsc",
        "hnsc": "hnsc",
        "head and neck cancer": "hnsc",
        "유방암": "brca",
        "brca": "brca",
        "breast cancer": "brca",
        "폐암": "luad",
        "luad": "luad",
        "lung adenocarcinoma": "luad",
        "간암": "lihc",
        "lihc": "lihc",
        "liver cancer": "lihc",
    }
    normalized = value.strip().lower()
    if normalized in known:
        return known[normalized]
    token = re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()
    return token or "disease"
