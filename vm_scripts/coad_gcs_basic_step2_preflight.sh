#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/sobi2026/final-project_data-pipline}"
CONFIG="$REPO_ROOT/vm_configs/04_coad_gcs_basic_step2.yaml"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
RUNTIME_ROOT="/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1"

cd "$REPO_ROOT"

echo "[1/5] Checking Python package imports"
"$PYTHON_BIN" - <<'PY'
import importlib
for name in ["numpy", "pandas", "pyarrow", "rdkit", "torch", "lightgbm", "xgboost", "catboost", "sklearn"]:
    importlib.import_module(name)
    print(f"  ok {name}")
PY

echo "[2/5] Checking Step1 outputs required by Step2"
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import pandas as pd
root = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
raw = root / "data/raw_cache"
required = [
    raw / "gdsc_ic50.parquet",
    raw / "cellline_cohort_from_depmap_model.csv",
    raw / "CRISPRGeneEffect.csv",
    raw / "drug_features_catalog.parquet",
    raw / "drug_target_mapping.parquet",
    raw / "lincs_drug_signature_normalized.parquet",
]
missing = [str(path) for path in required if not path.exists()]
print({"missing": missing})
if missing:
    raise SystemExit(2)
gdsc = pd.read_parquet(raw / "gdsc_ic50.parquet")
print({"gdsc_rows": len(gdsc), "cell_lines": gdsc["cell_line_name"].nunique(), "drugs": gdsc["DRUG_ID"].nunique()})
PY

echo "[3/5] Step2 dry-run"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step2 --dry-run

echo "[4/5] Step2 actual run"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step2

echo "[5/5] Checking Step2 final outputs"
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json
import pandas as pd
root = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
required = [
    root / "data/processed/slim_inputs/train_table.parquet",
    root / "outputs/model_runs/metrics_summary.json",
    root / "outputs/model_runs/ensemble_summary.json",
    root / "outputs/final_selection/final_drug_scores.parquet",
    root / "outputs/final_selection/pair_predictions.parquet",
    root / "outputs/final_selection/selected_drugs_top_n.csv",
    root / "outputs/final_selection/selection_summary.json",
]
missing = [str(path) for path in required if not path.exists()]
print({"missing": missing})
if missing:
    raise SystemExit(3)
summary = json.loads((root / "outputs/final_selection/selection_summary.json").read_text())
selected = pd.read_csv(root / "outputs/final_selection/selected_drugs_top_n.csv")
metrics = json.loads((root / "outputs/model_runs/metrics_summary.json").read_text())
print({
    "selected_rows": len(selected),
    "n_pairs": summary.get("n_pairs"),
    "n_drugs": summary.get("n_drugs"),
    "metric_keys": sorted(metrics.get("models", {}).keys()),
    "ensemble": metrics.get("groupcv_ensemble", {}),
})
PY
