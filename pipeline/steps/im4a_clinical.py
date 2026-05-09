from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipeline.utils.stats_utils import chi_square, continuous_tests, logrank_by_cluster


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    image = config.get("image_modal", {})
    analysis_cfg = config.get("analysis", {})
    out_root = Path(image.get("output_root", f"outputs/{disease}/0.Image_modal_{disease}"))
    out_dir = out_root / "step_im4a"
    clusters_csv = Path(image.get("clusters_csv", out_root / "step_im3" / "patient_clusters.csv"))
    clinical_csv = image.get("clinical_csv") or analysis_cfg.get("clinical_csv")

    if dry_run:
        return {"status": "dry_run", "clusters": str(clusters_csv), "clinical": str(clinical_csv)}
    if not clusters_csv.exists():
        raise FileNotFoundError(f"Missing clusters csv: {clusters_csv}")
    if not clinical_csv or not Path(clinical_csv).exists():
        raise FileNotFoundError(f"Missing clinical csv: {clinical_csv}")

    out_dir.mkdir(parents=True, exist_ok=True)
    clusters = pd.read_csv(clusters_csv)
    clinical = pd.read_csv(clinical_csv)
    left_key = image.get("cluster_id_column", "patient_id")
    right_key = analysis_cfg.get("clinical_id_column", left_key)
    merged = clusters.merge(clinical, left_on=left_key, right_on=right_key, how="inner")
    merged.to_csv(out_dir / "cluster_clinical_merged.csv", index=False)

    rows: list[dict] = []
    for col in analysis_cfg.get("clinical_vars", []):
        if col in merged.columns:
            rows.append(chi_square(merged, "cluster", col))
    for col in analysis_cfg.get("continuous_vars", []):
        if col in merged.columns:
            rows.extend(continuous_tests(merged, "cluster", col))
    for gene in analysis_cfg.get("driver_genes", []):
        for col in [f"{gene}_mut", gene]:
            if col in merged.columns:
                rows.append(chi_square(merged, "cluster", col))
                break

    survival = None
    surv_cfg = analysis_cfg.get("survival", {})
    if surv_cfg.get("time_col") in merged.columns and surv_cfg.get("event_col") in merged.columns:
        survival = logrank_by_cluster(merged, surv_cfg["time_col"], surv_cfg["event_col"], "cluster")
        rows.append({"variable": "overall_survival", **survival})

    tests = pd.DataFrame(rows)
    tests.to_csv(out_dir / "cluster_statistical_tests.csv", index=False)
    summary = {"n_merged": int(len(merged)), "n_tests": int(len(tests)), "survival": survival}
    (out_dir / "clinical_analysis_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"status": "completed", **summary}

