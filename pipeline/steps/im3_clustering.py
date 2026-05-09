from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    image = config.get("image_modal", {})
    out_root = Path(image.get("output_root", f"outputs/{disease}/0.Image_modal_{disease}"))
    out_dir = out_root / "step_im3"
    merged_npy = Path(image.get("merged_npy", out_root / "step_im2" / f"all_patient_embeddings_{disease.lower()}_merged.npy"))
    metadata_csv = image.get("embedding_metadata_csv")
    k_values = config.get("analysis", {}).get("k_values", [2, 3, 4, 5])

    if dry_run:
        return {"status": "dry_run", "input": str(merged_npy), "k_values": k_values}
    if not merged_npy.exists():
        raise FileNotFoundError(f"Missing merged embedding npy: {merged_npy}")

    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.load(merged_npy)
    if matrix.ndim != 2:
        raise ValueError(f"Embedding matrix must be 2D, got shape {matrix.shape}")
    scaled = StandardScaler().fit_transform(matrix)
    pca_xy = PCA(n_components=2, random_state=42).fit_transform(scaled)

    rows = []
    best = {"k": None, "silhouette": -1.0, "labels": None}
    for k in k_values:
        if k < 2 or k >= len(matrix):
            continue
        labels = KMeans(n_clusters=int(k), random_state=42, n_init=20).fit_predict(scaled)
        sil = float(silhouette_score(scaled, labels))
        rows.append({"k": int(k), "silhouette": sil})
        if sil > best["silhouette"]:
            best = {"k": int(k), "silhouette": sil, "labels": labels}
    if best["labels"] is None:
        raise RuntimeError("No valid k produced clustering labels")

    pd.DataFrame(rows).to_csv(out_dir / "kmeans_silhouette.csv", index=False)
    ids = _load_ids(metadata_csv, len(matrix))
    clusters = pd.DataFrame(
        {"patient_id": ids, "cluster": best["labels"].astype(int), "pca1": pca_xy[:, 0], "pca2": pca_xy[:, 1]}
    )
    clusters.to_csv(out_dir / "patient_clusters.csv", index=False)

    plt.figure(figsize=(7, 5.2))
    for cluster_id, grp in clusters.groupby("cluster"):
        plt.scatter(grp["pca1"], grp["pca2"], s=36, label=f"Cluster {cluster_id}")
    plt.title(f"{disease} embedding clusters (k={best['k']}, silhouette={best['silhouette']:.3f})")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "pca_clusters.png", dpi=180)
    plt.close()

    summary = {"best_k": best["k"], "best_silhouette": best["silhouette"], "n_patients": int(len(matrix))}
    (out_dir / "clustering_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"status": "completed", **summary}


def _load_ids(metadata_csv: str | None, n: int) -> list[str]:
    if metadata_csv and Path(metadata_csv).exists():
        meta = pd.read_csv(metadata_csv)
        for col in ["patient_id", "patient_barcode", "Patient", "identifier"]:
            if col in meta.columns and len(meta) == n:
                return meta[col].astype(str).tolist()
    return [f"sample_{i:04d}" for i in range(n)]

