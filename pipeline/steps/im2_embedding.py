from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pipeline.utils.embedding_utils import merge_embedding_parquets, validate_embedding_matrix
from pipeline.utils.image_modal_sagemaker import (
    ensure_image_defaults,
    launch_embedding,
    launch_tile_preprocessing,
    s3_object_count,
)


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"].lower()
    image = config.setdefault("image_modal", {})
    model = config.get("model", {}).get("foundation_model", "").upper()
    out_root = Path(image.get("output_root", f"./{disease.upper()}_pipeline/outputs/image_modal"))
    out_dir = out_root / "step_im2"
    merged_npy = Path(image.get("merged_npy", out_dir / f"all_patient_embeddings_{disease}_merged.npy"))
    metadata_csv = Path(image.get("embedding_metadata_csv", out_dir / f"all_patient_embeddings_{disease}_metadata.csv"))
    roots = ensure_image_defaults(config)

    if dry_run:
        return {
            "status": "dry_run",
            "foundation_model": model,
            "output": str(merged_npy),
            "s3_raw_wsi_root": roots["s3_raw_wsi_root"],
            "s3_tiles_root": roots["s3_tiles_root"],
            "s3_embedding_root": roots["s3_embedding_root"],
            "auto_launch": bool(image.get("auto_launch", False)),
        }

    if merged_npy.exists():
        import numpy as np

        qc = validate_embedding_matrix(np.load(merged_npy))
        return {"status": "reused_existing_embedding", "foundation_model": model, **qc}

    if model == "UNI2":
        root = image.get("embedding_root")
        s3_embedding_count = s3_object_count(roots["s3_embedding_root"], suffixes=(".parquet", ".npy"), limit=1)
        if not root and s3_embedding_count > 0:
            image["s3_embedding_root"] = roots["s3_embedding_root"]
            root = out_root / "s3_embedding_cache"
            root.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["aws", "s3", "sync", image["s3_embedding_root"].rstrip("/") + "/", str(root)],
                check=True,
            )
            if not any(Path(root).rglob("all_slide_embeddings_20260430_v1.parquet")):
                root = None
        if not root:
            wsi_limit = int(image.get("wsi_limit", config.get("execution", {}).get("wsi_limit", 100)) or 100)
            raw_wsi_count = s3_object_count(roots["s3_raw_wsi_root"], suffixes=(".svs", ".SVS"), limit=wsi_limit)
            tile_count = s3_object_count(roots["s3_tiles_root"], suffixes=(".h5", ".csv"), limit=1)
            launch = None
            reason = "image_modal.embedding_root or s3_embedding_root is required for UNI2 merge"
            if image.get("auto_launch", False):
                if raw_wsi_count < wsi_limit:
                    from pipeline.utils.image_modal_sagemaker import launch_wsi_download

                    launch = launch_wsi_download(config, dry_run=False)
                    reason = "raw WSI smoke/main download launched or already running"
                elif tile_count == 0:
                    launch = launch_tile_preprocessing(config, dry_run=False)
                    reason = "tile preprocessing launched or already running"
                else:
                    launch = launch_embedding(config, dry_run=False)
                    reason = "UNI2 embedding launched or already running"
            if image.get("skip_if_missing", True):
                out_dir.mkdir(parents=True, exist_ok=True)
                pending = {
                    "status": "pending",
                    "reason": reason,
                    "foundation_model": model,
                    "raw_wsi_count": raw_wsi_count,
                    "tile_count": tile_count,
                    "s3_embedding_count": s3_embedding_count,
                    "launch": launch,
                }
                (out_dir / "embedding_pending.json").write_text(json.dumps(pending, indent=2), encoding="utf-8")
                return pending
            raise ValueError("image_modal.embedding_root is required for UNI2 merge")
        qc = merge_embedding_parquets(root, merged_npy, metadata_csv, patient_level=True)
        return {"status": "completed", "foundation_model": model, **qc}

    raise NotImplementedError(
        f"{model} embedding extraction should be produced by the source scripts; configure image_modal.merged_npy to reuse it."
    )
