from __future__ import annotations

import json
import random
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
    seed = int(config.get("random_seed", 42) or 42)
    random.seed(seed)
    np.random.seed(seed)
    image = config.get("image_modal", {})
    out_root = Path(image.get("output_root", f"./{disease}_pipeline/outputs/image_modal"))
    out_dir = out_root / "step_im3"
    merged_npy = Path(image.get("merged_npy", out_root / "step_im2" / f"all_patient_embeddings_{disease.lower()}_merged.npy"))
    metadata_csv = image.get("embedding_metadata_csv")
    k_values = _k_values(config)

    if dry_run:
        return {"status": "dry_run", "input": str(merged_npy), "k_values": k_values, "random_seed": seed}
    if not merged_npy.exists():
        if image.get("skip_if_missing", True):
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = {"status": "pending", "reason": f"Missing merged embedding npy: {merged_npy}"}
            (out_dir / "clustering_pending.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            return summary
        raise FileNotFoundError(f"Missing merged embedding npy: {merged_npy}")

    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.load(merged_npy)
    if matrix.ndim != 2:
        raise ValueError(f"Embedding matrix must be 2D, got shape {matrix.shape}")
    scaled = StandardScaler().fit_transform(matrix)
    pca_xy = PCA(n_components=2, random_state=seed).fit_transform(scaled)

    results = []
    best = {"k": None, "silhouette": -1.0, "labels": None, "cluster_sizes": None}
    for k in k_values:
        if k < 2 or k >= len(matrix):
            continue
        labels = KMeans(n_clusters=int(k), random_state=seed, n_init=10).fit_predict(scaled)
        sil = float(silhouette_score(scaled, labels))
        cluster_sizes = [int((labels == i).sum()) for i in range(int(k))]
        row = {
            "k": int(k),
            "silhouette": round(sil, 6),
            "cluster_sizes": json.dumps(cluster_sizes),
            "min_cluster": min(cluster_sizes),
            "max_cluster": max(cluster_sizes),
            "imbalance_ratio": round(max(cluster_sizes) / max(min(cluster_sizes), 1), 2),
        }
        results.append(row)
        if sil > float(best["silhouette"]):
            best = {"k": int(k), "silhouette": sil, "labels": labels, "cluster_sizes": cluster_sizes}
    if best["labels"] is None:
        raise RuntimeError("No valid k produced clustering labels")

    results_df = pd.DataFrame(results)
    results_df.to_csv(out_dir / "im3_k_search_results.csv", index=False)
    results_df[["k", "silhouette", "cluster_sizes", "min_cluster", "max_cluster", "imbalance_ratio"]].to_csv(
        out_dir / "kmeans_silhouette.csv", index=False
    )
    _write_k_search_summary(out_dir / "im3_k_search_summary.md", results_df, best, seed)

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

    summary = {
        "best_k": best["k"],
        "best_silhouette": best["silhouette"],
        "n_patients": int(len(matrix)),
        "random_seed": seed,
        "k_values": k_values,
        "best_cluster_sizes": best["cluster_sizes"],
    }
    (out_dir / "clustering_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"status": "completed", **summary}


def _k_values(config: dict) -> list[int]:
    analysis = config.get("analysis", {})
    values = analysis.get("clustering_k_range") or analysis.get("k_values") or list(range(2, 9))
    if values != list(range(2, 9)):
        values = list(range(2, 9))
    return [int(k) for k in values]


def _write_k_search_summary(path: Path, results: pd.DataFrame, best: dict, seed: int) -> None:
    lines = [
        "# IM3 k Search Summary",
        "",
        f"- random_seed: {seed}",
        "- search_range: k=2..8",
        f"- best_k: {best['k']}",
        f"- best_silhouette: {best['silhouette']:.6f}",
        f"- best_cluster_sizes: {best['cluster_sizes']}",
        "",
        results.to_markdown(index=False),
        "",
        "Best k was selected by maximum silhouette score. Cluster size imbalance is reported for review but was not used as the primary optimizer.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_ids(metadata_csv: str | None, n: int) -> list[str]:
    if metadata_csv and Path(metadata_csv).exists():
        meta = pd.read_csv(metadata_csv)
        for col in ["patient_id", "patient_barcode", "Patient", "identifier"]:
            if col in meta.columns and len(meta) == n:
                return meta[col].astype(str).tolist()
    return [f"sample_{i:04d}" for i in range(n)]
