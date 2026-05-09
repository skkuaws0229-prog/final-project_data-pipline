#!/usr/bin/env bash
# Reuse GSE92742 LINCS files from sibling Colon clone (read-only symlink).
#
# Rationale: s3://say2-4team/Stad_raw/LInc1000/ currently mirrors GSE70138 only;
# team LINCS standard for STAD is GSE92742 (configs/lincs_source.json). The ~21GB
# gctx is identical disease-agnostic infrastructure — link instead of duplicating.
#
# Usage:
#   ./scripts/link_lincs_gse92742_from_colon.sh
#   COLON_ROOT=/path/to/20260420_new_pre_project_biso_Colon ./scripts/link_lincs_gse92742_from_colon.sh
#
# Does not modify any file inside Colon or under curated_data/lincs/GSE92742 (read through symlink).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
COLON_ROOT="${COLON_ROOT:-$REPO_ROOT/20260420_new_pre_project_biso_Colon}"
SRC="$COLON_ROOT/curated_data/lincs/GSE92742"
DST="$ROOT/curated_data/lincs/GSE92742"
LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/link_lincs_gse92742_$(date +%Y%m%d_%H%M%S).log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

if [[ ! -d "$SRC" ]]; then
  log "ERROR: Colon LINCS source missing: $SRC"
  log "Set COLON_ROOT to a clone that contains curated_data/lincs/GSE92742/"
  exit 1
fi

if [[ -L "$DST" ]]; then
  log "OK: already symlink -> $(readlink "$DST")"
  exit 0
fi
if [[ -d "$DST" ]]; then
  log "ERROR: $DST exists as a real directory; remove or rename before linking."
  exit 1
fi

mkdir -p "$(dirname "$DST")"
SRC_ABS="$(cd "$SRC" && pwd)"
ln -s "$SRC_ABS" "$DST"
log "I/O symlink $DST -> $SRC_ABS"
log "Done."
