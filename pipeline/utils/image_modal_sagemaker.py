from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote


BUCKET = "say2-4team"
PIPELINE_TAG = "20260430_v1"
DEFAULT_PACKAGE_DIR = "luad_lihc_wsi_homepc_package_20260502_v1"
DEFAULT_SAGEMAKER_ROLE = "arn:aws:iam::666803869796:role/SKKU-SageMaker-Processing-Execution-Role"
DEFAULT_HF_SECRET_ID = "protein2text/huggingface/read-token"
IMAGE_MODAL_ROLE_POLICY = "brca-image-modal-new-cancer-prefixes-20260501"


def disease_code(config: dict[str, Any]) -> str:
    raw = config.get("tcga_code", config.get("disease", "UNKNOWN"))
    if isinstance(raw, dict):
        raw = raw.get("code", raw.get("name", "UNKNOWN"))
    return str(raw).upper()


def image_prefix(config: dict[str, Any]) -> str:
    image = config.setdefault("image_modal", {})
    code = disease_code(config).lower()
    return str(image.get("s3_prefix") or f"{code}_image_modal_20260511_v1").strip("/")


def ensure_image_defaults(config: dict[str, Any]) -> dict[str, str]:
    image = config.setdefault("image_modal", {})
    code = disease_code(config)
    lower = code.lower()
    prefix = image_prefix(config)
    roots = {
        "s3_raw_wsi_root": f"s3://{BUCKET}/{prefix}/wsi_raw/",
        "s3_tiles_root": f"s3://{BUCKET}/{prefix}/output/wsi_tiles/",
        "s3_embedding_root": f"s3://{BUCKET}/{prefix}/output/embeddings_mid/",
        "s3_logs_root": f"s3://{BUCKET}/{prefix}/output/logs/",
    }
    image.setdefault("s3_prefix", prefix)
    for key, value in roots.items():
        image.setdefault(key, value)
    return {key: str(image[key]) for key in roots}


def package_root(config: dict[str, Any]) -> Path:
    configured = config.get("image_modal", {}).get("sagemaker_package_root")
    if configured:
        return Path(configured).expanduser().resolve()
    candidates = [
        Path(__file__).resolve().parents[2] / DEFAULT_PACKAGE_DIR,
        Path.cwd() / DEFAULT_PACKAGE_DIR,
        Path.home() / "Documents" / "New project 2" / DEFAULT_PACKAGE_DIR,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()


def s3_object_count(uri: str, suffixes: tuple[str, ...] | None = None, limit: int | None = None) -> int:
    cmd = ["aws", "s3", "ls", uri.rstrip("/") + "/", "--recursive"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return 0
    count = 0
    for line in result.stdout.splitlines():
        parts = line.split()
        key = parts[-1] if parts else ""
        if not suffixes or key.endswith(suffixes):
            count += 1
            if limit and count >= limit:
                return count
    return count


def active_processing_jobs(name_contains: str) -> list[dict[str, Any]]:
    cmd = [
        "aws",
        "sagemaker",
        "list-processing-jobs",
        "--name-contains",
        name_contains[:63],
        "--status-equals",
        "InProgress",
        "--max-results",
        "20",
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return []
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return []
    return payload.get("ProcessingJobSummaries", []) or []


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_or_plan(cmd: list[str], cwd: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "dry_run", "command": cmd, "cwd": str(cwd)}
    env = os.environ.copy()
    env.setdefault("IMAGE_MODAL_WAIT", "0")
    env.setdefault("SAGEMAKER_ROLE", DEFAULT_SAGEMAKER_ROLE)
    env.setdefault("HUGGING_FACE_HUB_TOKEN_SECRET_ID", DEFAULT_HF_SECRET_ID)
    result = subprocess.run(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "status": "launched" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "command": cmd,
        "cwd": str(cwd),
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }


def _role_name_from_arn(role_arn: str) -> str:
    return role_arn.rsplit("/", 1)[-1]


def _policy_document_for_role(role_arn: str) -> dict[str, Any] | None:
    cmd = [
        "aws",
        "iam",
        "get-role-policy",
        "--role-name",
        _role_name_from_arn(role_arn),
        "--policy-name",
        IMAGE_MODAL_ROLE_POLICY,
        "--output",
        "json",
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None
    document = payload.get("PolicyDocument")
    if isinstance(document, str):
        try:
            document = json.loads(unquote(document))
        except json.JSONDecodeError:
            return None
    return document if isinstance(document, dict) else None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _prefix_from_s3_uri(uri: str) -> str:
    without_scheme = uri.replace("s3://", "", 1).rstrip("/") + "/"
    parts = without_scheme.split("/", 1)
    return parts[1] if len(parts) > 1 else ""


def _resource_for_s3_uri(uri: str) -> str:
    return f"arn:aws:s3:::{BUCKET}/{_prefix_from_s3_uri(uri)}*"


def _resource_covers(required: str, resources: list[str]) -> bool:
    required = required.rstrip("*")
    for resource in resources:
        if resource.endswith("*") and required.startswith(resource[:-1]):
            return True
        if resource == required or resource == required.rstrip("/"):
            return True
    return False


def _list_prefix_covers(required_prefix: str, condition: dict[str, Any]) -> bool:
    prefixes = []
    for operator in ("StringLike", "StringEquals"):
        block = condition.get(operator, {})
        prefixes.extend(_as_list(block.get("s3:prefix")))
    for prefix in prefixes:
        prefix = str(prefix)
        if prefix.endswith("*") and required_prefix.startswith(prefix[:-1]):
            return True
        if required_prefix == prefix or required_prefix.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def sagemaker_s3_access_preflight(config: dict[str, Any], uris: list[str]) -> dict[str, Any]:
    role_arn = os.environ.get("SAGEMAKER_ROLE", DEFAULT_SAGEMAKER_ROLE)
    document = _policy_document_for_role(role_arn)
    if not document:
        return {
            "ok": False,
            "role": role_arn,
            "policy": IMAGE_MODAL_ROLE_POLICY,
            "reason": "SageMaker role policy could not be read",
            "uris": uris,
        }

    statements = _as_list(document.get("Statement"))
    failures = []
    for uri in uris:
        required_resource = _resource_for_s3_uri(uri)
        required_prefix = _prefix_from_s3_uri(uri)
        has_object_access = False
        has_list_access = False
        for statement in statements:
            if statement.get("Effect") != "Allow":
                continue
            actions = {str(action) for action in _as_list(statement.get("Action"))}
            resources = [str(resource) for resource in _as_list(statement.get("Resource"))]
            if {"s3:PutObject", "s3:GetObject"}.issubset(actions) and _resource_covers(required_resource, resources):
                has_object_access = True
            if "s3:ListBucket" in actions and f"arn:aws:s3:::{BUCKET}" in resources:
                if _list_prefix_covers(required_prefix, statement.get("Condition", {})):
                    has_list_access = True
        if not has_object_access or not has_list_access:
            failures.append(
                {
                    "uri": uri,
                    "required_resource": required_resource,
                    "list_prefix": required_prefix,
                    "has_object_access": has_object_access,
                    "has_list_access": has_list_access,
                }
            )

    return {
        "ok": not failures,
        "role": role_arn,
        "policy": IMAGE_MODAL_ROLE_POLICY,
        "uris": uris,
        "failures": failures,
    }


def launch_wsi_download(config: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    roots = ensure_image_defaults(config)
    code = disease_code(config)
    data = config.get("data", {})
    image = config.get("image_modal", {})
    projects = image.get("tcga_projects") or data.get("tcga_project") or f"TCGA-{code}"
    if isinstance(projects, list):
        projects = ",".join(projects)
    wsi_limit = int(image.get("wsi_limit", config.get("execution", {}).get("wsi_limit", 100)) or 100)
    smoke_count = max(1, int(image.get("wsi_smoke_count", config.get("execution", {}).get("wsi_smoke_count", 1)) or 1))
    download_workers = max(1, int(image.get("wsi_parallel_downloads", config.get("execution", {}).get("wsi_parallel_downloads", 4)) or 4))
    raw_wsi_count = s3_object_count(roots["s3_raw_wsi_root"], suffixes=(".svs", ".SVS"), limit=wsi_limit)
    target_slides = smoke_count if raw_wsi_count < smoke_count else wsi_limit
    phase = "smoke" if target_slides == smoke_count else "main"
    label = f"{code.lower()}-wsi-step1"
    jobs = active_processing_jobs(label)
    if jobs:
        return {
            "status": "already_running",
            "step": "wsi_download",
            "phase": phase,
            "raw_wsi_count": raw_wsi_count,
            "target_slides": target_slides,
            "jobs": jobs,
        }
    if raw_wsi_count >= wsi_limit:
        return {
            "status": "already_completed",
            "step": "wsi_download",
            "phase": "completed",
            "raw_wsi_count": raw_wsi_count,
            "target_slides": wsi_limit,
        }
    cmd = [
        "python3",
        "run_tcga_wsi_step1_sagemaker_20260501_v1.py",
        "--cancer",
        code,
        "--projects",
        str(projects),
        "--n-slides",
        str(target_slides),
        "--s3-uri",
        roots["s3_raw_wsi_root"],
        "--instance-type",
        str(image.get("download_instance_type", "ml.m5.4xlarge")),
        "--volume-size-gb",
        str(image.get("download_volume_size_gb", 1024)),
        "--download-workers",
        str(download_workers),
    ]
    result = run_or_plan(cmd, package_root(config), dry_run)
    result.update(
        {
            "step": "wsi_download",
            "phase": phase,
            "raw_wsi_count": raw_wsi_count,
            "target_slides": target_slides,
            "wsi_limit": wsi_limit,
            "wsi_max_limit": int(image.get("wsi_max_limit", config.get("execution", {}).get("wsi_max_limit", 200)) or 200),
            "download_workers": download_workers,
            "protocol": "1-slide smoke first; after smoke output exists, launch capped main WSI download with 4 parallel download workers.",
        }
    )
    return result


def launch_tile_preprocessing(config: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    roots = ensure_image_defaults(config)
    code = disease_code(config)
    image = config.get("image_modal", {})
    preflight = sagemaker_s3_access_preflight(
        config,
        [roots["s3_raw_wsi_root"], roots["s3_tiles_root"], roots["s3_logs_root"]],
    )
    if not preflight["ok"]:
        return {"status": "blocked_preflight_failed", "step": "tile_preprocessing", "preflight": preflight}
    run_label = f"{code.lower()}-full-step2-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    jobs = active_processing_jobs(f"{code.lower()}-full-step2")
    if jobs:
        return {"status": "already_running", "step": "tile_preprocessing", "jobs": jobs}
    cmd = [
        "python3",
        "run_brca_image_sagemaker_20260430_v1.py",
        "--mode",
        "existing-shard-step2",
        "--run-label",
        run_label,
        "--raw-uri",
        roots["s3_raw_wsi_root"],
        "--tiles-uri",
        roots["s3_tiles_root"],
        "--logs-uri",
        roots["s3_logs_root"],
        "--cpu-instance-type",
        str(image.get("preprocess_instance_type", "ml.m5.4xlarge")),
        "--volume-size-gb",
        str(image.get("preprocess_volume_size_gb", 1024)),
    ]
    return run_or_plan(cmd, package_root(config), dry_run)


def launch_embedding(config: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    roots = ensure_image_defaults(config)
    code = disease_code(config)
    image = config.get("image_modal", {})
    lower = code.lower()
    preflight = sagemaker_s3_access_preflight(
        config,
        [roots["s3_tiles_root"], roots["s3_embedding_root"], roots["s3_logs_root"]],
    )
    if not preflight["ok"]:
        return {"status": "blocked_preflight_failed", "step": "embedding", "preflight": preflight}
    jobs = active_processing_jobs(f"{lower}-image-modal-20260430-v1-step3")
    if jobs:
        return {"status": "already_running", "step": "embedding", "jobs": jobs}
    wsi_limit = int(image.get("wsi_limit", config.get("execution", {}).get("wsi_limit", 100)) or 100)
    part_count = max(1, int(image.get("embedding_parallel_parts", config.get("execution", {}).get("embedding_parallel_parts", 4)) or 4))
    shard_size = max(1, (wsi_limit + part_count - 1) // part_count)
    parts = [f"part{i:02d}" for i in range(part_count)]
    part_counts = [wsi_limit // part_count] * part_count
    for i in range(wsi_limit % part_count):
        part_counts[i] += 1
    part_starts = []
    cursor = 0
    for count in part_counts:
        part_starts.append(cursor)
        cursor += count
    cmd = [
        "python3",
        "run_luad_step3_parts_20260504.py",
        "--cancer",
        code,
        "--s3-prefix",
        image_prefix(config),
        "--parts",
        *parts,
        "--part-size",
        str(shard_size),
        "--part-counts",
        *[str(count) for count in part_counts],
        "--part-starts",
        *[str(start) for start in part_starts],
        "--instance-type",
        str(image.get("embedding_instance_type", "ml.g4dn.xlarge")),
        "--volume-size-gb",
        str(image.get("embedding_volume_size_gb", 125)),
        "--batch-size",
        str(image.get("embedding_batch_size", 8)),
    ]
    return run_or_plan(cmd, package_root(config), dry_run)
