"""Step 1 — Data Collection & Raw Cache Setup.

Downloads raw data from S3 and creates standardized aliases so that
downstream steps (FE, model training) can work with a consistent layout
regardless of the disease.

Usage (standalone):
    python step1_data_collection.py --config configs/skcm.yaml

Called by orchestrator:
    run_disease_pipeline.py -> steps.step1_data_collection.run(config)
"""
from __future__ import annotations

import json
import re
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

RAW_SEED_FILES = [
    "GDSC/GDSC2-dataset.csv",
    "GDSC/screened_compounds_rel_8.5.csv",
    "depmap/Model.csv",
    "depmap/Gene.csv",
    "depmap/CRISPRGeneEffect.csv",
    "drug/drug_features_catalog.parquet",
    "drug/drug_target_mapping.parquet",
    "lincs/lincs_drug_signature_normalized.parquet",
    "admet/admet_group.zip",
]


# ── Paths ────────────────────────────────────────────────────────────
@dataclass
class PipelinePaths:
    root: Path
    raw_cache: Path
    processed: Path
    standardized: Path
    disease_context: Path
    model_inputs: Path
    slim_inputs: Path
    validation_inputs: Path
    model_runs: Path
    final_selection: Path
    reports: Path


def make_paths(root: Path) -> PipelinePaths:
    return PipelinePaths(
        root=root,
        raw_cache=root / "data/raw_cache",
        processed=root / "data/processed",
        standardized=root / "data/processed/standardized",
        disease_context=root / "data/processed/disease_context",
        model_inputs=root / "data/processed/model_inputs",
        slim_inputs=root / "data/processed/slim_inputs",
        validation_inputs=root / "data/processed/validation_inputs",
        model_runs=root / "outputs/model_runs",
        final_selection=root / "outputs/final_selection",
        reports=root / "outputs/reports",
    )


def ensure_dirs(paths: PipelinePaths) -> None:
    for value in paths.__dict__.values():
        if isinstance(value, Path):
            value.mkdir(parents=True, exist_ok=True)


# ── S3 helpers ───────────────────────────────────────────────────────
def sh(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def s3_object_exists(uri: str) -> bool:
    result = subprocess.run(
        ["aws", "s3", "ls", uri],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def auto_provision_raw_sources(s3_root: str, template_root: str, tcga_code: str) -> dict[str, Any]:
    """Populate a disease raw prefix with reusable common inputs when missing.

    Agent 1 creates the disease config, but Step 1 owns the data preflight. The
    common GDSC/DepMap/drug/LINCS/ADMET files are disease-agnostic seeds; GDSC
    is filtered to the requested TCGA code after download.
    """
    root = s3_root.rstrip("/")
    template = template_root.rstrip("/")
    copied: list[str] = []
    already_present: list[str] = []
    unavailable: list[str] = []

    print(
        f"[Step1] Auto-provision preflight for {tcga_code}: {root} "
        f"(template={template})",
        flush=True,
    )
    for rel_path in RAW_SEED_FILES:
        target_uri = f"{root}/{rel_path}"
        if s3_object_exists(target_uri):
            already_present.append(rel_path)
            continue

        source_uri = f"{template}/{rel_path}"
        if not s3_object_exists(source_uri):
            unavailable.append(rel_path)
            continue

        sh(["aws", "s3", "cp", source_uri, target_uri])
        copied.append(rel_path)

    summary = {
        "template_root": template,
        "target_root": root,
        "copied": copied,
        "already_present": already_present,
        "unavailable": unavailable,
    }
    print(f"[Step1] Auto-provision summary: {json.dumps(summary, indent=2)}", flush=True)
    return summary


def download_sources(paths: PipelinePaths, s3_root: str) -> None:
    """aws s3 sync from the disease-specific raw bucket."""
    sh(["aws", "s3", "sync", s3_root.rstrip("/") + "/", str(paths.raw_cache)])


# ── GDSC conversion ─────────────────────────────────────────────────
def copy_or_convert_gdsc(paths: PipelinePaths, tcga_code: str) -> None:
    """Convert CSV GDSC data into parquet, filtering by TCGA code.

    Supports two layouts:
      1) derived subset:  GDSC/derived_{code}/GDSC2_{CODE}_ic50_subset.csv
      2) full GDSC2:      GDSC/GDSC2-dataset.csv  (filtered by TCGA_DESC)
    """
    out_path = paths.raw_cache / "gdsc_ic50.parquet"
    if out_path.exists():
        return

    code_upper = tcga_code.upper()
    code_lower = tcga_code.lower()

    # Try derived subset first
    subset = paths.raw_cache / f"GDSC/derived_{code_lower}/GDSC2_{code_upper}_ic50_subset.csv"
    if not subset.exists():
        subset = paths.raw_cache / f"GDSC/derived_{code_upper}/GDSC2_{code_upper}_ic50_subset.csv"
    source = subset if subset.exists() else paths.raw_cache / "GDSC/GDSC2-dataset.csv"

    if not source.exists():
        print(f"[WARN] No GDSC source found at {source}. Trying alternative names...")
        for candidate in paths.raw_cache.glob("GDSC/*.csv"):
            if "dataset" in candidate.name.lower() or "ic50" in candidate.name.lower():
                source = candidate
                break

    if not source.exists():
        raise FileNotFoundError(f"GDSC data not found. Tried {subset} and GDSC2-dataset.csv in {paths.raw_cache / 'GDSC'}")

    print(f"[Step1] Loading GDSC from {source}", flush=True)
    gdsc = pd.read_csv(source)

    # Filter by TCGA code if full dataset
    if "TCGA_DESC" in gdsc.columns and not subset.exists():
        gdsc = gdsc[gdsc["TCGA_DESC"].astype(str).str.upper().eq(code_upper)].copy()
        print(f"[Step1] Filtered GDSC to {code_upper}: {len(gdsc)} rows", flush=True)

    rename = {
        "CELL_LINE_NAME": "cell_line_name",
        "DRUG_NAME": "drug_name",
        "LN_IC50": "ln_IC50",
        "PUTATIVE_TARGET": "putative_target",
        "PATHWAY_NAME": "pathway_name",
    }
    gdsc = gdsc.rename(columns=rename)
    keep = [
        "cell_line_name", "DRUG_ID", "drug_name", "ln_IC50",
        "putative_target", "pathway_name", "SANGER_MODEL_ID",
        "COSMIC_ID", "TCGA_DESC", "WEBRELEASE",
    ]
    for col in keep:
        if col not in gdsc.columns:
            gdsc[col] = ""
    gdsc[keep].to_parquet(out_path, index=False)
    print(f"[Step1] Saved gdsc_ic50.parquet: {len(gdsc)} rows", flush=True)


# ── Raw cache aliases ────────────────────────────────────────────────
def prepare_raw_cache_aliases(paths: PipelinePaths, tcga_code: str) -> None:
    """Create flat aliases expected by downstream code from the raw layout."""
    copy_or_convert_gdsc(paths, tcga_code)

    code_upper = tcga_code.upper()
    alias_map = {
        "GDSC/screened_compounds_rel_8.5.csv": "screened_compounds_rel_8.5.csv",
        "depmap/Model.csv": "Model.csv",
        "depmap/Gene.csv": "Gene.csv",
        "depmap/CRISPRGeneEffect.csv": "CRISPRGeneEffect.csv",
        "drug/drug_features_catalog.parquet": "drug_features_catalog.parquet",
        "drug/drug_target_mapping.parquet": "drug_target_mapping.parquet",
        "lincs/lincs_drug_signature_normalized.parquet": "lincs_drug_signature_normalized.parquet",
        f"tcga/xena_tcgahub/TCGA.{code_upper}.sampleMap_HiSeqV2.gz": f"TCGA.{code_upper}.sampleMap_HiSeqV2.gz",
        f"tcga/xena_tcgahub/TCGA.{code_upper}.sampleMap_{code_upper}_clinicalMatrix.tsv":
            f"TCGA.{code_upper}.sampleMap_{code_upper}_clinicalMatrix.tsv",
    }
    for source_rel, target_name in alias_map.items():
        source = paths.raw_cache / source_rel
        target = paths.raw_cache / target_name
        if source.exists() and not target.exists():
            target.write_bytes(source.read_bytes())

    # Build cohort mapping from DepMap Model.csv if not present
    cohort_path = paths.raw_cache / "cellline_cohort_from_depmap_model.csv"
    if not cohort_path.exists():
        raw_map = paths.raw_cache / f"raw_meta/{tcga_code.lower()}_gdsc_depmap_cellline_map.csv"
        if raw_map.exists():
            mapping = pd.read_csv(raw_map)
            out = pd.DataFrame({
                "cell_line_name": mapping["CELL_LINE_NAME"].astype(str).str.strip(),
                "ModelID": mapping["ModelID"].fillna("").astype(str),
                "OncotreeCode": mapping.get("OncotreeCode", "").fillna("").astype(str),
                "OncotreeSubtype": mapping.get("OncotreeSubtype", "").fillna("").astype(str),
                "cohort": code_upper,
            })
        else:
            model_path = paths.raw_cache / "Model.csv"
            if model_path.exists():
                model = pd.read_csv(model_path)
                out = pd.DataFrame({
                    "cell_line_name": model["CellLineName"].astype(str).str.strip(),
                    "ModelID": model["ModelID"].astype(str),
                    "OncotreeCode": model.get("OncotreeCode", "").fillna("").astype(str),
                    "OncotreeSubtype": model.get("OncotreeSubtype", "").fillna("").astype(str),
                    "cohort": code_upper,
                })
            else:
                print(f"[WARN] No Model.csv found, cannot build cohort mapping")
                out = pd.DataFrame(columns=["cell_line_name", "ModelID", "OncotreeCode", "OncotreeSubtype", "cohort"])
        out = out[out["ModelID"].astype(str).str.len() > 0].drop_duplicates("cell_line_name")
        out.to_csv(cohort_path, index=False)

    # Unzip ADMET data if needed
    admet_zip = paths.raw_cache / "admet/admet_group.zip"
    admet_out = paths.raw_cache / "admet/tdc_admet_group/admet_group"
    if admet_zip.exists() and not admet_out.exists():
        admet_out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(admet_zip, "r") as zf:
            zf.extractall(admet_out.parent)
        print(f"[Step1] Extracted ADMET data to {admet_out.parent}", flush=True)


# ── Public interface (called by orchestrator) ────────────────────────
def run(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """Entry point called by run_disease_pipeline.py orchestrator.

    Args:
        config: Parsed YAML config with keys:
            - disease / tcga_code: e.g. "SKCM"
            - s3_raw_root: e.g. "s3://say2-4team/SKCM_raw"
            - project_root: local working directory
            - skip_download: bool (optional)
    Returns:
        Summary dict with counts and paths.
    """
    raw = config.get("tcga_code", config.get("disease", "UNKNOWN"))
    if isinstance(raw, dict):
        tcga_code = str(raw.get("code", raw.get("name", "UNKNOWN"))).upper()
    else:
        tcga_code = str(raw).upper()
    s3_root = config.get("s3_raw_root", f"s3://say2-4team/{tcga_code}_raw")
    execution = config.get("execution", {}) if isinstance(config.get("execution", {}), dict) else {}
    auto_provision_raw = config.get("auto_provision_raw", execution.get("auto_provision_raw", True))
    raw_template_root = config.get("raw_template_root", execution.get("raw_template_root", "s3://say2-4team/HNSC_raw"))
    project_root = Path(config.get("project_root", f"./{tcga_code}_pipeline"))
    skip_download = config.get("skip_download", False)

    paths = make_paths(project_root)
    ensure_dirs(paths)

    # Download
    if not skip_download:
        provision_summary = None
        if auto_provision_raw and raw_template_root:
            provision_summary = auto_provision_raw_sources(s3_root, raw_template_root, tcga_code)
        print(f"[Step1] Downloading from {s3_root} ...", flush=True)
        download_sources(paths, s3_root)
    else:
        provision_summary = None
        print(f"[Step1] Skipping download (skip_download=True)", flush=True)

    # Aliases & GDSC conversion
    print(f"[Step1] Preparing raw cache aliases for {tcga_code} ...", flush=True)
    prepare_raw_cache_aliases(paths, tcga_code)

    # Summary
    summary = {
        "step": "step1_data_collection",
        "disease": tcga_code,
        "s3_root": s3_root,
        "auto_provision_raw": bool(auto_provision_raw),
        "raw_template_root": raw_template_root,
        "raw_provision": provision_summary,
        "project_root": str(project_root),
        "gdsc_parquet_exists": (paths.raw_cache / "gdsc_ic50.parquet").exists(),
        "cohort_csv_exists": (paths.raw_cache / "cellline_cohort_from_depmap_model.csv").exists(),
        "admet_dir_exists": (paths.raw_cache / "admet/tdc_admet_group/admet_group").exists(),
    }

    # Count GDSC rows if available
    if summary["gdsc_parquet_exists"]:
        gdsc = pd.read_parquet(paths.raw_cache / "gdsc_ic50.parquet")
        summary["gdsc_rows"] = int(len(gdsc))
        summary["gdsc_cell_lines"] = int(gdsc["cell_line_name"].nunique())
        summary["gdsc_drugs"] = int(gdsc["DRUG_ID"].nunique()) if "DRUG_ID" in gdsc.columns else 0

    print(f"[Step1] Complete. Summary: {json.dumps(summary, indent=2)}", flush=True)
    return summary


# ── Standalone execution ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="Step 1: Data Collection")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    run(config)
