#!/usr/bin/env bash
# STAD Raw 데이터 다운로드 — Stad_raw → 로컬 curated_data/
# 기반: 20260420_new_pre_project_biso_Colon/scripts/parallel_download_colon.sh

set -euo pipefail
BASE_DIR="/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260421_new_pre_project_biso_STAD"
S3_RAW="s3://say2-4team/Stad_raw"
mkdir -p "$BASE_DIR/logs"
LOG_FILE="$BASE_DIR/logs/download_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== STAD Raw 다운로드 시작 (source: ${S3_RAW}) ==="

log "  - GDSC"
aws s3 sync "${S3_RAW}/GDSC/" "$BASE_DIR/curated_data/gdsc/" \
  --exclude "*" --include "GDSC2-dataset.csv" \
  --include "Cell_Lines_Details.xlsx" \
  --include "Compounds-annotation.csv" \
  2>&1 | tee -a "$LOG_FILE"

log "  - DepMap (원본 CSV)"
aws s3 sync "${S3_RAW}/depmap/" "$BASE_DIR/curated_data/depmap/" \
  --exclude "*" \
  --include "CRISPRGeneEffect.csv" \
  --include "CRISPRGeneDependency.csv" \
  --include "Model.csv" \
  --include "ModelCondition.csv" \
  2>&1 | tee -a "$LOG_FILE"

# LINCS: 팀 표준 GSE92742 (configs/lincs_source.json). Stad_raw에 해당 GSE가 없으면
#   scripts/link_lincs_gse92742_from_colon.sh 로 형제 Colon 클론의 동일 파일을 링크.
LINCS_GSE="${LINCS_GSE:-GSE92742}"
log "  - LINCS (${LINCS_GSE}; 경로 LInc1000/ — Colon_raw와 동일; override: env LINCS_GSE=...)"
aws s3 sync "${S3_RAW}/LInc1000/${LINCS_GSE}/" "$BASE_DIR/curated_data/lincs/${LINCS_GSE}/" \
  2>&1 | tee -a "$LOG_FILE"
# Colon_raw와 같이 sig_info/cell_info 등이 LInc1000/ 루트에만 있는 경우 → 동일 GSE 폴더로 보조 동기화
aws s3 sync "${S3_RAW}/LInc1000/" "$BASE_DIR/curated_data/lincs/${LINCS_GSE}/" \
  --exclude "*" \
  --include "${LINCS_GSE}_Broad_LINCS_sig_info*.txt.gz" \
  --include "${LINCS_GSE}_Broad_LINCS_cell_info*.txt.gz" \
  --include "${LINCS_GSE}_Broad_LINCS_pert_info*.txt.gz" \
  --include "${LINCS_GSE}_Broad_LINCS_gene_info*.txt.gz" \
  --include "${LINCS_GSE}_Broad_LINCS_Level5*.gctx.gz" \
  2>&1 | tee -a "$LOG_FILE" || true

log "  - DrugBank"
aws s3 sync "${S3_RAW}/drugbank/" "$BASE_DIR/curated_data/drugbank/" \
  2>&1 | tee -a "$LOG_FILE"

log "  - ChEMBL"
aws s3 sync "${S3_RAW}/chembl/" "$BASE_DIR/curated_data/chembl/" \
  --exclude "*" \
  --include "chembl_*_chemreps.txt.gz" \
  --include "chembl_uniprot_mapping.txt" \
  --include "chembl_*_sqlite.tar.gz" \
  2>&1 | tee -a "$LOG_FILE"

log "  - ADMET"
aws s3 sync "${S3_RAW}/admet/" "$BASE_DIR/curated_data/admet/" \
  2>&1 | tee -a "$LOG_FILE"

log "  - cBioPortal (TCGA-STAD + CPTAC-STAD — 스터디 폴더명은 S3 실제 구조에 맞게 조정)"
if aws s3 ls "${S3_RAW}/cbioportal/" 2>/dev/null | head -1; then
  aws s3 sync "${S3_RAW}/cbioportal/" "$BASE_DIR/curated_data/cbioportal/" \
    2>&1 | tee -a "$LOG_FILE"
else
  log "  (skip) ${S3_RAW}/cbioportal/ not found or empty"
fi

log "  - GEO GSE62254, GSE15459, GSE84437"
for GSE in GSE62254 GSE15459 GSE84437; do
  if aws s3 ls "${S3_RAW}/geo/${GSE}/" 2>/dev/null | head -1; then
    aws s3 sync "${S3_RAW}/geo/${GSE}/" "$BASE_DIR/curated_data/geo/${GSE}/" \
      2>&1 | tee -a "$LOG_FILE"
  else
    log "  (skip) ${S3_RAW}/geo/${GSE}/ not found"
  fi
done

log "  - COSMIC STAD curated (cosmic_stad/)"
if aws s3 ls "${S3_RAW}/additional_sources/cosmic_stad/" 2>/dev/null | head -1; then
  aws s3 sync "${S3_RAW}/additional_sources/cosmic_stad/" \
    "$BASE_DIR/curated_data/additional_sources/cosmic_stad/" \
    2>&1 | tee -a "$LOG_FILE"
else
  log "  (skip) ${S3_RAW}/additional_sources/cosmic_stad/ not found — run scripts/build_cosmic_stad.py + SYNC_S3=1"
fi

log "  - CPTAC-STAD PDC manifests (under cptac_stad/pdc_manifests/)"
if aws s3 ls "${S3_RAW}/cptac_stad/pdc_manifests/" 2>/dev/null | head -1; then
  aws s3 sync "${S3_RAW}/cptac_stad/pdc_manifests/" \
    "$BASE_DIR/curated_data/cptac_stad/pdc_manifests/" \
    2>&1 | tee -a "$LOG_FILE"
else
  log "  (skip) ${S3_RAW}/cptac_stad/pdc_manifests/ not found — run scripts/fetch_pdc_cptac_stad_manifest.py"
fi

log "  - ClinicalTrials (gastric; optional — run scripts/download_stad_clinicaltrials.sh if missing)"
if aws s3 ls "${S3_RAW}/additional_sources/clinicaltrials/" 2>/dev/null | head -1; then
  aws s3 sync "${S3_RAW}/additional_sources/clinicaltrials/" \
    "$BASE_DIR/curated_data/additional_sources/clinicaltrials/" \
    2>&1 | tee -a "$LOG_FILE"
else
  log "  (skip) ${S3_RAW}/additional_sources/clinicaltrials/ not found — populate via download_stad_clinicaltrials.sh + SYNC_S3=1"
fi

log "=== 다운로드 완료 ==="
log "Disk usage:"
du -sh "$BASE_DIR/curated_data/"* 2>&1 | tee -a "$LOG_FILE" || true
