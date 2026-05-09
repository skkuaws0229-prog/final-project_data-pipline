#!/usr/bin/env python3
"""Cluster BRCA WSI image embeddings and connect clusters to Top30 drug pathways.

Available inputs in this workspace are TCGA slide embeddings plus GDSC drug
annotations. Clinical, mutation, subtype, and pathway-enrichment files can be
provided later with CLI options; if absent, the report records that limitation
instead of pretending those annotations were analyzed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--embedding-npy",
        default="output/embeddings_mid/shard00_merged/all_slide_embeddings_shard00_merged.npy",
    )
    parser.add_argument(
        "--manifest",
        default="output/embeddings_mid/shard00_merged/all_slide_embeddings_shard00_merged_manifest.csv",
    )
    parser.add_argument("--top30", default="brca_data/brca_directive_top30_tiered_candidates.csv")
    parser.add_argument("--drug-annotation", default="brca_data/gdsc2_drug_annotation_master_20260406.parquet")
    parser.add_argument("--clinical", default=None)
    parser.add_argument("--mutation", default=None)
    parser.add_argument("--subtype", default=None)
    parser.add_argument("--output-dir", default="results/brca_image_clustering_20260430_v1")
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def tcga_case_id(slide_id: str) -> str:
    parts = str(slide_id).split("-")
    return "-".join(parts[:3]) if len(parts) >= 3 and parts[0] == "TCGA" else str(slide_id)


def read_table(path: Optional[str]) -> Optional[pd.DataFrame]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    if p.suffix.lower() == ".parquet":
        return pd.read_parquet(p)
    if p.suffix.lower() in {".tsv", ".txt"}:
        return pd.read_csv(p, sep="\t")
    return pd.read_csv(p)


def pick_patient_col(df: pd.DataFrame) -> Optional[str]:
    candidates = [
        "case_id",
        "patient_id",
        "submitter_id",
        "bcr_patient_barcode",
        "barcode",
        "sample_id",
        "TCGA_ID",
    ]
    lower_map = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]
    for c in df.columns:
        if "barcode" in c.lower() or "patient" in c.lower() or "case" in c.lower():
            return c
    return None


def attach_annotation(cluster_df: pd.DataFrame, anno: Optional[pd.DataFrame], prefix: str) -> tuple[pd.DataFrame, dict]:
    if anno is None:
        return cluster_df, {"status": "missing", "rows": 0, "patient_col": None, "matched_cases": 0}
    patient_col = pick_patient_col(anno)
    if patient_col is None:
        return cluster_df, {"status": "no_patient_column_detected", "rows": len(anno), "patient_col": None, "matched_cases": 0}
    anno = anno.copy()
    anno["tcga_case_id"] = anno[patient_col].astype(str).str.extract(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", expand=False)
    if anno["tcga_case_id"].isna().all():
        anno["tcga_case_id"] = anno[patient_col].astype(str)
    rename = {
        c: f"{prefix}_{c}"
        for c in anno.columns
        if c not in {patient_col, "tcga_case_id"}
    }
    anno = anno.rename(columns=rename)
    merged = cluster_df.merge(anno.drop_duplicates("tcga_case_id"), on="tcga_case_id", how="left")
    matched = int(merged[[c for c in merged.columns if c.startswith(prefix + "_")]].notna().any(axis=1).sum())
    return merged, {
        "status": "attached",
        "rows": len(anno),
        "patient_col": patient_col,
        "matched_cases": matched,
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_clustering(x: np.ndarray, random_state: int) -> tuple[pd.DataFrame, dict, np.ndarray, np.ndarray]:
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    n_components = min(50, x_scaled.shape[0] - 1, x_scaled.shape[1])
    pca = PCA(n_components=n_components, random_state=random_state)
    x_pca = pca.fit_transform(x_scaled)

    rows = []
    labels_by_k = {}
    for k in [3, 4, 5]:
        labels = KMeans(n_clusters=k, n_init=50, random_state=random_state).fit_predict(x_pca)
        labels_by_k[k] = labels
        rows.append(
            {
                "method": "kmeans",
                "k": k,
                "silhouette": float(silhouette_score(x_pca, labels)),
                "calinski_harabasz": float(calinski_harabasz_score(x_pca, labels)),
                "davies_bouldin": float(davies_bouldin_score(x_pca, labels)),
            }
        )

    z = linkage(x_pca, method="ward")
    for k in [3, 4, 5]:
        labels = fcluster(z, t=k, criterion="maxclust") - 1
        rows.append(
            {
                "method": "hierarchical_ward",
                "k": k,
                "silhouette": float(silhouette_score(x_pca, labels)),
                "calinski_harabasz": float(calinski_harabasz_score(x_pca, labels)),
                "davies_bouldin": float(davies_bouldin_score(x_pca, labels)),
            }
        )

    metrics = pd.DataFrame(rows).sort_values(["silhouette", "calinski_harabasz"], ascending=[False, False])
    best = metrics.iloc[0].to_dict()
    best_k = int(best["k"])
    if best["method"] == "kmeans":
        best_labels = labels_by_k[best_k]
    else:
        best_labels = fcluster(z, t=best_k, criterion="maxclust") - 1

    return metrics, best, best_labels, x_pca


def plot_pca(cluster_df: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=cluster_df,
        x="pca_1",
        y="pca_2",
        hue="best_cluster",
        style="part",
        palette="tab10",
        s=54,
        linewidth=0,
    )
    plt.title("BRCA WSI Embedding Clusters (PCA)")
    plt.tight_layout()
    plt.savefig(output_dir / "brca_image_clusters_pca_20260430_v1.png", dpi=180)
    plt.close()


def plot_dendrogram(x_pca: np.ndarray, output_dir: Path) -> None:
    z = linkage(x_pca, method="ward")
    plt.figure(figsize=(12, 5))
    dendrogram(z, no_labels=True, color_threshold=None)
    plt.title("BRCA WSI Embedding Hierarchical Clustering")
    plt.tight_layout()
    plt.savefig(output_dir / "brca_image_clusters_dendrogram_20260430_v1.png", dpi=180)
    plt.close()


def summarize_clusters(cluster_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cluster_df.groupby("best_cluster")
        .agg(
            n_slides=("slide_id", "count"),
            n_cases=("tcga_case_id", "nunique"),
            parts=("part", lambda s: ",".join(sorted(s.astype(str).unique()))),
            pc1_mean=("pca_1", "mean"),
            pc2_mean=("pca_2", "mean"),
            pc3_mean=("pca_3", "mean"),
        )
        .reset_index()
    )
    return summary


def link_top30_drugs(top30: pd.DataFrame, drug_anno: pd.DataFrame) -> pd.DataFrame:
    anno = drug_anno.copy()
    anno["DRUG_ID"] = pd.to_numeric(anno["DRUG_ID"], errors="coerce")
    top = top30.copy()
    top["canonical_drug_id"] = pd.to_numeric(top["canonical_drug_id"], errors="coerce")
    merged = top.merge(
        anno,
        left_on="canonical_drug_id",
        right_on="DRUG_ID",
        how="left",
    )
    keep = [
        "rank",
        "canonical_drug_id",
        "drug_name",
        "drug_level_score",
        "confidence_grade",
        "PUTATIVE_TARGET",
        "PATHWAY_NAME",
        "tier_name",
        "tier_rationale",
    ]
    return merged[[c for c in keep if c in merged.columns]]


def write_report(
    output_dir: Path,
    metrics: pd.DataFrame,
    best: dict,
    cluster_summary: pd.DataFrame,
    annotation_status: dict,
    top30_linked: pd.DataFrame,
) -> None:
    pathway_counts = (
        top30_linked["PATHWAY_NAME"].fillna("unknown").value_counts().head(12).reset_index()
        if "PATHWAY_NAME" in top30_linked.columns
        else pd.DataFrame()
    )
    if not pathway_counts.empty:
        pathway_counts.columns = ["pathway", "n_top30_drugs"]

    report = [
        "# BRCA Image Embedding Clustering Report",
        "",
        "## Summary",
        "",
        f"- Best clustering: {best['method']}, k={int(best['k'])}, silhouette={best['silhouette']:.4f}",
        "- Input image embeddings: 284 slides x 1,536 dimensions",
        "- TCGA clinical/mutation/subtype/pathway annotation files were not found locally unless marked as attached below.",
        "",
        "## Annotation Status",
        "",
        pd.DataFrame(annotation_status).T.to_markdown(),
        "",
        "## Clustering Metrics",
        "",
        metrics.to_markdown(index=False),
        "",
        "## Cluster Summary",
        "",
        cluster_summary.to_markdown(index=False),
        "",
        "## Top30 Drug Target/Pathway Link",
        "",
        "Current linkage is target/pathway-level only, because patient-level drug response labels are GDSC cell-line based while image clusters are TCGA patient-slide based.",
        "",
        pathway_counts.to_markdown(index=False) if not pathway_counts.empty else "No pathway annotation available for Top30 drugs.",
        "",
        "## Cluster-Specific Drug Interpretation",
        "",
        "Cluster-specific drug assignment needs clinical/mutation/subtype/pathway enrichment per TCGA case. Once those files are attached, this script can summarize enrichment per cluster and map enriched pathways to the Top30 drug target/pathway table.",
        "",
    ]
    (output_dir / "brca_image_clustering_report_20260430_v1.md").write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    x = np.load(args.embedding_npy)
    manifest = pd.read_csv(args.manifest)
    if x.shape != (len(manifest), 1536):
        raise ValueError(f"Expected manifest rows x 1536 to match embeddings, got {x.shape}, manifest={len(manifest)}")
    if np.isnan(x).any() or np.isinf(x).any():
        raise ValueError("Embedding contains NaN or Inf")

    metrics, best, labels, x_pca = run_clustering(x, args.random_state)
    metrics.to_csv(output_dir / "cluster_metrics_k3_k4_k5_20260430_v1.csv", index=False)
    write_json(output_dir / "best_cluster_config_20260430_v1.json", best)

    cluster_df = manifest.copy()
    cluster_df["tcga_case_id"] = cluster_df["slide_id"].map(tcga_case_id)
    cluster_df["best_cluster"] = [f"C{int(v)}" for v in labels]
    for i in range(min(10, x_pca.shape[1])):
        cluster_df[f"pca_{i+1}"] = x_pca[:, i]

    anno_status = {}
    for key, path in [("clinical", args.clinical), ("mutation", args.mutation), ("subtype", args.subtype)]:
        cluster_df, anno_status[key] = attach_annotation(cluster_df, read_table(path), key)

    cluster_df.to_csv(output_dir / "slide_cluster_assignments_20260430_v1.csv", index=False)
    cluster_summary = summarize_clusters(cluster_df)
    cluster_summary.to_csv(output_dir / "cluster_summary_20260430_v1.csv", index=False)
    plot_pca(cluster_df, output_dir)
    plot_dendrogram(x_pca, output_dir)

    top30 = pd.read_csv(args.top30)
    drug_anno = pd.read_parquet(args.drug_annotation)
    top30_linked = link_top30_drugs(top30, drug_anno)
    top30_linked.to_csv(output_dir / "top30_drug_target_pathway_link_20260430_v1.csv", index=False)

    write_report(output_dir, metrics, best, cluster_summary, anno_status, top30_linked)
    print("[done]", output_dir)
    print("best", best)
    print(cluster_summary.to_string(index=False))


if __name__ == "__main__":
    main()
