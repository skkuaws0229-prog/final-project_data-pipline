#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 pipeline/run_disease_pipeline.py --config vm_configs/02_luad_gcs_basic_step3.yaml --step step3
