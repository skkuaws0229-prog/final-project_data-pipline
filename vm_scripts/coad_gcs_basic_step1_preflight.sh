#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/sobi2026/final-project_data-pipline}"
CONFIG="$REPO_ROOT/vm_configs/04_coad_gcs_basic_step1.yaml"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
GCS_TEMPLATE="gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso/202604_Final_data/HNSC/raw/HNSC_raw"

cd "$REPO_ROOT"

echo "[1/4] Checking required template seed files in GCS"
for rel in   GDSC/GDSC2-dataset.csv   GDSC/screened_compounds_rel_8.5.csv   depmap/Model.csv   depmap/Gene.csv   depmap/CRISPRGeneEffect.csv   drug/drug_features_catalog.parquet   drug/drug_target_mapping.parquet   lincs/lincs_drug_signature_normalized.parquet   admet/admet_group.zip; do
  gcloud storage ls "$GCS_TEMPLATE/$rel" >/dev/null
  echo "  ok $rel"
done

echo "[2/4] Dry-run import and config validation"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step1 --dry-run

echo "[3/4] Actual step1 run: downloads required seed files from read-only GCS to VM runtime"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step1

echo "[4/4] Local output check"
"$PYTHON_BIN" - <<'PY2'
from pathlib import Path
import pandas as pd
root = Path('/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1')
raw = root / 'data/raw_cache'
required = [
    raw / 'gdsc_ic50.parquet',
    raw / 'cellline_cohort_from_depmap_model.csv',
    raw / 'drug_features_catalog.parquet',
    raw / 'drug_target_mapping.parquet',
    raw / 'lincs_drug_signature_normalized.parquet',
]
missing = [str(p) for p in required if not p.exists()]
print({'missing': missing})
if missing:
    raise SystemExit(2)
gdsc = pd.read_parquet(raw / 'gdsc_ic50.parquet')
print({'gdsc_rows': len(gdsc), 'cell_lines': gdsc['cell_line_name'].nunique(), 'drugs': gdsc['DRUG_ID'].nunique()})
PY2
