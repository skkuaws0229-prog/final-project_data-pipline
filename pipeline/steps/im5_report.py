from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run(config: dict, dry_run: bool = False) -> dict:
    disease = config["disease"]["name"]
    image = config.get("image_modal", {})
    out_root = Path(image.get("output_root", f"./{disease}_pipeline/outputs/image_modal"))
    out_dir = out_root / "step_im5"
    if dry_run:
        return {"status": "dry_run", "output": str(out_dir / "image_modal_summary.md")}
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [f"# {disease} Image Modal Summary", ""]
    for rel, title in [
        ("step_im2/embedding_qc.json", "Embedding QC"),
        ("step_im3/clustering_summary.json", "Clustering"),
        ("step_im4a/clinical_analysis_summary.json", "Clinical Analysis"),
        ("step_im4c/cluster_drug_summary.json", "Cluster-Drug Linkage"),
    ]:
        path = out_root / rel
        lines.append(f"## {title}")
        if path.exists():
            lines.append("```json")
            lines.append(json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2))
            lines.append("```")
        else:
            lines.append("Not available.")
        lines.append("")
    tests = out_root / "step_im4a" / "cluster_statistical_tests.csv"
    if tests.exists():
        df = pd.read_csv(tests)
        lines.extend(["## Statistical Tests", df.to_markdown(index=False), ""])
    report = out_dir / "image_modal_summary.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "completed", "report": str(report)}
