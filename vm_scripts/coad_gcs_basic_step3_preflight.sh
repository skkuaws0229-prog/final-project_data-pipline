#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/sobi2026/final-project_data-pipline}"
CONFIG="$REPO_ROOT/vm_configs/04_coad_gcs_basic_step3.yaml"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
RUNTIME_ROOT="/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1"

cd "$REPO_ROOT"

echo "[1/4] Checking Step2 candidates and ADMET inputs"
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import pandas as pd
root = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
required = [
    root / "outputs/final_selection/selected_drugs_top_n.csv",
    root / "outputs/final_selection/final_drug_scores.parquet",
    root / "data/raw_cache/admet/tdc_admet_group/admet_group",
]
missing = [str(path) for path in required if not path.exists()]
print({"missing": missing})
if missing:
    raise SystemExit(2)
selected = pd.read_csv(root / "outputs/final_selection/selected_drugs_top_n.csv")
name_key = selected["drug_name"].fillna("").astype(str).str.lower().str.strip()
print({"selected_rows": len(selected), "unique_names": name_key.nunique(), "duplicate_name_rows": int(name_key.duplicated().sum())})
PY

echo "[2/4] Step3 dry-run"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step3 --dry-run

echo "[3/4] Step3 actual run"
"$PYTHON_BIN" pipeline/run_disease_pipeline.py --config "$CONFIG" --step step3

echo "[4/4] Checking Step3 outputs"
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
import json
import pandas as pd
root = Path("/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
required = [
    root / "outputs/final_selection/admet_candidate_gate.csv",
    root / "outputs/final_selection/admet_filtered_top15.csv",
    root / "outputs/final_selection/admet_summary.json",
]
missing = [str(path) for path in required if not path.exists()]
print({"missing": missing})
if missing:
    raise SystemExit(3)
summary = json.loads((root / "outputs/final_selection/admet_summary.json").read_text())
gate = pd.read_csv(root / "outputs/final_selection/admet_candidate_gate.csv")
filtered = pd.read_csv(root / "outputs/final_selection/admet_filtered_top15.csv")
name_key = gate["drug_name"].fillna("").astype(str).str.lower().str.strip()
print({
    "summary": summary,
    "gate_rows": len(gate),
    "filtered_rows": len(filtered),
    "duplicate_name_rows": int(name_key.duplicated().sum()),
})
PY
