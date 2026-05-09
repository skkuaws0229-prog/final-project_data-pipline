#!/usr/bin/env python3
"""
Build BRCA Step4 model summary tables from the latest multicancer rerun artifacts.

Outputs:
  - 20260428_new_BRCA_data/brca_model_performance_summary.csv
  - 20260428_new_BRCA_data/brca_model_performance_summary.md
  - 20260428_new_BRCA_data/brca_model_performance_detailed.csv
  - 20260428_new_BRCA_data/copied_source_manifest.csv
  - 20260428_new_BRCA_data/README.md

It also copies the exact source files used for the summary:
  - metrics.json
  - split_info.json
"""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
SOURCE_ROOT = (
    WORKSPACE
    / "20260415_preproject_choi_protocol_v1_bisotest-1"
    / "20260415_preproject_choi_protocol_v1_bisotest"
    / "results"
    / "20260424_multicancer_stad_protocol_rerun"
    / "step4_models"
    / "fs_a_stad_baseline"
)
OUTPUT_ROOT = WORKSPACE / "20260428_new_BRCA_data"
COPIED_ROOT = OUTPUT_ROOT / "copied_sources"

FAMILY_DIRS = {
    "ML": "ml_step4_1",
    "DL": "dl_step4_2_7model_full",
    "Graph": "graph_step4_3_2model_full",
}
TRACK_LABELS = {
    "2A_numeric": "2A",
    "2B_numeric_smiles": "2B",
    "2C_numeric_smiles_context": "2C",
}
EVAL_MODES = ("cv", "groupcv", "scaffoldcv")


def fmt(value: float | None, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NA"
    return f"{value:.{digits}f}"


def load_json(path: Path) -> dict | list:
    with path.open() as fh:
        return json.load(fh)


def copy_used_file(path: Path) -> Path:
    rel = path.relative_to(WORKSPACE)
    dest = COPIED_ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest


def collect_model_rows() -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    manifest: list[dict] = []

    for family, family_dir in FAMILY_DIRS.items():
        family_root = SOURCE_ROOT / family_dir / "brca"
        for track_dir, phase in TRACK_LABELS.items():
            track_root = family_root / track_dir
            if not track_root.exists():
                continue

            for model_dir in sorted(p for p in track_root.iterdir() if p.is_dir()):
                row = {
                    "phase": phase,
                    "track": track_dir,
                    "family": family,
                    "model": model_dir.name,
                    "cv_spearman": None,
                    "groupcv_spearman": None,
                    "scaffoldcv_spearman": None,
                    "cv_overfit_gap": None,
                    "groupcv_overfit_gap": None,
                    "scaffoldcv_overfit_gap": None,
                    "cv_fold_std": None,
                    "groupcv_fold_std": None,
                    "scaffoldcv_fold_std": None,
                    "cv_folds": None,
                    "groupcv_folds": None,
                    "scaffoldcv_folds": None,
                }

                for eval_mode in EVAL_MODES:
                    eval_root = model_dir / eval_mode
                    metrics_path = eval_root / "metrics.json"
                    split_path = eval_root / "split_info.json"

                    if not metrics_path.exists():
                        continue

                    metrics = load_json(metrics_path)
                    split_info = load_json(split_path) if split_path.exists() else []

                    row[f"{eval_mode}_spearman"] = metrics["core_mean"]["spearman"]
                    row[f"{eval_mode}_overfit_gap"] = metrics["overfit"]["spearman_gap"]
                    row[f"{eval_mode}_fold_std"] = metrics["overfit"]["fold_std"]
                    row[f"{eval_mode}_folds"] = len(split_info) if isinstance(split_info, list) else None

                    copied_metrics = copy_used_file(metrics_path)
                    manifest.append(
                        {
                            "phase": phase,
                            "family": family,
                            "model": model_dir.name,
                            "eval_mode": eval_mode,
                            "file_type": "metrics",
                            "source_path": str(metrics_path),
                            "copied_path": str(copied_metrics),
                        }
                    )

                    if split_path.exists():
                        copied_split = copy_used_file(split_path)
                        manifest.append(
                            {
                                "phase": phase,
                                "family": family,
                                "model": model_dir.name,
                                "eval_mode": eval_mode,
                                "file_type": "split_info",
                                "source_path": str(split_path),
                                "copied_path": str(copied_split),
                            }
                        )

                generalization_values = [
                    row["groupcv_spearman"],
                    row["scaffoldcv_spearman"],
                ]
                generalization_values = [v for v in generalization_values if v is not None]
                row["generalization_mean"] = (
                    sum(generalization_values) / len(generalization_values)
                    if generalization_values
                    else None
                )
                row["primary_overfit_gap"] = row["groupcv_overfit_gap"]
                row["source_model_dir"] = str(model_dir)
                rows.append(row)

    return rows, manifest


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(rows: list[dict]) -> str:
    lines: list[str] = []
    lines.append("# BRCA Step4 Model Performance Summary")
    lines.append("")
    lines.append("- Source: latest BRCA results from `20260424_multicancer_stad_protocol_rerun`")
    lines.append("- Note: latest artifacts expose `cv` as 3-fold (`cv_fold1~3`), not a separate `5foldcv` artifact")
    lines.append("- Overfit gap = `train_spearman - test_spearman`; lower is better")
    lines.append("- Summary sort = `generalization_mean` desc, then `groupcv_spearman` desc, then `primary_overfit_gap` asc")
    lines.append("")

    for phase in ("2A", "2B", "2C"):
        phase_rows = [r for r in rows if r["phase"] == phase]
        phase_rows.sort(
            key=lambda r: (
                -1 if r["generalization_mean"] is None else -r["generalization_mean"],
                -1 if r["groupcv_spearman"] is None else -r["groupcv_spearman"],
                999 if r["primary_overfit_gap"] is None else r["primary_overfit_gap"],
                r["family"],
                r["model"],
            )
        )

        lines.append(f"## {phase}")
        lines.append("")
        lines.append(
            "| Family | Model | CV Spearman | GroupCV Spearman | ScaffoldCV Spearman | Overfit Gap (GroupCV) | Mean(Group+Scaffold) |"
        )
        lines.append(
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |"
        )
        for row in phase_rows:
            lines.append(
                f"| {row['family']} | {row['model']} | {fmt(row['cv_spearman'])} | "
                f"{fmt(row['groupcv_spearman'])} | {fmt(row['scaffoldcv_spearman'])} | "
                f"{fmt(row['primary_overfit_gap'])} | {fmt(row['generalization_mean'])} |"
            )
        lines.append("")

    return "\n".join(lines)


def write_readme(rows: list[dict], manifest: list[dict]) -> str:
    model_count = len(rows)
    file_count = len(manifest)
    return "\n".join(
        [
            "# 20260428_new_BRCA_data",
            "",
            "This folder contains the BRCA Step4 performance summary used to re-evaluate ensemble candidates.",
            "",
            "Contents:",
            "- `brca_model_performance_summary.csv`: summary table for ensemble screening",
            "- `brca_model_performance_summary.md`: markdown version grouped by 2A/2B/2C",
            "- `brca_model_performance_detailed.csv`: includes per-mode overfit gaps, fold std, and source dirs",
            "- `copied_source_manifest.csv`: exact files copied for traceability",
            "- `copied_sources/`: copied `metrics.json` and `split_info.json` files used by the summary",
            "",
            "Notes:",
            "- Latest BRCA step4 artifacts provide `cv`, `groupcv`, and `scaffoldcv`.",
            "- The `cv` artifact is a 3-fold split (`cv_fold1~3`), not a separate 5-fold artifact.",
            "- `Overfit Gap (GroupCV)` is computed from `metrics.json -> overfit -> spearman_gap`.",
            f"- Rows summarized: {model_count}",
            f"- Copied source files: {file_count}",
            "",
        ]
    )


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    COPIED_ROOT.mkdir(parents=True, exist_ok=True)

    rows, manifest = collect_model_rows()
    rows.sort(
        key=lambda r: (
            r["phase"],
            r["family"],
            -1 if r["generalization_mean"] is None else -r["generalization_mean"],
            -1 if r["groupcv_spearman"] is None else -r["groupcv_spearman"],
            r["model"],
        )
    )

    summary_rows = []
    for row in rows:
        summary_rows.append(
            {
                "phase": row["phase"],
                "family": row["family"],
                "model": row["model"],
                "cv_spearman": row["cv_spearman"],
                "groupcv_spearman": row["groupcv_spearman"],
                "scaffoldcv_spearman": row["scaffoldcv_spearman"],
                "overfit_gap_groupcv": row["primary_overfit_gap"],
                "mean_group_scaffold_spearman": row["generalization_mean"],
                "source_model_dir": row["source_model_dir"],
            }
        )

    write_csv(
        OUTPUT_ROOT / "brca_model_performance_summary.csv",
        summary_rows,
        [
            "phase",
            "family",
            "model",
            "cv_spearman",
            "groupcv_spearman",
            "scaffoldcv_spearman",
            "overfit_gap_groupcv",
            "mean_group_scaffold_spearman",
            "source_model_dir",
        ],
    )

    write_csv(
        OUTPUT_ROOT / "brca_model_performance_detailed.csv",
        rows,
        [
            "phase",
            "track",
            "family",
            "model",
            "cv_spearman",
            "groupcv_spearman",
            "scaffoldcv_spearman",
            "cv_overfit_gap",
            "groupcv_overfit_gap",
            "scaffoldcv_overfit_gap",
            "cv_fold_std",
            "groupcv_fold_std",
            "scaffoldcv_fold_std",
            "cv_folds",
            "groupcv_folds",
            "scaffoldcv_folds",
            "generalization_mean",
            "primary_overfit_gap",
            "source_model_dir",
        ],
    )

    write_csv(
        OUTPUT_ROOT / "copied_source_manifest.csv",
        manifest,
        [
            "phase",
            "family",
            "model",
            "eval_mode",
            "file_type",
            "source_path",
            "copied_path",
        ],
    )

    (OUTPUT_ROOT / "brca_model_performance_summary.md").write_text(build_markdown(rows))
    (OUTPUT_ROOT / "README.md").write_text(write_readme(rows, manifest))

    print(f"Output folder: {OUTPUT_ROOT}")
    print(f"Summary rows: {len(summary_rows)}")
    print(f"Copied files: {len(manifest)}")


if __name__ == "__main__":
    main()
