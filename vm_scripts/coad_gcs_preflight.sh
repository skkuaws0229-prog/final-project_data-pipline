#!/bin/bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/sobi2026/final-project_data-pipline}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8010}"
GCS_WORKFLOW_ROOT="${GCS_WORKFLOW_ROOT:-gs://sobi2026-myfirst-gcs-backup-20260518/workflow-data/20260408_new_pre_project_biso}"
CONFIG_PATH="${CONFIG_PATH:-$REPO_ROOT/vm_configs/04_coad_gcs_dryrun.yaml}"

export GCS_WORKFLOW_ROOT
export RAW_STORAGE_ROOT="${RAW_STORAGE_ROOT:-$GCS_WORKFLOW_ROOT/202604_Final_data/Colon/shared_inputs/curated_data}"
export GCS_RAW_WSI_ROOT="${GCS_RAW_WSI_ROOT:-$GCS_WORKFLOW_ROOT/202604_Final_data/Colon/0.Image_modal_COAD/_raw_downloads/}"
export GCS_EMBEDDING_ROOT="${GCS_EMBEDDING_ROOT:-$GCS_WORKFLOW_ROOT/202604_Final_data/Colon/0.Image_modal_COAD/step_im2/}"
export GCS_TILES_ROOT="${GCS_TILES_ROOT:-$GCS_WORKFLOW_ROOT/202604_Final_data/Colon/0.Image_modal_COAD/step_im2/}"

cd "$REPO_ROOT"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi

echo "== GCS read preflight =="
gcloud storage ls "$GCS_WORKFLOW_ROOT/202604_Final_data/Colon/" >/dev/null
echo "GCS Colon prefix readable."

echo "== API preflight =="
curl -sS -X POST "$API_BASE_URL/api/pipeline-runs/preflight" \
  -H "Content-Type: application/json" \
  -d '{"disease_name":"대장암","mode":"basic","execution_backend":"gcp_workflows","requested_by":"vm-preflight"}'
echo

echo "== Pipeline dry-run =="
"$PYTHON" pipeline/run_disease_pipeline.py --config "$CONFIG_PATH" --dry-run
