from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd
try:
    from scipy.stats import fisher_exact
except Exception:  # pragma: no cover - optional dependency
    fisher_exact = None

BACKGROUND_GENE_COUNT = 20000


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    image = config.get("image_modal", {})
    out_root = Path(image.get("output_root", f"./{disease}_pipeline/outputs/image_modal"))
    out_dir = out_root / "step_im4c"
    scored_dir = out_root / "step_im4"
    clusters_csv = Path(image.get("clusters_csv", out_root / "step_im3" / "patient_clusters.csv"))
    top30_csv = config.get("drug", {}).get("top30_csv")
    if not top30_csv:
        project_root = Path(config.get("project_root", f"./{disease}_pipeline"))
        for candidate in [
            project_root / "outputs/final_selection/admet_filtered_top15.csv",
            project_root / "outputs/final_selection/selected_drugs_top_n.csv",
        ]:
            if candidate.exists():
                top30_csv = str(candidate)
                break

    if dry_run:
        return {"status": "dry_run", "clusters": str(clusters_csv), "top30": str(top30_csv)}
    if not clusters_csv.exists():
        if image.get("skip_if_missing", True):
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = {"status": "pending", "reason": f"Missing clusters csv: {clusters_csv}"}
            (out_dir / "cluster_drug_pending.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            return summary
        raise FileNotFoundError(f"Missing clusters csv: {clusters_csv}")
    if not top30_csv or not Path(top30_csv).exists():
        if image.get("skip_if_missing", True):
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = {"status": "pending", "reason": f"Missing top30 drug csv: {top30_csv}"}
            (out_dir / "cluster_drug_pending.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            return summary
        raise FileNotFoundError(f"Missing top30 drug csv: {top30_csv}")

    out_dir.mkdir(parents=True, exist_ok=True)
    scored_dir.mkdir(parents=True, exist_ok=True)
    clusters = pd.read_csv(clusters_csv)
    top30 = pd.read_csv(top30_csv).head(30)
    drug_col = _first_existing(top30, ["drug_name", "Drug", "drug", "name", "canonical_drug_id"]) or top30.columns[0]
    target_col = _best_target_column(top30, ["putative_target", "drug__target_list", "target", "targets", "Target", "pathway", "pathway_name", "moa"])
    marker_source, marker_by_cluster = _load_cluster_marker_genes(config, clusters)

    rows = []
    for cluster_id in sorted(clusters["cluster"].dropna().unique()):
        cluster_id_int = int(cluster_id)
        n_patients = int((clusters["cluster"] == cluster_id).sum())
        cluster_genes = marker_by_cluster.get(cluster_id_int, [])
        for rank, drug in top30.iterrows():
            target = str(drug[target_col]) if target_col else ""
            drug_targets = _parse_targets(target)
            score = _confidence(cluster_genes, drug_targets)
            rows.append(
                {
                    "cluster": cluster_id_int,
                    "cluster_id": cluster_id_int,
                    "n_patients": n_patients,
                    "drug_rank": int(rank) + 1,
                    "drug_name": drug[drug_col],
                    "target_or_pathway": target,
                    "linkage_rationale": _rationale(target, config.get("analysis", {}).get("driver_genes", [])),
                    "confidence_score": score["confidence_score"],
                    "confidence_grade": score["confidence_grade"],
                    "overlap_genes": ";".join(score["overlap_genes"]),
                    "jaccard": score["jaccard"],
                    "p_value": score["p_value"],
                    "link_method": score["link_method"],
                    "cluster_gene_source": marker_source,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "cluster_drug_hypotheses.csv", index=False)
    scored_path = scored_dir / "im4c_cluster_drug_links_scored.csv"
    out.to_csv(scored_path, index=False)
    _write_confidence_summary(scored_dir / "im4c_confidence_summary.md", out, marker_source)
    summary = {
        "n_cluster_drug_links": int(len(out)),
        "n_drugs": int(len(top30)),
        "n_clusters": int(clusters["cluster"].nunique()),
        "scored_links_csv": str(scored_path),
        "confidence_method": marker_source,
    }
    (out_dir / "cluster_drug_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"status": "completed", **summary}


def _best_target_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        col = _first_existing(df, [candidate])
        if col and df[col].notna().any() and df[col].astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA}).notna().any():
            return col
    return _first_existing(df, candidates)


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def _load_cluster_marker_genes(config: dict, clusters: pd.DataFrame) -> tuple[str, dict[int, list[str]]]:
    image = config.get("image_modal", {})
    marker_csv = image.get("cluster_marker_genes_csv")
    out: dict[int, list[str]] = {}
    if marker_csv and Path(marker_csv).exists():
        df = pd.read_csv(marker_csv)
        cluster_col = _first_existing(df, ["cluster", "cluster_id"])
        gene_col = _first_existing(df, ["gene", "gene_symbol", "marker_gene"])
        if cluster_col and gene_col:
            for cid, grp in df.groupby(cluster_col):
                out[int(cid)] = sorted({_clean_gene(g) for g in grp[gene_col].dropna() if _clean_gene(g)})
            return "cluster_marker_genes_csv", out
    fallback = sorted({_clean_gene(g) for g in config.get("analysis", {}).get("driver_genes", []) if _clean_gene(g)})
    for cid in sorted(clusters["cluster"].dropna().unique()):
        out[int(cid)] = fallback
    return "fallback_analysis_driver_genes_no_cluster_deg_available", out


def _clean_gene(value: object) -> str:
    token = str(value).upper().strip()
    token = re.sub(r"[^A-Z0-9]+", "", token)
    return token


def _parse_targets(text: str) -> list[str]:
    tokens = []
    for part in re.split(r"[,;/|]+|\band\b", str(text), flags=re.IGNORECASE):
        gene = _clean_gene(part)
        if gene and gene not in {"NAN", "NONE", "OTHER", "DNA", "REPLICATION", "SIGNALING", "PROTEIN", "STABILITY", "DEGRADATION"}:
            tokens.append(gene)
    return sorted(set(tokens))


def _confidence(cluster_genes: list[str], drug_targets: list[str]) -> dict:
    cset = set(cluster_genes)
    dset = set(drug_targets)
    overlap = sorted(cset & dset)
    union = cset | dset
    jaccard = len(overlap) / len(union) if union else 0.0
    p_value = math.nan
    if fisher_exact and cset and dset:
        a = len(overlap)
        b = max(len(dset) - a, 0)
        c = max(len(cset) - a, 0)
        d = max(BACKGROUND_GENE_COUNT - a - b - c, 0)
        try:
            _, p_value = fisher_exact([[a, b], [c, d]], alternative="greater")
        except Exception:
            p_value = math.nan
    confidence_score = float(jaccard)
    if confidence_score > 0.3 or (not math.isnan(p_value) and p_value < 0.01):
        grade = "A"
    elif confidence_score > 0.1:
        grade = "B"
    else:
        grade = "C"
    return {
        "confidence_score": round(confidence_score, 6),
        "confidence_grade": grade,
        "overlap_genes": overlap,
        "jaccard": round(float(jaccard), 6),
        "p_value": p_value,
        "link_method": "target_overlap_jaccard_fisher",
    }


def _write_confidence_summary(path: Path, out: pd.DataFrame, marker_source: str) -> None:
    grade_counts = out["confidence_grade"].value_counts().sort_index().rename_axis("grade").reset_index(name="n_links")
    lines = [
        "# IM4c Confidence Summary",
        "",
        f"- marker_gene_source: {marker_source}",
        "- confidence_score: Jaccard overlap between cluster genes and parsed drug targets/pathways.",
        "- confidence_grade: A if score > 0.3 or p < 0.01; B if 0.1 < score <= 0.3; C otherwise.",
        "- Note: when cluster-specific DEG/marker genes are unavailable, the pipeline uses analysis.driver_genes as a conservative fallback and records this in cluster_gene_source.",
        "",
        grade_counts.to_markdown(index=False),
        "",
        "Top scored links:",
        out.sort_values(["confidence_score", "drug_rank"], ascending=[False, True]).head(20).to_markdown(index=False),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _rationale(target: str, drivers: list[str]) -> str:
    text = target.upper()
    hits = [g for g in drivers if g.upper() in text]
    if hits:
        return "Direct/near-direct overlap with " + ", ".join(hits)
    return "Prioritized by baseline drug score; review pathway-level fit for this cluster."
