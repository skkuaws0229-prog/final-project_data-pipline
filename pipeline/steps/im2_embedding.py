from __future__ import annotations

from pathlib import Path

from pipeline.utils.embedding_utils import merge_embedding_parquets, validate_embedding_matrix


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"].lower()
    image = config.get("image_modal", {})
    model = config.get("model", {}).get("foundation_model", "").upper()
    out_root = Path(image.get("output_root", f"outputs/{disease}/0.Image_modal_{disease.upper()}"))
    out_dir = out_root / "step_im2"
    merged_npy = Path(image.get("merged_npy", out_dir / f"all_patient_embeddings_{disease}_merged.npy"))
    metadata_csv = Path(image.get("embedding_metadata_csv", out_dir / f"all_patient_embeddings_{disease}_metadata.csv"))

    if dry_run:
        return {"status": "dry_run", "foundation_model": model, "output": str(merged_npy)}

    if merged_npy.exists():
        import numpy as np

        qc = validate_embedding_matrix(np.load(merged_npy))
        return {"status": "reused_existing_embedding", "foundation_model": model, **qc}

    if model == "UNI2":
        root = image.get("embedding_root")
        if not root:
            raise ValueError("image_modal.embedding_root is required for UNI2 merge")
        qc = merge_embedding_parquets(root, merged_npy, metadata_csv, patient_level=True)
        return {"status": "completed", "foundation_model": model, **qc}

    raise NotImplementedError(
        f"{model} embedding extraction should be produced by the source scripts; configure image_modal.merged_npy to reuse it."
    )

