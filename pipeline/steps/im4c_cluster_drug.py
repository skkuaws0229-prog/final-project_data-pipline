from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    image = config.get("image_modal", {})
    out_root = Path(image.get("output_root", f"outputs/{disease}/0.Image_modal_{disease}"))
    out_dir = out_root / "step_im4c"
    clusters_csv = Path(image.get("clusters_csv", out_root / "step_im3" / "patient_clusters.csv"))
    top30_csv = config.get("drug", {}).get("top30_csv")

    if dry_run:
        return {"status": "dry_run", "clusters": str(clusters_csv), "top30": str(top30_csv)}
    if not clusters_csv.exists():
        raise FileNotFoundError(f"Missing clusters csv: {clusters_csv}")
    if not top30_csv or not Path(top30_csv).exists():
        raise FileNotFoundError(f"Missing top30 drug csv: {top30_csv}")

    out_dir.mkdir(parents=True, exist_ok=True)
    clusters = pd.read_csv(clusters_csv)
    top30 = pd.read_csv(top30_csv).head(30)
    drug_col = _first_existing(top30, ["drug_name", "Drug", "drug", "name", "canonical_drug_id"]) or top30.columns[0]
    target_col = _first_existing(top30, ["target", "targets", "Target", "pathway", "moa"])

    rows = []
    for cluster_id in sorted(clusters["cluster"].dropna().unique()):
        n_patients = int((clusters["cluster"] == cluster_id).sum())
        for rank, drug in top30.iterrows():
            target = str(drug[target_col]) if target_col else ""
            rows.append(
                {
                    "cluster": int(cluster_id),
                    "n_patients": n_patients,
                    "drug_rank": int(rank) + 1,
                    "drug_name": drug[drug_col],
                    "target_or_pathway": target,
                    "linkage_rationale": _rationale(target, config.get("analysis", {}).get("driver_genes", [])),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / "cluster_drug_hypotheses.csv", index=False)
    summary = {"n_cluster_drug_links": int(len(out)), "n_drugs": int(len(top30)), "n_clusters": int(clusters["cluster"].nunique())}
    (out_dir / "cluster_drug_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"status": "completed", **summary}


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def _rationale(target: str, drivers: list[str]) -> str:
    text = target.upper()
    hits = [g for g in drivers if g.upper() in text]
    if hits:
        return "Direct/near-direct overlap with " + ", ".join(hits)
    return "Prioritized by baseline drug score; review pathway-level fit for this cluster."

