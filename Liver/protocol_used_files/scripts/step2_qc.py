#!/usr/bin/env python3
"""
Step 2 integrated QC for STAD FE inputs.

Adapted from:
  20260420_new_pre_project_biso_Colon/scripts/step2_qc.py

Input/output shapes (expectations):
  - labels.parquet: (N_pairs, 4) — sample_id, canonical_drug_id, ic50, binary_label
  - drug_features.parquet: (N_drugs, 5) — team4 schema
  - drug_target_mapping.parquet: (M, 2)
  - lincs_stad.parquet: (N_sigs, 12336)
  - lincs_stad_drug_level.parquet: (≤N_drugs, 12329)
  - depmap/depmap_crispr_long_stad.parquet: long DepMap CRISPR
  - stad_subtype_metadata.parquet: optional

Exit code 1 if any required file missing or critical schema failure.

중요: 이 QC는 Step 2 후속 단계(filter_stad_depmap_to_labels.py)가 생성한
data/depmap/depmap_crispr_long_stad.parquet 를 주 검증 대상으로 삼는다.

과거 이슈 (2026-04-21):
- curated_data/processed/depmap/... (1150 cells 원본)만 검증하면 "19 unmatched" 경고 나옴
- 이 경고를 "Colon도 비슷"이라고 넘기면 Step 3 FE에서 39% row loss 발생
- 실제 FE가 참조하는 경로는 data/depmap/ 이며, Step 2는 이 경로를 20 cells로 재필터링함
- QC는 "실제 FE 입력"을 검증해야 정확함
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="STAD project root (contains data/, curated_data/)",
    )
    p.add_argument(
        "--allow-missing-lincs",
        action="store_true",
        help="Do not fail if LINCS parquet outputs are absent (pre-LINCS smoke test).",
    )
    return p.parse_args()


def check_file(path: Path, name: str, report: dict) -> bool:
    if not path.exists():
        log(f"  MISSING: {name} ({path})")
        report["files"][name] = {"exists": False, "path": str(path)}
        return False
    sz = path.stat().st_size
    log(f"  OK {name}: {sz / 1024**2:.2f} MB")
    report["files"][name] = {"exists": True, "path": str(path), "size_bytes": sz}
    return True


def main() -> int:
    args = parse_args()
    root: Path = args.project_root.resolve()
    data_dir = root / "data"
    processed_depmap = root / "curated_data" / "processed" / "depmap"
    data_depmap = data_dir / "depmap"
    out_report = root / "reports" / "step2_integrated_qc_report.json"

    report: dict = {
        "timestamp": datetime.now().isoformat(),
        "project_root": str(root),
        "files": {},
        "schemas": {},
        "consistency": {},
        "issues": [],
        "warnings": [],
        "info": [],
        "passed": True,
    }

    depmap_pre_path = processed_depmap / "depmap_crispr_long_stad.parquet"
    depmap_post_path = data_depmap / "depmap_crispr_long_stad.parquet"

    files_to_check = {
        "labels": data_dir / "labels.parquet",
        "drug_features": data_dir / "drug_features.parquet",
        "drug_target_mapping": data_dir / "drug_target_mapping.parquet",
        "lincs_stad": data_dir / "lincs_stad.parquet",
        "lincs_stad_drug_level": data_dir / "lincs_stad_drug_level.parquet",
        "lincs_stad_drug_level_prefixed": data_dir / "lincs_stad_drug_level_with_crispr_prefix.parquet",
        "depmap_crispr_long_pre_refilter": depmap_pre_path,
        "depmap_crispr_long_post_refilter": depmap_post_path,
        "stad_subtype_metadata": data_dir / "stad_subtype_metadata.parquet",
        "gdsc_for_fe": data_dir / "GDSC2-dataset.parquet",
    }

    effective_depmap_key = "depmap_crispr_long_post_refilter"
    effective_depmap_path = depmap_post_path
    if not depmap_post_path.exists():
        effective_depmap_key = "depmap_crispr_long_pre_refilter"
        effective_depmap_path = depmap_pre_path

    required = [
        "labels",
        "drug_features",
        "drug_target_mapping",
        effective_depmap_key,
    ]
    if not args.allow_missing_lincs:
        required += [
            "lincs_stad",
            "lincs_stad_drug_level_prefixed",
        ]

    log("=== STAD Step 2 QC: file presence ===")
    dfs: dict[str, pd.DataFrame] = {}
    for name, path in files_to_check.items():
        if not check_file(path, name, report):
            if name in required:
                report["issues"].append(f"Missing required: {name}")
                report["passed"] = False
            continue
        try:
            dfs[name] = pd.read_parquet(path)
        except Exception as e:
            report["issues"].append(f"{name}: load failed {e}")
            report["passed"] = False

    schemas = {
        "labels": ["sample_id", "canonical_drug_id", "ic50", "binary_label"],
        "drug_features": [
            "canonical_drug_id",
            "canonical_smiles",
            "canonical_smiles_raw",
            "drug_name_norm",
            "has_smiles",
        ],
        "drug_target_mapping": ["canonical_drug_id", "target_gene_symbol"],
        "lincs_stad": ["sig_id", "pert_id", "pert_iname", "cell_id"],
        "lincs_stad_drug_level_prefixed": ["canonical_drug_id"],
        "depmap_crispr_long_pre_refilter": ["cell_line_name", "gene_name", "dependency"],
        "depmap_crispr_long_post_refilter": ["cell_line_name", "gene_name", "dependency"],
    }

    log("=== Schema checks ===")
    for name, cols in schemas.items():
        if name not in dfs:
            continue
        df = dfs[name]
        miss = [c for c in cols if c not in df.columns]
        if miss:
            report["issues"].append(f"{name}: missing columns {miss}")
            report["passed"] = False
        report["schemas"][name] = {"shape": [int(df.shape[0]), int(df.shape[1])]}
        if name == "lincs_stad" and len(df.columns) != 12336:
            report["issues"].append(
                f"lincs_stad: expected 12336 cols, got {len(df.columns)} (warn)"
            )
        if name == "lincs_stad_drug_level_prefixed" and len(df.columns) < 100:
            report["issues"].append("lincs_stad_drug_level_with_crispr_prefix: unexpectedly few columns")

    if "labels" in dfs and "drug_features" in dfs:
        ld = set(dfs["labels"]["canonical_drug_id"].astype(str))
        fd = set(dfs["drug_features"]["canonical_drug_id"].astype(str))
        report["consistency"]["labels_vs_features"] = {
            "labels_only": len(ld - fd),
            "match": ld == fd,
        }
        if ld != fd:
            report["issues"].append("labels drug IDs != drug_features (exact match required for FE)")
            report["passed"] = False

    if "labels" in dfs:
        lc = set(dfs["labels"]["sample_id"].astype(str))
        depmap_consistency: dict[str, dict] = {}

        for key in ["depmap_crispr_long_pre_refilter", "depmap_crispr_long_post_refilter"]:
            if key not in dfs:
                continue
            dc = set(dfs[key]["cell_line_name"].astype(str))
            missing = sorted(lc - dc)
            depmap_consistency[key] = {
                "depmap_path": str(files_to_check[key]),
                "labels_cells_in_depmap": len(lc & dc),
                "labels_not_in_depmap": len(missing),
                "missing_sample_ids": missing,
            }

        report["consistency"]["depmap_validation"] = depmap_consistency
        report["consistency"]["depmap_effective_for_fe"] = {
            "key": effective_depmap_key,
            "path": str(effective_depmap_path),
            "exists": effective_depmap_path.exists(),
        }

        if effective_depmap_key in depmap_consistency:
            eff = depmap_consistency[effective_depmap_key]
            report["consistency"]["labels_cells_in_depmap"] = eff["labels_cells_in_depmap"]
            report["consistency"]["labels_not_in_depmap"] = eff["labels_not_in_depmap"]

            missing_count = eff["labels_not_in_depmap"]
            missing_ids = eff["missing_sample_ids"]
            if missing_count == 0:
                report["info"].append(
                    "Post-refilter: all label sample_ids are present in data/depmap."
                )
            elif missing_count <= 4:
                report["info"].append(
                    "Post-refilter: "
                    f"{missing_count} labels without CRISPR data (expected drop: {missing_ids})."
                )
            else:
                report["warnings"].append(
                    "Post-refilter: "
                    f"{missing_count}/{len(lc)} label sample_ids not in data/depmap "
                    f"(e.g. {missing_ids[:5]}) — check refilter mapping."
                )
        else:
            report["warnings"].append(
                "Post-refilter depmap file missing; falling back to curated_data/processed/depmap for consistency check."
            )

    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    log(f"Report: {out_report}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
