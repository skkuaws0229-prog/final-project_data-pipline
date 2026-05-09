#!/usr/bin/env bash
set -euo pipefail

for cfg in "$(dirname "$0")"/configs/*.yaml; do
  python "$(dirname "$0")/run_disease_pipeline.py" --config "$cfg"
done
