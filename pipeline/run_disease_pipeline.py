#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib
import inspect
import csv
import json
import os
import random
import sys
import traceback
from pathlib import Path
from typing import Any

import yaml

try:
    import numpy as np
except Exception:  # pragma: no cover - optional at import time
    np = None

try:
    import torch
except Exception:  # pragma: no cover - optional at import time
    torch = None

PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if not (PROJECT_ROOT / "pipeline").exists() and (PIPELINE_ROOT / "steps").exists():
    import types

    package = types.ModuleType("pipeline")
    package.__path__ = [str(PIPELINE_ROOT)]
    sys.modules.setdefault("pipeline", package)

SM_INPUT_DIR = Path(os.environ.get("SM_INPUT_DIR", "/opt/ml/processing/input/data"))
SM_OUTPUT_DIR = Path(os.environ.get("SM_OUTPUT_DIR", "/opt/ml/processing/output"))


def is_sagemaker_processing() -> bool:
    return bool(
        os.environ.get("SM_PROCESSING_INPUT")
        or os.environ.get("SM_PROCESSING_JOB_NAME")
        or os.environ.get("SM_CURRENT_HOST")
    )


def apply_runtime_paths(config: dict[str, Any]) -> dict[str, Any]:
    if not is_sagemaker_processing():
        return config
    disease_code = disease_code_from_config(config)
    output_root = SM_OUTPUT_DIR / f"{disease_code}_pipeline"
    config["project_root"] = str(output_root)
    config.setdefault("runtime", {})["environment"] = "sagemaker_processing"
    config["runtime"]["input_dir"] = str(SM_INPUT_DIR)
    config["runtime"]["output_dir"] = str(SM_OUTPUT_DIR)
    if os.environ.get("S3_OUTPUT"):
        config.setdefault("output", {})["s3_output_path"] = os.environ["S3_OUTPUT"]
    if os.environ.get("RANDOM_SEED"):
        config["random_seed"] = int(os.environ["RANDOM_SEED"])
    image = config.setdefault("image_modal", {})
    image["output_root"] = str(output_root / "outputs" / "image_modal")
    image.setdefault("merged_npy", str(output_root / "outputs" / "image_modal" / "step_im2" / f"all_patient_embeddings_{disease_code.lower()}_merged.npy"))
    image.setdefault("embedding_metadata_csv", str(output_root / "outputs" / "image_modal" / "step_im2" / f"all_patient_embeddings_{disease_code.lower()}_metadata.csv"))
    config.setdefault("drug", {})["top30_csv"] = str(output_root / "outputs" / "final_selection" / "admet_filtered_top15.csv")
    return config


STEP_MODULES = {
    "step1": "pipeline.steps.step1_data_collection",
    "step2": "pipeline.steps.step2_basic_pipeline",
    "step3": "pipeline.steps.step3_admet",
    "im1": "pipeline.steps.im1_image_collection",
    "im2": "pipeline.steps.im2_embedding",
    "im3": "pipeline.steps.im3_clustering",
    "im4a": "pipeline.steps.im4a_clinical",
    "im4c": "pipeline.steps.im4c_cluster_drug",
    "im5": "pipeline.steps.im5_report",
}
DEFAULT_ORDER = ["step1", "step2", "step3", "im1", "im2", "im3", "im4a", "im4c", "im5"]
MAX_AGENT_RETRIES = 3
DEFAULT_RANDOM_SEED = 42


def set_global_random_seed(config: dict[str, Any] | None = None) -> int:
    seed = DEFAULT_RANDOM_SEED
    if config is not None:
        seed = int(config.get("random_seed", config.get("seed", DEFAULT_RANDOM_SEED)) or DEFAULT_RANDOM_SEED)
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    if np is not None:
        np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        try:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        except Exception:
            pass
    return seed


DEFAULT_CONFIG: dict[str, Any] = {
    "random_seed": DEFAULT_RANDOM_SEED,
    "disease": {
        "name": "AUTO",
        "label": "",
        "type": "unknown",
        "number": 0,
    },
    "data": {
        "source": "GDSC",
        "tcga_project": "",
        "image_source": "",
        "image_type": "",
        "geo_datasets": [],
        "chembl_targets": [],
    },
    "model": {
        "basic_pipeline": "config_a",
        "foundation_model": "",
        "embedding_dim": None,
    },
    "analysis": {
        "driver_genes": [],
        "subtypes": [],
        "subtype_column": "",
        "clinical_vars": [],
        "continuous_vars": [],
        "k_values": list(range(2, 9)),
        "clustering_k_range": list(range(2, 9)),
    },
    "tier_classification": {
        "tier1_drugs": [],
        "tier4_exclude": [],
    },
    "execution": {
        "step3_env": "aws",
        "local_gpu": "xpu",
        "mode": "light",
        "model_count": 3,
        "wsi_limit": 100,
        "wsi_max_limit": 200,
        "wsi_smoke_count": 1,
        "wsi_parallel_downloads": 4,
        "embedding_parallel_parts": 4,
        "wsi_shard_size": 25,
        "self_heal": True,
        "supervisor": True,
        "max_step_retries": 2,
        "steps": DEFAULT_ORDER,
    },
    "output": {
        "s3_disease_folder": "",
    },
    "image_modal": {},
    "drug": {},
}

PLAN_PROMPT = """다음 질환에 대해 약물 재창출 파이프라인 config를 설계해줘.
질환: {disease}

JSON으로만 응답해. 마크다운 백틱 없이 순수 JSON만:
{{
  "disease": {{
    "name": "LAML",
    "label": "급성 골수성 백혈병",
    "type": "cancer",
    "number": 0
  }},
  "data": {{
    "source": "GDSC",
    "tcga_project": "TCGA-LAML",
    "image_source": "TCGA",
    "image_type": "wsi",
    "geo_datasets": [],
    "chembl_targets": []
  }},
  "model": {{
    "basic_pipeline": "config_a",
    "foundation_model": "UNI2",
    "embedding_dim": 1536
  }},
  "analysis": {{
    "driver_genes": ["FLT3", "NPM1", "IDH1", "IDH2", "TP53"],
    "subtypes": [],
    "subtype_column": "",
    "clinical_vars": ["AJCC_PATHOLOGIC_TUMOR_STAGE"],
    "clustering_k_range": [2, 3, 4, 5]
  }},
  "tier_classification": {{
    "tier1_drugs": [],
    "tier4_exclude": []
  }},
    "execution": {{
    "step3_env": "aws",
    "local_gpu": "xpu",
    "mode": "light",
    "model_count": 3,
    "wsi_limit": 100,
    "wsi_max_limit": 200,
    "wsi_smoke_count": 1,
    "wsi_parallel_downloads": 4,
    "embedding_parallel_parts": 4,
    "wsi_shard_size": 25,
    "self_heal": true,
    "supervisor": true
  }},
  "output": {{
    "s3_disease_folder": "LAML/"
  }},
  "image_modal": {{
    "enabled": true,
    "auto_launch": false,
    "skip_if_missing": true
  }}
}}"""

EVAL_PROMPT = """다음 약물 재창출 파이프라인 결과를 평가해줘.

질환: {disease}
Silhouette: {silhouette}
Clinical p-values: {p_values}
Tier1 약물: {tier1_count}개
Cluster-Drug 연결: {drug_links}건

JSON으로만 응답해:
{{
  "verdict": "ok" 또는 "retry",
  "reason": "이유",
  "retry_action": {{
    "step": "im3",
    "change": {{"clustering_k_range": [2, 3]}}
  }}
}}"""


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    config["_config_path"] = str(Path(path).resolve())
    return config


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < start:
            raise
        parsed = json.loads(raw[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Claude response JSON root must be an object.")
    return parsed


def ensure_anthropic_api_key() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    secret_id = os.environ.get("ANTHROPIC_SECRET_ID")
    if not secret_id:
        return
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 패키지가 필요합니다. Secrets Manager에서 Anthropic key를 읽을 수 없습니다.") from exc
    secret_string = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]
    try:
        payload = json.loads(secret_string)
        api_key = payload.get("ANTHROPIC_API_KEY") or payload.get("api_key")
    except json.JSONDecodeError:
        api_key = secret_string
    if not api_key:
        raise RuntimeError(f"Secret {secret_id} does not contain ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = api_key


def anthropic_client() -> Any:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic 패키지가 필요합니다. `python -m pip install anthropic` 후 다시 실행하세요.") from exc
    ensure_anthropic_api_key()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수 또는 ANTHROPIC_SECRET_ID 환경변수가 필요합니다.")
    return anthropic.Anthropic()


def claude_text_response(prompt: str, max_tokens: int) -> str:
    client = anthropic_client()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


def normalize_agent_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = deep_merge(DEFAULT_CONFIG, config)
    normalized["random_seed"] = int(normalized.get("random_seed", DEFAULT_RANDOM_SEED) or DEFAULT_RANDOM_SEED)
    disease_code = disease_code_from_config(normalized)
    normalized.setdefault("project_root", f"./{disease_code}_pipeline")
    normalized.setdefault("s3_raw_root", f"s3://say2-4team/{disease_code}_raw")
    normalized.setdefault("raw_template_root", "s3://say2-4team/HNSC_raw")
    normalized.setdefault("auto_provision_raw", True)

    analysis = normalized.setdefault("analysis", {})
    if "clustering_k_range" in config.get("analysis", {}):
        analysis["k_values"] = analysis["clustering_k_range"]
    elif "k_values" in analysis:
        analysis["clustering_k_range"] = analysis["k_values"]
    execution = normalized.setdefault("execution", {})
    execution.setdefault("steps", DEFAULT_ORDER)
    if os.environ.get("WSI_DEFAULT_LIMIT"):
        execution["wsi_limit"] = int(os.environ["WSI_DEFAULT_LIMIT"])
    if os.environ.get("WSI_MAX_LIMIT"):
        execution["wsi_max_limit"] = int(os.environ["WSI_MAX_LIMIT"])
    if os.environ.get("WSI_SMOKE_COUNT"):
        execution["wsi_smoke_count"] = int(os.environ["WSI_SMOKE_COUNT"])
    if os.environ.get("WSI_PARALLEL_DOWNLOADS"):
        execution["wsi_parallel_downloads"] = int(os.environ["WSI_PARALLEL_DOWNLOADS"])
    if os.environ.get("EMBEDDING_PARALLEL_PARTS"):
        execution["embedding_parallel_parts"] = int(os.environ["EMBEDDING_PARALLEL_PARTS"])
    apply_execution_mode(normalized)
    image = normalized.setdefault("image_modal", {})
    image.setdefault("enabled", True)
    image.setdefault("skip_if_missing", True)
    requested_wsi = int(execution.get("wsi_limit", image.get("wsi_limit", 100)) or 100)
    max_wsi = int(execution.get("wsi_max_limit", image.get("wsi_max_limit", 200)) or 200)
    image["wsi_limit"] = max(1, min(requested_wsi, max_wsi))
    image.setdefault("wsi_max_limit", max_wsi)
    image.setdefault("wsi_smoke_count", int(execution.get("wsi_smoke_count", 1) or 1))
    image.setdefault("wsi_parallel_downloads", int(execution.get("wsi_parallel_downloads", 4) or 4))
    image.setdefault("embedding_parallel_parts", int(execution.get("embedding_parallel_parts", 4) or 4))
    image.setdefault("wsi_shard_size", max(1, (int(image["wsi_limit"]) + int(image["embedding_parallel_parts"]) - 1) // int(image["embedding_parallel_parts"])))
    image.setdefault("embedding_instance_count", int(image["embedding_parallel_parts"]))
    image.setdefault("output_root", f"./{disease_code}_pipeline/outputs/image_modal")
    image.setdefault("s3_prefix", f"{disease_code.lower()}_image_modal_20260511_v1")
    image.setdefault("s3_raw_wsi_root", f"s3://say2-4team/{image['s3_prefix']}/wsi_raw/")
    image.setdefault("s3_tiles_root", f"s3://say2-4team/{image['s3_prefix']}/output/wsi_tiles/")
    image.setdefault(
        "s3_embedding_root",
        f"s3://say2-4team/{image['s3_prefix']}/output/embeddings_mid/",
    )
    image.setdefault("s3_logs_root", f"s3://say2-4team/{image['s3_prefix']}/output/logs/")
    if str(execution.get("mode", "light")).lower() == "full" and image.get("disable_auto_launch") is not True:
        image["auto_launch"] = True
    else:
        image.setdefault("auto_launch", False)
    drug = normalized.setdefault("drug", {})
    drug.setdefault("top30_csv", f"./{disease_code}_pipeline/outputs/final_selection/admet_filtered_top15.csv")
    return normalized


def disease_code_from_config(config: dict[str, Any]) -> str:
    raw = config.get("tcga_code", config.get("disease", "UNKNOWN"))
    if isinstance(raw, dict):
        raw = raw.get("code", raw.get("name", "UNKNOWN"))
    return str(raw).upper()


def apply_execution_mode(config: dict[str, Any]) -> None:
    execution = config.setdefault("execution", {})
    mode = str(execution.get("mode", config.get("mode", "light"))).lower()
    default_models = ["lightgbm", "xgboost", "catboost", "residual_mlp", "mlp"]
    model_count = int(execution.get("model_count", config.get("model_count", 3)) or 3)
    config.setdefault("models", default_models[: max(1, min(model_count, len(default_models)))])
    config.setdefault("n_splits", int(execution.get("n_splits", config.get("n_splits", 2)) or 2))
    config.setdefault("candidate_limit", int(execution.get("candidate_limit", config.get("candidate_limit", 30)) or 30))
    config.setdefault("max_crispr_features", int(execution.get("max_crispr_features", config.get("max_crispr_features", 3000)) or 3000))
    config.setdefault("max_lincs_features", int(execution.get("max_lincs_features", config.get("max_lincs_features", 768)) or 768))


def agent_plan(disease_name: str) -> Path:
    """Agent 1: 질환 분석 -> yaml config 생성."""
    text = claude_text_response(PLAN_PROMPT.format(disease=disease_name), max_tokens=1000)
    config_json = normalize_agent_config(extract_json(text))
    disease_code = str(config_json.get("disease", {}).get("name", disease_name)).lower()
    safe_code = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in disease_code)
    config_path = PIPELINE_ROOT / "configs" / f"auto_{safe_code}.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config_json, f, allow_unicode=True, sort_keys=False)
    print(f"Agent 1: config 생성 완료 -> {config_path}")
    return config_path


def config_output_root(config: dict[str, Any]) -> Path | None:
    output_root = config.get("image_modal", {}).get("output_root")
    if not output_root:
        disease = config.get("disease", {}).get("name")
        if disease:
            output_root = PROJECT_ROOT / str(disease) / f"0.Image_modal_{disease}"
    return Path(output_root) if output_root else None


def read_csv_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append({str(k): str(v) for k, v in row.items()})
            if limit and len(rows) >= limit:
                break
        return rows


def collect_result_metrics(config: dict[str, Any], step_results: list[dict[str, Any]]) -> dict[str, Any]:
    output_root = config_output_root(config)
    metrics: dict[str, Any] = {
        "step_results": step_results,
        "output_root": str(output_root) if output_root else "",
        "silhouette": None,
        "p_values": {},
        "tier1_count": 0,
        "drug_links": 0,
    }
    if not output_root:
        return metrics

    silhouette_rows = read_csv_rows(output_root / "step_im3" / "kmeans_silhouette.csv")
    for row in silhouette_rows:
        is_best = row.get("is_best", "").lower() in {"true", "1", "yes"} or row.get("best", "").lower() in {"true", "1", "yes"}
        if is_best or metrics["silhouette"] is None:
            value = row.get("silhouette") or row.get("silhouette_score")
            try:
                metrics["silhouette"] = float(value) if value not in {None, ""} else None
            except ValueError:
                metrics["silhouette"] = value

    tests = read_csv_rows(output_root / "step_im4a" / "cluster_statistical_tests.csv")
    p_values: dict[str, Any] = {}
    for row in tests:
        key = row.get("variable") or row.get("gene") or row.get("test") or row.get("name")
        value = row.get("p_value") or row.get("p") or row.get("pvalue")
        if key and value not in {None, ""}:
            try:
                p_values[key] = float(value)
            except ValueError:
                p_values[key] = value
    metrics["p_values"] = p_values

    step_im4c = output_root / "step_im4c"
    for candidate in ("cluster_drug_hypotheses.csv", "cluster_drug_linkage.csv"):
        path = step_im4c / candidate
        if path.exists():
            metrics["drug_links"] = len(read_csv_rows(path))
            break
    if metrics["drug_links"] == 0 and step_im4c.exists():
        linkage_files = sorted(step_im4c.glob("*cluster*drug*.csv"))
        if linkage_files:
            metrics["drug_links"] = len(read_csv_rows(linkage_files[0]))

    tier_files = sorted(step_im4c.glob("*4tier*.csv")) + sorted(step_im4c.glob("*tier*.csv"))
    if tier_files:
        rows = read_csv_rows(tier_files[0])
        metrics["tier1_count"] = sum(
            1
            for row in rows
            if str(row.get("tier") or row.get("Tier") or row.get("tier_class") or "").lower().startswith("tier 1")
            or str(row.get("tier") or row.get("Tier") or row.get("tier_class") or "") == "1"
        )
    return metrics


def agent_evaluate(config: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    """Agent 2: 결과 평가 -> ok/retry 판단."""
    pending_steps = {
        row.get("step")
        for row in results.get("step_results", [])
        if str(row.get("status", row.get("step_status", ""))).lower() == "pending"
    }
    if pending_steps & {"im1", "im2"}:
        return {
            "verdict": "ok",
            "reason": "Image-modal upstream jobs are pending; wait for WSI/embedding outputs before retrying downstream IM steps.",
            "retry_action": {},
        }
    text = claude_text_response(
        EVAL_PROMPT.format(
            disease=config.get("disease", {}).get("name", ""),
            silhouette=results.get("silhouette"),
            p_values=json.dumps(results.get("p_values", {}), ensure_ascii=False),
            tier1_count=results.get("tier1_count", 0),
            drug_links=results.get("drug_links", 0),
        ),
        max_tokens=500,
    )
    evaluation = extract_json(text)
    evaluation.setdefault("verdict", "ok")
    evaluation.setdefault("reason", "")
    return evaluation


def apply_retry_action(config: dict[str, Any], retry_action: dict[str, Any]) -> str | None:
    step = retry_action.get("step")
    change = retry_action.get("change") or {}
    if not isinstance(change, dict):
        return step
    if "clustering_k_range" in change:
        config.setdefault("analysis", {})["k_values"] = change["clustering_k_range"]
        config.setdefault("analysis", {})["clustering_k_range"] = change["clustering_k_range"]
    config_path = config.get("_config_path")
    if config_path:
        clean_config = {k: v for k, v in config.items() if not k.startswith("_")}
        with Path(config_path).open("w", encoding="utf-8") as f:
            yaml.safe_dump(clean_config, f, allow_unicode=True, sort_keys=False)
    return step


def persist_config(config: dict[str, Any]) -> None:
    config_path = config.get("_config_path")
    if not config_path:
        return
    clean_config = {k: v for k, v in config.items() if not k.startswith("_")}
    with Path(config_path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(clean_config, f, allow_unicode=True, sort_keys=False)


def agent0_preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Agent 0: normalize orchestration settings and catch obvious deadlocks."""
    config.update(normalize_agent_config(config))
    steps = config.get("execution", {}).get("steps", DEFAULT_ORDER)
    unknown = [step for step in steps if step not in STEP_MODULES]
    if unknown:
        raise KeyError(f"Agent 0 found unknown steps: {unknown}")
    report = {
        "agent": "agent0_supervisor",
        "phase": "preflight",
        "disease": disease_code_from_config(config),
        "mode": config.get("execution", {}).get("mode", "light"),
        "steps": steps,
        "models": config.get("models", []),
        "image_enabled": config.get("image_modal", {}).get("enabled", True),
        "image_auto_launch": config.get("image_modal", {}).get("auto_launch", False),
        "s3_raw_wsi_root": config.get("image_modal", {}).get("s3_raw_wsi_root", ""),
        "s3_tiles_root": config.get("image_modal", {}).get("s3_tiles_root", ""),
        "s3_embedding_root": config.get("image_modal", {}).get("s3_embedding_root", ""),
        "self_heal": config.get("execution", {}).get("self_heal", True),
    }
    write_agent_report(config, "agent0_preflight.json", report)
    print(json.dumps({"agent0_preflight": report}, ensure_ascii=False, indent=2))
    return report


def agent0_postflight(config: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    statuses = [
        {"step": row.get("step"), "status": row.get("status", row.get("step_status", "unknown"))}
        for row in metrics.get("step_results", [])
    ]
    blocking_failures = [row for row in statuses if str(row.get("status")).lower() in {"failed", "error"}]
    pending = [row for row in statuses if str(row.get("status")).lower() == "pending"]
    report = {
        "agent": "agent0_supervisor",
        "phase": "postflight",
        "disease": disease_code_from_config(config),
        "blocking_failures": blocking_failures,
        "pending_steps": pending,
        "silhouette": metrics.get("silhouette"),
        "tier1_count": metrics.get("tier1_count", 0),
        "drug_links": metrics.get("drug_links", 0),
        "verdict": "blocked" if blocking_failures else "ok_with_pending" if pending else "ok",
    }
    write_agent_report(config, "agent0_postflight.json", report)
    print(json.dumps({"agent0_postflight": report}, ensure_ascii=False, indent=2))
    return report


def write_agent_report(config: dict[str, Any], filename: str, payload: dict[str, Any]) -> None:
    project_root = Path(config.get("project_root", f"./{disease_code_from_config(config)}_pipeline"))
    out_dir = project_root / "outputs" / "agent_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def agent3_self_heal(config: dict[str, Any], step: str, exc: BaseException) -> dict[str, Any]:
    """Agent 3: apply deterministic repairs from traceback/config context."""
    message = f"{type(exc).__name__}: {exc}"
    repairs: list[str] = []
    disease = disease_code_from_config(config)
    project_root = Path(config.get("project_root", f"./{disease}_pipeline"))

    if step == "im4c" and "top30" in message.lower():
        candidates = [
            project_root / "outputs/final_selection/admet_filtered_top15.csv",
            project_root / "outputs/final_selection/selected_drugs_top_n.csv",
        ]
        for candidate in candidates:
            if candidate.exists():
                config.setdefault("drug", {})["top30_csv"] = str(candidate)
                repairs.append(f"set drug.top30_csv={candidate}")
                break

    if step in {"im2", "im3", "im4a", "im4c", "im5"} and any(
        token in message.lower() for token in ["missing", "required", "not found", "no embedding"]
    ):
        config.setdefault("image_modal", {})["skip_if_missing"] = True
        repairs.append("set image_modal.skip_if_missing=true")

    if step == "step2" and "catboost" in message.lower():
        models = [m for m in config.get("models", []) if str(m).lower() != "catboost"]
        if models:
            config["models"] = models
            repairs.append("removed catboost from models")

    if step == "step2" and "drug__target_list" in message:
        config.setdefault("step2_runtime_hints", {})["optional_drug_meta_columns"] = True
        repairs.append("marked drug metadata columns as optional")

    if step == "step3" and "canonical_drug_id" in message and "merge on int64 and object" in message:
        config.setdefault("step3_runtime_hints", {})["canonical_drug_id_as_string"] = True
        repairs.append("marked canonical_drug_id merge key as string-normalized")

    persist_config(config)
    payload = {
        "agent": "agent3_self_healing",
        "step": step,
        "error": message,
        "traceback": traceback.format_exc(limit=8),
        "repairs": repairs,
        "retriable": bool(repairs),
    }
    write_agent_report(config, f"agent3_{step}_repair.json", payload)
    print(json.dumps({"agent3_self_heal": payload}, ensure_ascii=False, indent=2))
    return payload


class DiseasePipeline:
    def __init__(self, config: dict[str, Any], dry_run: bool = False) -> None:
        self.config = config
        self.dry_run = dry_run

    def run(self, only_step: str | None = None) -> list[dict[str, Any]]:
        steps = [only_step] if only_step else self.config.get("execution", {}).get("steps", DEFAULT_ORDER)
        results = []
        for step in steps:
            results.append(self.run_step(step))
        return results

    def run_step(self, step: str) -> dict[str, Any]:
        if step not in STEP_MODULES:
            raise KeyError(f"Unknown step '{step}'. Valid steps: {', '.join(STEP_MODULES)}")
        max_retries = int(self.config.get("execution", {}).get("max_step_retries", 2) or 0)
        self_heal = bool(self.config.get("execution", {}).get("self_heal", True))
        last_error: BaseException | None = None
        for attempt in range(max_retries + 1):
            try:
                module = importlib.import_module(STEP_MODULES[step])
                signature = inspect.signature(module.run)
                if "dry_run" in signature.parameters:
                    result = module.run(self.config, dry_run=self.dry_run)
                else:
                    result = module.run(self.config)
                payload = {"step": step, **result, "attempt": attempt + 1}
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return payload
            except Exception as exc:
                last_error = exc
                if not self_heal or attempt >= max_retries:
                    raise
                repair = agent3_self_heal(self.config, step, exc)
                if not repair.get("retriable"):
                    raise
                print(f"Agent 3: {step} 자동 복구 후 재시도 attempt={attempt + 2}")
        raise RuntimeError(f"{step} failed after retries: {last_error}")


def run_pipeline(config: dict[str, Any], step: str | None = None, dry_run: bool = False) -> list[dict[str, Any]]:
    set_global_random_seed(config)
    pipeline = DiseasePipeline(config, dry_run=dry_run)
    return pipeline.run(step)


def run_agent_pipeline(disease_name: str, dry_run: bool = False, mode: str | None = None) -> dict[str, Any]:
    config_path = agent_plan(disease_name)
    config = load_config(config_path)
    if mode:
        config.setdefault("execution", {})["mode"] = mode
    apply_runtime_paths(config)
    set_global_random_seed(config)
    agent0_preflight(config)
    last_metrics: dict[str, Any] = {}
    for attempt in range(1, MAX_AGENT_RETRIES + 1):
        print(f"Agent: 파이프라인 실행 attempt={attempt}")
        step_results = run_pipeline(config, dry_run=dry_run)
        last_metrics = collect_result_metrics(config, step_results)
        agent0_postflight(config, last_metrics)
        evaluation = agent_evaluate(config, last_metrics)
        print(json.dumps({"agent_evaluation": evaluation}, ensure_ascii=False, indent=2))
        if evaluation.get("verdict") == "ok":
            print("Agent: 결과 OK! 종료.")
            break
        retry_action = evaluation.get("retry_action") or {}
        step = apply_retry_action(config, retry_action)
        if not step:
            print("Agent: retry step이 없어 종료합니다.")
            break
        print(f"Agent: 재시도. 이유: {evaluation.get('reason', '')}")
        step_results = run_pipeline(config, step=step, dry_run=dry_run)
        last_metrics = collect_result_metrics(config, step_results)
    return last_metrics


def main(argv: list[str] | None = None) -> int:
    if argv is None and os.environ.get("DISEASE_NAME") and len(sys.argv) == 1:
        argv = ["--disease", os.environ["DISEASE_NAME"], "--mode", os.environ.get("PIPELINE_MODE", "full")]
    parser = argparse.ArgumentParser(description="Run a disease image-modal pipeline")
    parser.add_argument("--config", help="YAML config path")
    parser.add_argument("--disease", help="Disease name for Agent 1 config planning")
    parser.add_argument("--step", choices=sorted(STEP_MODULES), help="Run one step only")
    parser.add_argument("--mode", choices=["light", "full"], help="Override execution.mode")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing outputs")
    args = parser.parse_args(argv)

    if args.disease:
        if args.step:
            parser.error("--disease mode does not accept --step; Agent 2 decides retry steps.")
        try:
            run_agent_pipeline(args.disease, dry_run=args.dry_run, mode=args.mode)
        except RuntimeError as exc:
            parser.exit(2, f"Agent error: {exc}\n")
    elif args.config:
        config = load_config(args.config)
        if args.mode:
            config.setdefault("execution", {})["mode"] = args.mode
        apply_runtime_paths(config)
        set_global_random_seed(config)
        agent0_preflight(config)
        run_pipeline(config, step=args.step, dry_run=args.dry_run)
    else:
        parser.error("one of --config or --disease is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
