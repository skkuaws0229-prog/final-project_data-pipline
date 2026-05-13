from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pipeline.utils.image_modal_sagemaker import (
    ensure_image_defaults,
    launch_wsi_download,
    s3_object_count,
)


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    execution = config.get("execution", {})
    image = config.setdefault("image_modal", {})
    if image.get("enabled", True) is False:
        return {"status": "skipped", "reason": "image_modal.enabled=false"}

    wsi_limit = int(image.get("wsi_limit", execution.get("wsi_limit", 50)) or 50)
    out_root = Path(image.get("output_root", f"./{disease}_pipeline/outputs/image_modal"))
    out_dir = out_root / "step_im1"
    manifest_path = out_dir / "wsi_manifest.json"
    embedding_root = image.get("embedding_root")
    s3_embedding_root = image.get("s3_embedding_root")
    roots = ensure_image_defaults(config)
    s3_raw_wsi_root = roots["s3_raw_wsi_root"]

    if dry_run:
        return {
            "status": "dry_run",
            "wsi_limit": wsi_limit,
            "embedding_root": str(embedding_root or ""),
            "s3_embedding_root": str(s3_embedding_root or ""),
            "s3_raw_wsi_root": s3_raw_wsi_root,
            "auto_launch": bool(image.get("auto_launch", False)),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    local_files = []
    if embedding_root and Path(embedding_root).exists():
        local_files = [str(p) for p in sorted(Path(embedding_root).rglob("*.parquet"))[:wsi_limit]]

    s3_files = []
    if not local_files and s3_embedding_root:
        result = subprocess.run(
            ["aws", "s3", "ls", s3_embedding_root.rstrip("/") + "/", "--recursive"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                key = line.split()[-1] if line.split() else ""
                if key.endswith(".parquet"):
                    s3_files.append(key)
                if len(s3_files) >= wsi_limit:
                    break

    raw_wsi_count = s3_object_count(s3_raw_wsi_root, suffixes=(".svs", ".SVS"), limit=wsi_limit)
    launch = None
    if raw_wsi_count < wsi_limit and image.get("auto_launch", False):
        launch = launch_wsi_download(config, dry_run=False)

    manifest = {
        "disease": disease,
        "wsi_limit": wsi_limit,
        "s3_raw_wsi_root": s3_raw_wsi_root,
        "raw_wsi_count": raw_wsi_count,
        "embedding_root": str(embedding_root or ""),
        "s3_embedding_root": str(s3_embedding_root or ""),
        "local_embedding_files": local_files,
        "s3_embedding_files": s3_files,
        "launch": launch,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if local_files or s3_files or raw_wsi_count >= wsi_limit:
        status = "completed"
    elif launch and launch.get("status") in {"launched", "already_running"}:
        status = "pending"
    else:
        status = "pending"
    return {
        "status": status,
        "manifest": str(manifest_path),
        "n_local_embedding_files": len(local_files),
        "n_s3_embedding_files": len(s3_files),
        "raw_wsi_count": raw_wsi_count,
        "launch": launch,
    }
