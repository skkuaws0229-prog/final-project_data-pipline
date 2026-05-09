#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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

DEFAULT_CONFIG: dict[str, Any] = {
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
        "k_values": [2, 3, 4, 5],
        "clustering_k_range": [2, 3, 4, 5],
    },
    "tier_classification": {
        "tier1_drugs": [],
        "tier4_exclude": [],
    },
    "execution": {
        "step3_env": "aws",
        "local_gpu": "xpu",
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
    "local_gpu": "xpu"
  }},
  "output": {{
    "s3_disease_folder": "LAML/"
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


def anthropic_client() -> Any:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic 패키지가 필요합니다. `python -m pip install anthropic` 후 다시 실행하세요.") from exc
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY 환경변수가 필요합니다.")
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
    analysis = normalized.setdefault("analysis", {})
    if "clustering_k_range" in config.get("analysis", {}):
        analysis["k_values"] = analysis["clustering_k_range"]
    elif "k_values" in analysis:
        analysis["clustering_k_range"] = analysis["k_values"]
    execution = normalized.setdefault("execution", {})
    execution.setdefault("steps", DEFAULT_ORDER)
    return normalized


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
        module = importlib.import_module(STEP_MODULES[step])
        result = module.run(self.config, dry_run=self.dry_run)
        payload = {"step": step, **result}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload


def run_pipeline(config: dict[str, Any], step: str | None = None, dry_run: bool = False) -> list[dict[str, Any]]:
    pipeline = DiseasePipeline(config, dry_run=dry_run)
    return pipeline.run(step)


def run_agent_pipeline(disease_name: str, dry_run: bool = False) -> dict[str, Any]:
    config_path = agent_plan(disease_name)
    config = load_config(config_path)
    last_metrics: dict[str, Any] = {}
    for attempt in range(1, MAX_AGENT_RETRIES + 1):
        print(f"Agent: 파이프라인 실행 attempt={attempt}")
        step_results = run_pipeline(config, dry_run=dry_run)
        last_metrics = collect_result_metrics(config, step_results)
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
    parser = argparse.ArgumentParser(description="Run a disease image-modal pipeline")
    parser.add_argument("--config", help="YAML config path")
    parser.add_argument("--disease", help="Disease name for Agent 1 config planning")
    parser.add_argument("--step", choices=sorted(STEP_MODULES), help="Run one step only")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing outputs")
    args = parser.parse_args(argv)

    if args.disease:
        if args.step:
            parser.error("--disease mode does not accept --step; Agent 2 decides retry steps.")
        try:
            run_agent_pipeline(args.disease, dry_run=args.dry_run)
        except RuntimeError as exc:
            parser.exit(2, f"Agent error: {exc}\n")
    elif args.config:
        config = load_config(args.config)
        run_pipeline(config, step=args.step, dry_run=args.dry_run)
    else:
        parser.error("one of --config or --disease is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
