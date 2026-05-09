#!/usr/bin/env bash
set -euo pipefail

# One-click runner for Liver package handoff
# Scope:
#   1) Step6 external validation (CPTAC excluded mode)
#   2) Step7 ADMET(22) + Top15
#   3) Tier1/2/3/4 table generation
#
# Usage example:
#   bash "scripts/run_liver_oneclick.sh" \
#     --top30-csv "/abs/path/lihc_top30_directive_ensemble_with_names.csv" \
#     --result-tag "20260428_liver_step4_cv5_gc_sc"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULT_TAG="${RESULT_TAG:-20260428_liver_step4_cv5_gc_sc}"
TOP30_CSV="${TOP30_CSV:-}"
SKIP_STEP6="${SKIP_STEP6:-0}"

NESTED_PROTOCOL_ROOT="${ROOT_DIR}/20260415_preproject_choi_protocol_v1_bisotest/20260421_new_pre_project_biso_STAD"
RUNTIME_SCRIPTS_DIR="${ROOT_DIR}/scripts"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --result-tag)
      RESULT_TAG="$2"
      shift 2
      ;;
    --top30-csv)
      TOP30_CSV="$2"
      shift 2
      ;;
    --skip-step6)
      SKIP_STEP6="1"
      shift 1
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

require_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "ERROR: required file not found: $f" >&2
    exit 1
  fi
}

ensure_runtime_script() {
  local script_name="$1"
  local local_script="${RUNTIME_SCRIPTS_DIR}/${script_name}"
  local source_script="${NESTED_PROTOCOL_ROOT}/scripts/${script_name}"
  if [[ -f "$local_script" ]]; then
    return 0
  fi
  require_file "$source_script"
  cp "$source_script" "$local_script"
}

mkdir -p "${ROOT_DIR}/results" "${ROOT_DIR}/external_validation/${RESULT_TAG}" "${ROOT_DIR}/logs"

if [[ -z "$TOP30_CSV" ]]; then
  TOP30_CSV="${ROOT_DIR}/results/${RESULT_TAG}/lihc_top30_directive_ensemble_with_names.csv"
fi
require_file "$TOP30_CSV"

if [[ "$SKIP_STEP6" != "1" ]]; then
  log "Step6 start (CPTAC excluded): result_tag=${RESULT_TAG}"
  mkdir -p "${ROOT_DIR}/results/${RESULT_TAG}"
  cp "$TOP30_CSV" "${ROOT_DIR}/results/${RESULT_TAG}/lihc_top30_directive_ensemble_with_names.csv"
  python3 "${ROOT_DIR}/scripts/step6_ext_lihc_independent_cptac_excluded.py" \
    --project-root "$ROOT_DIR" \
    --result-tag "$RESULT_TAG"
else
  log "Step6 skipped by flag (--skip-step6)."
fi

log "Ensure Step7 runtime scripts"
ensure_runtime_script "step7_1_admet_filtering_stad.py"
ensure_runtime_script "step7_2_select_top15_lihc.py"

log "Step7-1 start (ADMET 22 assays)"
STAD_TOP30_CSV="$TOP30_CSV" python3 "${ROOT_DIR}/scripts/step7_1_admet_filtering_stad.py"

log "Step7-2 start (Top15)"
python3 "${ROOT_DIR}/scripts/step7_2_select_top15_lihc.py"

log "Build tier1/2/3/4 table from Step7 + Step6 outputs"
ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import json
import os
from pathlib import Path
import pandas as pd

root = Path(os.environ["ROOT_DIR"]).resolve()
result_tag = "20260428_liver_step4_cv5_gc_sc"
top15 = root / "results" / "stad_final_top15.csv"
ext = root / "external_validation" / result_tag / "top30_external_validation_lihc_cptac_excluded.csv"
out_csv = root / "results" / "lihc_step7_final_top15_tier4.csv"
out_json = root / "results" / "lihc_step7_final_top15_tier4_summary.json"

if not top15.is_file():
    raise FileNotFoundError(f"Missing {top15}")
if not ext.is_file():
    raise FileNotFoundError(f"Missing {ext}")

df = pd.read_csv(top15)
extdf = pd.read_csv(ext)
df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
extdf["canonical_drug_id"] = extdf["canonical_drug_id"].astype(str)

merge_cols = [
    "canonical_drug_id",
    "prism_has_evidence",
    "clinical_trials_has_evidence",
    "geo_has_evidence",
    "opentargets_has_evidence",
    "cosmic_has_evidence",
]
df = df.merge(extdf[merge_cols], on="canonical_drug_id", how="left")
for c in merge_cols[1:]:
    df[c] = df[c].fillna(False).astype(bool)
df["external_support_count"] = df[merge_cols[1:]].sum(axis=1)

def assign(row):
    verdict = str(row.get("verdict", "")).upper()
    support = int(row.get("external_support_count", 0))
    approved = bool(row.get("hcc_approved", False))
    if verdict == "PASS" and approved:
        return ("tier1", "HCC-approved and ADMET PASS")
    if verdict == "PASS":
        return ("tier2", "ADMET PASS but not HCC-approved")
    if verdict == "WARNING" and support >= 2:
        return ("tier3", "ADMET WARNING with multi-source support")
    return ("tier4", "ADMET WARNING with limited support")

assigned = df.apply(assign, axis=1)
df["tier"] = assigned.map(lambda x: x[0])
df["tier_note"] = assigned.map(lambda x: x[1])
df["tier_rank"] = df["tier"].map({"tier1": 1, "tier2": 2, "tier3": 3, "tier4": 4})
df = df.sort_values(["tier_rank", "safety_score", "pred_ic50_mean"], ascending=[True, False, True]).reset_index(drop=True)
df["tier_order_rank"] = range(1, len(df) + 1)

keep = [
    "tier_order_rank",
    "recommendation_rank",
    "drug_name",
    "canonical_drug_id",
    "verdict",
    "safety_score",
    "pred_ic50_mean",
    "usage_category",
    "hcc_approved",
    "n_clinical_trials",
    "external_support_count",
    "tier",
    "tier_note",
]
keep = [c for c in keep if c in df.columns]
df[keep].to_csv(out_csv, index=False)

summary = {
    "result_tag": result_tag,
    "input_top15": str(top15),
    "external_validation_csv": str(ext),
    "output_tier4_csv": str(out_csv),
    "tier_counts": df["tier"].value_counts().to_dict(),
}
out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY

log "Done. Key outputs:"
log "  - ${ROOT_DIR}/external_validation/${RESULT_TAG}/external_validation_lihc_cptac_excluded_summary.json"
log "  - ${ROOT_DIR}/results/stad_admet_summary.json"
log "  - ${ROOT_DIR}/results/stad_final_top15.csv"
log "  - ${ROOT_DIR}/results/lihc_step7_final_top15_tier4.csv"
