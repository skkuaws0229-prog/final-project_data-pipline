#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[LUAD GCP] Step1 data collection / preprocessing"
python3 pipeline/run_disease_pipeline.py --config vm_configs/02_luad_gcs_basic_step1.yaml --step step1

echo "[LUAD GCP] Step2 feature engineering / model training / ranking"
python3 pipeline/run_disease_pipeline.py --config vm_configs/02_luad_gcs_basic_step2.yaml --step step2

echo "[LUAD GCP] Step3 ADMET gate / top15"
python3 pipeline/run_disease_pipeline.py --config vm_configs/02_luad_gcs_basic_step3.yaml --step step3

echo "[LUAD GCP] Step1-3 complete. Run the SDK orchestrator next:"
echo "python3 vm_scripts/coad_gcs_4agent_auto_loop.py --disease LUAD --run-heavy --vm-status-override RUNNING"
