#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
OUT_DIR = WORKSPACE / "20260428_new_BRCA_data"
JSON_OUT = OUT_DIR / "BRCA_s3_upload_manifest_20260428.json"
MD_OUT = OUT_DIR / "BRCA_s3_upload_manifest_20260428.md"
S3_PREFIX = "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/"

ROOTS = [
    Path("20260428_new_BRCA_data"),
    Path("scripts"),
    Path("20260415_preproject_protocol_choi/data"),
    Path(
        "20260415_preproject_choi_protocol_v1_bisotest-1"
        "/20260415_preproject_choi_protocol_v1_bisotest"
        "/results/20260424_multicancer_stad_protocol_rerun"
    ),
    Path(
        "20260415_preproject_choi_protocol_v1_bisotest-1"
        "/20260415_preproject_choi_protocol_v1_bisotest"
        "/curated_data/admet/tdc_admet_group/admet_group"
    ),
]

EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_PARTS = {"__pycache__"}


def should_skip(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return True
    return any(part in EXCLUDE_PARTS for part in path.parts)


def summarize_root(rel_root: Path) -> dict:
    abs_root = WORKSPACE / rel_root
    file_count = 0
    total_bytes = 0
    examples: list[str] = []
    for path in sorted(abs_root.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        file_count += 1
        total_bytes += path.stat().st_size
        if len(examples) < 5:
            examples.append(str(path.relative_to(WORKSPACE)))
    return {
        "relative_root": str(rel_root),
        "absolute_root": str(abs_root),
        "s3_prefix": S3_PREFIX + str(rel_root).replace("\\", "/") + "/",
        "file_count": file_count,
        "total_bytes": total_bytes,
        "example_files": examples,
    }


def build_markdown(summary: list[dict]) -> str:
    total_files = sum(item["file_count"] for item in summary)
    total_bytes = sum(item["total_bytes"] for item in summary)
    lines = [
        "# BRCA S3 Upload Manifest",
        "",
        f"- S3 prefix: `{S3_PREFIX}`",
        "- Purpose: store all BRCA deliverables plus the exact data dependencies required to rerun Step4 -> Step7 from the protocol.",
        f"- Included roots: `{len(summary)}`",
        f"- Total files: `{total_files}`",
        f"- Total bytes: `{total_bytes}`",
        "",
        "## Included Roots",
        "",
        "| Relative Root | Files | Bytes | S3 Prefix |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in summary:
        lines.append(
            f"| `{item['relative_root']}` | {item['file_count']} | {item['total_bytes']} | `{item['s3_prefix']}` |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- These paths are uploaded with workspace-relative structure preserved.",
        "- If downloaded back under the same workspace root, the current BRCA reproduction scripts can be executed without changing hard-coded relative paths.",
        "- `20260428_new_BRCA_data` includes the protocol, report, dashboard, manifests, Top30/Top15 outputs, and validation summaries.",
        "- `scripts` includes the BRCA rerun scripts used for Step4, Step5, Step6, Step7, reporting, and S3 manifest generation.",
        "- `20260415_preproject_protocol_choi/data` includes BRCA model inputs, drug catalog, and METABRIC parquet files.",
        "- `results/20260424_multicancer_stad_protocol_rerun` is required because Step4 and Step5 scripts read the original step4 metrics/predictions from there.",
        "- `curated_data/admet/tdc_admet_group/admet_group` is required because Step7 reads the 22-assay ADMET reference library from there.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = [summarize_root(root) for root in ROOTS]
    payload = {
        "date": "2026-04-28",
        "s3_prefix": S3_PREFIX,
        "workspace": str(WORKSPACE),
        "included_roots": summary,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_OUT.write_text(build_markdown(summary), encoding="utf-8")
    print(f"wrote: {JSON_OUT}")
    print(f"wrote: {MD_OUT}")


if __name__ == "__main__":
    main()
