#!/usr/bin/env python3
"""Evidence-agent tier verification package for LUAD GCS basic top15.

This first LUAD pass is intentionally conservative: it carries forward the
existing LUAD 4-tier protocol labels, adds machine-readable review fields, and
marks every row for human clinical/scientific signoff before final use.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_IM4C_SUMMARY = Path(
    "LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_im4c_remap/"
    "luad_gcs_basic_top15_im4c_drug_summary.csv"
)
DEFAULT_OUTPUT_DIR = Path("LUNG/0.Image_modal_LUAD/step_gcs_basic_top15_evidence_agent")


TIER_EVIDENCE_GRADE = {
    "Tier1": "current_lung_reference_or_standard_context",
    "Tier2": "approved_other_or_lung_research_context",
    "Tier3": "repurposing_or_research_candidate",
    "Tier4": "insufficient_or_low_priority_for_repositioning",
}


def build_evidence(im4c_summary: Path) -> pd.DataFrame:
    im4c = pd.read_csv(im4c_summary)
    rows: list[dict[str, Any]] = []
    for _, row in im4c.sort_values("admet_filtered_rank").iterrows():
        raw_tier = row.get("luad_4tier")
        if pd.isna(raw_tier) or not str(raw_tier).strip():
            raw_tier = row.get("crc_4tier")
        tier = "Tier4" if pd.isna(raw_tier) or not str(raw_tier).strip() else str(raw_tier)
        rows.append(
            {
                "admet_filtered_rank": int(row["admet_filtered_rank"]),
                "drug_name": row["drug_name"],
                "im4c_protocol_tier": tier,
                "evidence_agent_final_tier": tier,
                "evidence_grade": TIER_EVIDENCE_GRADE.get(tier, "needs_review"),
                "approved_any_indication": None,
                "approved_lung_indication": None,
                "lung_clinical_evidence": None,
                "lung_preclinical_evidence": None,
                "target": row.get("target"),
                "target_pathway": row.get("target_pathway"),
                "admet_verdict": row.get("admet_verdict"),
                "admet_adjusted_score": row.get("admet_adjusted_score"),
                "im4c_best_match_score": row.get("best_match_score"),
                "tier_change": "unchanged",
                "evidence_rationale": (
                    "Carried forward from existing LUAD 4-tier protocol for the first GCS SDK orchestration test; "
                    "requires refreshed FDA/NCI/ClinicalTrials/PubMed verification before final clinical interpretation."
                ),
                "source_keys": "",
                "source_urls": "",
                "review_status": "evidence_agent_scaffold_needs_human_clinical_signoff",
            }
        )
    return pd.DataFrame(rows)


def write_sources(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source_key", "url", "note"])
        writer.writeheader()
        writer.writerow(
            {
                "source_key": "to_refresh",
                "url": "",
                "note": "Add current FDA/NCI/ClinicalTrials/PubMed sources before clinical use.",
            }
        )


def write_report(df: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# LUAD GCS Basic Top15 Evidence Agent",
        "",
        "Evidence agent started after confirming VM state. This first LUAD pass preserves existing protocol tiers and prepares a review package.",
        "",
        "## VM Check",
        "",
        f"- VM status at evidence-agent start: {summary['vm_status_at_start']}",
        "",
        "## Tier Counts",
        "",
    ]
    for tier, count in summary["final_tier_counts"].items():
        lines.append(f"- {tier}: {count}")
    lines.extend(
        [
            "",
            "## Final Evidence Table",
            "",
            "| Rank | Drug | Final tier | Evidence grade | Review status |",
            "|---:|---|---|---|---|",
        ]
    )
    for _, row in df.iterrows():
        lines.append(
            f"| {int(row['admet_filtered_rank'])} | {row['drug_name']} | {row['evidence_agent_final_tier']} | "
            f"{row['evidence_grade']} | {row['review_status']} |"
        )
    lines.extend(
        [
            "",
            "## Next Evidence-Agent Upgrade",
            "",
            "- Refresh current approval and clinical-trial evidence per drug.",
            "- Split Tier2 and Tier3 candidates into repositioning-priority review queues.",
            "- Require human clinical/scientific signoff before DB loading.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(im4c_summary: Path, output_dir: Path, vm_status_at_start: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_evidence(im4c_summary)
    final_csv = output_dir / "luad_gcs_basic_top15_evidence_verified_tiers.csv"
    sources_csv = output_dir / "luad_gcs_basic_top15_evidence_sources.csv"
    summary_json = output_dir / "luad_gcs_basic_top15_evidence_summary.json"
    report_md = output_dir / "luad_gcs_basic_top15_evidence_report.md"

    df.to_csv(final_csv, index=False)
    write_sources(sources_csv)
    summary = {
        "step": "luad_evidence_agent_tier_verification_scaffold",
        "disease": "LUAD",
        "vm_status_at_start": vm_status_at_start,
        "input_im4c_summary": str(im4c_summary),
        "n_drugs": int(len(df)),
        "final_tier_counts": df["evidence_agent_final_tier"].value_counts().sort_index().to_dict(),
        "changed_from_im4c_protocol_tier": [],
        "outputs": {
            "verified_tiers_csv": str(final_csv),
            "sources_csv": str(sources_csv),
            "summary_json": str(summary_json),
            "report_md": str(report_md),
        },
        "review_scope": "Scaffold evidence package only; requires refreshed source retrieval and human signoff before final use.",
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(df, summary, report_md)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--im4c-summary", type=Path, default=DEFAULT_IM4C_SUMMARY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--vm-status-at-start", default="TERMINATED")
    args = parser.parse_args()
    print(json.dumps(run(args.im4c_summary, args.output_dir, args.vm_status_at_start), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
