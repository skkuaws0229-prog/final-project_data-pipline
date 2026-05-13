#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

PIPELINE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PIPELINE_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if not (PROJECT_ROOT / "pipeline").exists() and (PIPELINE_ROOT / "steps").exists():
    import types

    package = types.ModuleType("pipeline")
    package.__path__ = [str(PIPELINE_ROOT)]
    sys.modules.setdefault("pipeline", package)

from pipeline.steps import im3_clustering, im4c_cluster_drug, im5_report  # noqa: E402
from run_disease_pipeline import set_global_random_seed  # noqa: E402

SM_INPUT = Path(os.environ.get("SM_INPUT_DIR", "/opt/ml/processing/input"))
SM_OUTPUT = Path(os.environ.get("SM_OUTPUT_DIR", "/opt/ml/processing/output"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run IM3~IM5 image-modal CPU steps in SageMaker Processing")
    parser.add_argument("--config", help="Optional YAML config path. If omitted, a minimal config is built from env/input mounts.")
    parser.add_argument("--disease", default=os.environ.get("DISEASE_NAME", "AUTO"))
    args = parser.parse_args()

    config = _load_or_build_config(args.config, args.disease)
    set_global_random_seed(config)
    _prepare_inputs(config)

    im3 = im3_clustering.run(config)
    im4c = im4c_cluster_drug.run(config)
    im5 = im5_report.run(config)
    print({"im3": im3, "im4c": im4c, "im5": im5})
    return 0


def _load_or_build_config(config_path: str | None, disease_name: str) -> dict[str, Any]:
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        disease_code = os.environ.get("DISEASE_CODE") or os.environ.get("DISEASE_SLUG", disease_name).upper()
        config = {
            "random_seed": int(os.environ.get("RANDOM_SEED", "42")),
            "disease": {"name": disease_code, "label": disease_name, "type": "cancer"},
            "analysis": {"k_values": list(range(2, 9)), "clustering_k_range": list(range(2, 9)), "driver_genes": []},
            "model": {"foundation_model": "UNI2", "embedding_dim": 1536},
            "project_root": str(SM_OUTPUT / f"{disease_code}_pipeline"),
            "image_modal": {},
            "drug": {},
        }
    disease_code = str(config.get("disease", {}).get("name", os.environ.get("DISEASE_CODE", "AUTO"))).upper()
    project_root = SM_OUTPUT / f"{disease_code}_pipeline"
    image_root = project_root / "outputs" / "image_modal"
    config["project_root"] = str(project_root)
    config.setdefault("random_seed", int(os.environ.get("RANDOM_SEED", "42")))
    config.setdefault("analysis", {}).setdefault("clustering_k_range", list(range(2, 9)))
    config["analysis"].setdefault("k_values", config["analysis"]["clustering_k_range"])
    image = config.setdefault("image_modal", {})
    image["output_root"] = str(image_root)
    image["merged_npy"] = str(image_root / "step_im2" / f"all_patient_embeddings_{disease_code.lower()}_merged.npy")
    image["embedding_metadata_csv"] = str(image_root / "step_im2" / f"all_patient_embeddings_{disease_code.lower()}_metadata.csv")
    image.setdefault("skip_if_missing", False)
    config.setdefault("drug", {})["top30_csv"] = _find_basic_top30(disease_code)
    return config


def _prepare_inputs(config: dict[str, Any]) -> None:
    disease_code = str(config["disease"]["name"]).lower()
    image = config["image_modal"]
    merged_npy = Path(image["merged_npy"])
    metadata_csv = Path(image["embedding_metadata_csv"])
    merged_npy.parent.mkdir(parents=True, exist_ok=True)

    embeddings_root = SM_INPUT / "embeddings"
    npy_candidates = sorted(embeddings_root.rglob("*.npy"))
    metadata_candidates = sorted(embeddings_root.rglob("*metadata*.csv"))
    if npy_candidates:
        shutil.copy2(npy_candidates[0], merged_npy)
    parquet_candidates = sorted(embeddings_root.rglob("all_slide_embeddings_20260430_v1.parquet"))
    if parquet_candidates and not npy_candidates:
        image["embedding_root"] = str(embeddings_root)
    if metadata_candidates:
        shutil.copy2(metadata_candidates[0], metadata_csv)
    elif npy_candidates:
        # im3 can proceed without metadata; ids will become sample_0000...
        pass

    if not merged_npy.exists() and not image.get("embedding_root"):
        raise FileNotFoundError(f"No merged .npy or embedding parquet input found under {embeddings_root}")


def _find_basic_top30(disease_code: str) -> str:
    basic_root = SM_INPUT / "basic_results"
    candidates = [
        *basic_root.rglob("admet_filtered_top15.csv"),
        *basic_root.rglob("selected_drugs_top_n.csv"),
        *basic_root.rglob("top30.csv"),
    ]
    if not candidates:
        raise FileNotFoundError(f"No Top30/ADMET drug CSV found under {basic_root}")
    return str(candidates[0])


if __name__ == "__main__":
    raise SystemExit(main())
