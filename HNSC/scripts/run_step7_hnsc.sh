#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[Step7] ROOT_DIR=${ROOT_DIR}"
python3 "${ROOT_DIR}/scripts/step7_finalize_hnsc.py"
python3 "${ROOT_DIR}/scripts/build_step7_extended_hnsc.py"
echo "[Step7] Done."
