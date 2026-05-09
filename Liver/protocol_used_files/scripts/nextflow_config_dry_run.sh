#!/usr/bin/env bash
# Print resolved Nextflow params (requires `nextflow` on PATH).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/nextflow"
exec nextflow config .
