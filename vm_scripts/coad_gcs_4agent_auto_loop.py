#!/usr/bin/env python3
"""CLI wrapper for the internal pdrp_sdk 4-agent workflow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pdrp_sdk import FourAgentWorkflow, WorkflowConfig


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--disease", default="COAD", help="Disease profile to run. v0.2 ships with COAD; add profiles in pdrp_sdk.config for more diseases.")
    parser.add_argument("--runtime-root", default="/home/skku_aws2_14/sobi2026/runtime/coad_gcs_basic_step1")
    parser.add_argument("--local-step3-fallback", default="/private/tmp/coad_step3_outputs/final_selection/admet_filtered_top15.csv")
    parser.add_argument("--run-heavy", action="store_true", help="Actually run Step1/Step2/Step3 scripts instead of resume verification.")
    parser.add_argument("--upload-gcs", action="store_true", help="Upload auto-loop report/code to GCS after completion.")
    parser.add_argument("--vm-status-override", choices=["TERMINATED", "RUNNING", "STOPPING", "UNKNOWN"], help="Use a known VM status when local gcloud checks are sandbox-limited.")
    args = parser.parse_args()
    config = WorkflowConfig.from_repo_root(
        REPO_ROOT,
        disease=args.disease,
        runtime_root=Path(args.runtime_root),
        local_step3_fallback=Path(args.local_step3_fallback),
    )
    workflow = FourAgentWorkflow(config)
    result = workflow.run(
        run_heavy=args.run_heavy,
        upload_gcs=args.upload_gcs,
        vm_status_override=args.vm_status_override,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
