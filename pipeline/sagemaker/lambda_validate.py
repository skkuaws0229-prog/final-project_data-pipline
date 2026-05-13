from __future__ import annotations

from urllib.parse import urlparse

import boto3


def handler(event, context):
    disease_slug = event.get("disease_slug") or event.get("disease_name")
    s3_output = event["s3_output"].rstrip("/")
    bucket, prefix = _parse_s3(s3_output)
    s3 = boto3.client("s3")

    required_suffixes = [
        f"{disease_slug}/basic_pipeline/",
        f"{disease_slug}/image_modal/",
    ]
    required_files = [
        f"{disease_slug}/basic_pipeline/*/outputs/final_selection/selected_drugs_top_n.csv",
        f"{disease_slug}/basic_pipeline/*/outputs/final_selection/admet_filtered_top15.csv",
        f"{disease_slug}/image_modal/*/outputs/image_modal/step_im3/im3_k_search_results.csv",
        f"{disease_slug}/image_modal/*/outputs/image_modal/step_im5/image_modal_summary.md",
    ]

    checks = []
    for suffix in required_suffixes:
        checks.append(_prefix_check(s3, bucket, f"{prefix}/{suffix}".strip("/")))
    for pattern in required_files:
        checks.append(_glob_check(s3, bucket, prefix, pattern))

    missing = [c for c in checks if c["status"] == "MISSING"]
    return {"verdict": "PASS" if not missing else "FAIL", "checks": checks, "missing_count": len(missing)}


def _parse_s3(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected s3:// URI, got {uri}")
    return parsed.netloc, parsed.path.strip("/")


def _prefix_check(s3, bucket: str, prefix: str) -> dict:
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix.rstrip("/") + "/", MaxKeys=1)
    return {"file": prefix + "/", "status": "EXISTS" if resp.get("KeyCount", 0) > 0 else "MISSING"}


def _glob_check(s3, bucket: str, root_prefix: str, pattern: str) -> dict:
    # Lightweight wildcard support for '*' path segments by scanning the static prefix before first '*'.
    before_star = pattern.split("*", 1)[0]
    scan_prefix = f"{root_prefix}/{before_star}".strip("/")
    suffix = pattern.rsplit("*", 1)[-1]
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=scan_prefix, MaxKeys=1000)
    for obj in resp.get("Contents", []):
        if obj["Key"].endswith(suffix):
            return {"file": pattern, "status": "EXISTS", "matched_key": obj["Key"]}
    return {"file": pattern, "status": "MISSING"}
