#!/usr/bin/env bash
# Orchestrate STAD Step 2 after curated_data/ is populated (see parallel_download_stad.sh).
# Reference: 20260420_new_pre_project_biso_Colon differences.md Step 2 records.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
LOG="$ROOT/logs/step2_run_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "[$(date -Iseconds)] STAD Step 2 start ROOT=$ROOT"

LINCS_GSE="${LINCS_GSE:-GSE92742}"
LINCS_DIR="$ROOT/curated_data/lincs/$LINCS_GSE"
# Must match configs/lincs_source.json — do not use find() (would pick GSE70138 if present).
GCTX_FILE="$(ls -1 "$LINCS_DIR"/"${LINCS_GSE}"_Broad_LINCS_Level5*.gctx.gz 2>/dev/null | head -1 || true)"
SIG_FILE="$(ls -1 "$LINCS_DIR"/"${LINCS_GSE}"_Broad_LINCS_sig_info*.txt.gz 2>/dev/null | head -1 || true)"

python3 "$ROOT/scripts/convert_raw_to_parquet.py"
python3 "$ROOT/scripts/extract_chembl_from_sqlite.py"

python3 "$ROOT/nextflow/scripts/convert_depmap_wide_to_long.py" \
  --crispr-uri "$ROOT/curated_data/processed/depmap/CRISPRGeneDependency.parquet" \
  --model-uri "$ROOT/curated_data/processed/depmap/Model.parquet" \
  --output-uri "$ROOT/curated_data/processed/depmap/depmap_crispr_long_stad.parquet"

mkdir -p "$ROOT/data/depmap"
cp -f "$ROOT/curated_data/processed/depmap/depmap_crispr_long_stad.parquet" "$ROOT/data/depmap/"

python3 "$ROOT/scripts/filter_stad_cell_lines.py" \
  --gdsc-ic50 "$ROOT/curated_data/processed/gdsc/GDSC2-dataset.parquet" \
  --gdsc-annotation "$ROOT/curated_data/processed/gdsc/Compounds-annotation.parquet" \
  --depmap-model "$ROOT/curated_data/processed/depmap/Model.parquet" \
  --depmap-long "$ROOT/curated_data/processed/depmap/depmap_crispr_long_stad.parquet" \
  --output-labels "$ROOT/data/labels.parquet" \
  --output-cells "$ROOT/reports/matched_stad_cell_lines.csv" \
  --output-report "$ROOT/reports/step2_4_matching_report.json"

python3 "$ROOT/scripts/export_stad_gdsc_for_prepare.py" \
  --gdsc-parquet "$ROOT/curated_data/processed/gdsc/GDSC2-dataset.parquet" \
  --output "$ROOT/data/GDSC2-dataset.parquet"

python3 "$ROOT/scripts/filter_stad_depmap_to_labels.py" \
  --labels-uri "$ROOT/data/labels.parquet" \
  --depmap-long-uri "$ROOT/curated_data/processed/depmap/depmap_crispr_long_stad.parquet" \
  --depmap-model-uri "$ROOT/curated_data/processed/depmap/Model.parquet" \
  --output-depmap-long "$ROOT/data/depmap/depmap_crispr_long_stad.parquet" \
  --output-gdsc-fe "$ROOT/data/GDSC2-dataset.parquet" \
  --output-report "$ROOT/reports/step2_stad_depmap_refilter.json"

python3 "$ROOT/nextflow/scripts/build_drug_catalog.py" \
  --gdsc-annotation-uri "$ROOT/curated_data/processed/gdsc/Compounds-annotation.parquet" \
  --gdsc-ic50-uri "$ROOT/curated_data/processed/gdsc/GDSC2-dataset.parquet" \
  --chembl-uri "$ROOT/curated_data/processed/chembl/chembl_compounds.parquet" \
  --drugbank-uri "$ROOT/curated_data/processed/drugbank/drugbank_master.parquet" \
  --drugbank-synonym-uri "$ROOT/curated_data/processed/drugbank/drugbank_synonyms.parquet" \
  --output-uri "$ROOT/curated_data/processed/drug_catalog_stad.parquet"

python3 "$ROOT/scripts/bridge_drug_features.py" \
  --catalog-uri "$ROOT/curated_data/processed/drug_catalog_stad.parquet" \
  --labels-uri "$ROOT/data/labels.parquet" \
  --output-uri "$ROOT/data/drug_features.parquet" \
  --report-uri "$ROOT/reports/step2_5_bridge_report.json"

COLON_DTM="/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260420_new_pre_project_biso_Colon/data/drug_target_mapping.parquet"
if [[ -f "$COLON_DTM" ]]; then
  cp -f "$COLON_DTM" "$ROOT/data/drug_target_mapping.parquet"
  echo "Copied drug_target_mapping from Colon (disease-agnostic)."
else
  echo "WARN: drug_target_mapping not found at $COLON_DTM — place drug_target_mapping.parquet under data/"
fi

if [[ -n "$GCTX_FILE" && -f "$GCTX_FILE" && -n "$SIG_FILE" && -f "$SIG_FILE" ]]; then
  python3 "$ROOT/scripts/extract_lincs_gctx_stad.py" \
    --gctx-uri "$GCTX_FILE" \
    --sig-info-uri "$SIG_FILE" \
    --cell-ids-json "$ROOT/configs/stad_lincs_cell_ids.json" \
    --output-uri "$ROOT/data/lincs_stad.parquet" \
    --report-uri "$ROOT/reports/lincs_stad_extract_report.json"

  python3 "$ROOT/scripts/aggregate_lincs_to_drug_level.py" \
    --lincs-sig-uri "$ROOT/data/lincs_stad.parquet" \
    --drug-features-uri "$ROOT/data/drug_features.parquet" \
    --output-uri "$ROOT/data/lincs_stad_drug_level.parquet" \
    --report-uri "$ROOT/reports/lincs_stad_aggregate_report.json"

  python3 "$ROOT/scripts/preprocess_lincs_crispr_prefix.py" \
    --input "$ROOT/data/lincs_stad_drug_level.parquet" \
    --mapping "$ROOT/scripts/gene_symbol_to_entrez.json" \
    --output "$ROOT/data/lincs_stad_drug_level_with_crispr_prefix.parquet"
else
  echo "WARN: LINCS gctx and/or sig_info not found under curated_data/lincs/ — skip LINCS extract."
fi

if [[ ! -f "$ROOT/data/lincs_stad_drug_level_with_crispr_prefix.parquet" ]]; then
  python3 "$ROOT/scripts/step2_qc.py" --project-root "$ROOT" --allow-missing-lincs
else
  python3 "$ROOT/scripts/step2_qc.py" --project-root "$ROOT"
fi
echo "[$(date -Iseconds)] STAD Step 2 done. Log: $LOG"
