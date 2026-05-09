from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def tcga_patient_barcode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", value.upper())
    return match.group(1) if match else None


def embedding_columns(df: pd.DataFrame) -> list[str]:
    cols = [c for c in df.columns if c.startswith("emb_")]
    if cols:
        return sorted(cols, key=lambda c: int(c.split("_", 1)[1]))
    numeric = df.select_dtypes(include=["number"]).columns.tolist()
    return [c for c in numeric if not c.lower().endswith(("cluster", "label"))]


def merge_embedding_parquets(
    embedding_root: str | Path,
    output_npy: str | Path,
    metadata_csv: str | Path | None = None,
    patient_level: bool = True,
    id_column: str | None = None,
    pattern: str = "all_slide_embeddings_20260430_v1.parquet",
) -> dict[str, Any]:
    root = Path(embedding_root)
    files = sorted(root.rglob(pattern))
    if not files:
        raise FileNotFoundError(f"No embedding parquet files matching {pattern} under {root}")

    frames: list[pd.DataFrame] = []
    for path in files:
        frame = pd.read_parquet(path)
        frame["source_part"] = path.parent.name
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    emb_cols = embedding_columns(df)
    if not emb_cols:
        raise ValueError("No embedding columns found")

    id_col = id_column or ("slide_id" if "slide_id" in df.columns else df.columns[0])
    if patient_level:
        df["patient_id"] = df[id_col].map(tcga_patient_barcode).fillna(df[id_col].astype(str))
        meta = df.groupby("patient_id", as_index=False)[emb_cols].mean()
        if "slide_id" in df.columns:
            meta["n_slides"] = meta["patient_id"].map(df.groupby("patient_id")["slide_id"].nunique())
        matrix = meta[emb_cols].to_numpy(dtype=np.float32)
    else:
        meta = df.copy()
        matrix = df[emb_cols].to_numpy(dtype=np.float32)

    output_npy = Path(output_npy)
    output_npy.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_npy, matrix)
    if metadata_csv is not None:
        Path(metadata_csv).parent.mkdir(parents=True, exist_ok=True)
        keep = [c for c in ["patient_id", id_col, "slide_id", "source_part", "n_slides"] if c in meta.columns]
        meta[keep].to_csv(metadata_csv, index=False)

    qc = validate_embedding_matrix(matrix)
    qc.update({"shape": list(matrix.shape), "source_files": [str(p) for p in files]})
    output_npy.with_suffix(".qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
    return qc


def validate_embedding_matrix(matrix: np.ndarray) -> dict[str, int]:
    return {
        "nan_count": int(np.isnan(matrix).sum()),
        "inf_count": int(np.isinf(matrix).sum()),
        "n_rows": int(matrix.shape[0]),
        "n_dims": int(matrix.shape[1]) if matrix.ndim == 2 else 0,
    }

