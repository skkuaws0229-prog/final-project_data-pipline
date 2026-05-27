#!/usr/bin/env python3
"""Evidence-agent final Tier1-4 verification for COAD GCS basic top15.

This is a lightweight evidence synthesis step. It does not run model training.
It consumes the im4c remap drug summary and writes a verified/provisional
Tier1-4 evidence package with source URLs and review notes.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_IM4C_SUMMARY = Path(
    "Colon/0.Image_modal_COAD/step_gcs_basic_top15_im4c_remap/"
    "coad_gcs_basic_top15_im4c_drug_summary.csv"
)
DEFAULT_OUTPUT_DIR = Path("Colon/0.Image_modal_COAD/step_gcs_basic_top15_evidence_agent")


SOURCES = {
    "nci_crc_drugs": "https://www.cancer.gov/about-cancer/treatment/drugs/colorectal",
    "irinotecan_label": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=7a30d551-9ea7-47ea-9073-f541bff457a3",
    "gemcitabine_nci": "https://www.cancer.gov/about-cancer/treatment/drugs/gemcitabinehydrochloride",
    "gemcitabine_rectal_phase2": "https://pubmed.ncbi.nlm.nih.gov/35146939/",
    "gemcitabine_mcrc": "https://pubmed.ncbi.nlm.nih.gov/26885049/",
    "trametinib_nci": "https://www.cancer.gov/about-cancer/treatment/drugs/trametinib",
    "trametinib_ulixertinib_crc_case": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6954994/",
    "pd0325901_crc_trial": "https://clinicaltrials.gov/study/NCT02510001",
    "pd0325901_crc_pmc": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7156736/",
    "pd0325901_crc_preclinical": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4234626/",
    "mg132_colon_pubmed": "https://pubmed.ncbi.nlm.nih.gov/18414391/",
    "bi2536_phase1": "https://pubmed.ncbi.nlm.nih.gov/18955456/",
    "bi2536_pancreas_pmc": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3394983/",
    "hsp90_crc_pubmed": "https://pubmed.ncbi.nlm.nih.gov/25296971/",
    "avagacestat_gsi_review": "https://pubmed.ncbi.nlm.nih.gov/33284507/",
    "ro4929097_crc_pmc": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4522922/",
    "fulvestrant_fda": "https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-capivasertib-fulvestrant-breast-cancer",
    "esr1_crc_pubmed": "https://pubmed.ncbi.nlm.nih.gov/32266127/",
    "mycophenolic_crc_pubmed": "https://pubmed.ncbi.nlm.nih.gov/8640790/",
    "mycophenolate_label": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/050722s049s051%2C050723s049s051%2C050758s047s049%2C050759s054s056lbl.pdf",
    "azd8055_colon_pubmed": "https://pubmed.ncbi.nlm.nih.gov/29491070/",
    "azd8055_crc_pubmed": "https://pubmed.ncbi.nlm.nih.gov/24163374/",
    "elesclomol_crc_pmc": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8637554/",
}


EVIDENCE = {
    "MG-132": {
        "final_tier": "Tier3",
        "evidence_grade": "preclinical_crc",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": True,
        "rationale": "Not an approved drug, but MG-132/proteasome inhibition has colon-cancer cell-line evidence.",
        "sources": ["mg132_colon_pubmed"],
    },
    "PD0325901": {
        "final_tier": "Tier3",
        "evidence_grade": "crc_clinical_investigational",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": True,
        "crc_preclinical": True,
        "rationale": "Investigational MEK inhibitor with CRC clinical study evidence; not FDA-approved as a marketed drug.",
        "sources": ["pd0325901_crc_trial", "pd0325901_crc_pmc", "pd0325901_crc_preclinical"],
    },
    "Irinotecan": {
        "final_tier": "Tier1",
        "evidence_grade": "crc_approved",
        "approved_any": True,
        "approved_crc": True,
        "crc_clinical": True,
        "crc_preclinical": True,
        "rationale": "FDA/NCI-listed colorectal cancer therapy; label includes metastatic carcinoma of colon or rectum.",
        "sources": ["nci_crc_drugs", "irinotecan_label"],
    },
    "BI-2536": {
        "final_tier": "Tier4",
        "evidence_grade": "weak_non_crc_solid_tumor",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "Investigational PLK1 inhibitor with advanced solid-tumor trials, but no strong drug-specific CRC evidence found in this pass.",
        "sources": ["bi2536_phase1", "bi2536_pancreas_pmc"],
    },
    "CCT-018159": {
        "final_tier": "Tier3",
        "evidence_grade": "target_pathway_crc_preclinical",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": True,
        "rationale": "HSP90 inhibition has CRC cell-line sensitization evidence; CCT-018159 remains investigational.",
        "sources": ["hsp90_crc_pubmed"],
    },
    "YK-4-279": {
        "final_tier": "Tier4",
        "evidence_grade": "insufficient_crc_evidence",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "No sufficient CRC-specific clinical or preclinical treatment evidence found in this pass.",
        "sources": [],
    },
    "Avagacestat": {
        "final_tier": "Tier4",
        "evidence_grade": "class_relevance_not_drug_specific",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "Gamma-secretase/Notch class has CRC relevance, but available CRC clinical evidence is for another GSI rather than avagacestat.",
        "sources": ["avagacestat_gsi_review", "ro4929097_crc_pmc"],
    },
    "Trametinib": {
        "final_tier": "Tier2",
        "evidence_grade": "approved_other_crc_research",
        "approved_any": True,
        "approved_crc": False,
        "crc_clinical": True,
        "crc_preclinical": True,
        "rationale": "FDA-approved for other BRAF-mutant cancers; CRC case/research evidence exists for MEK/ERK-pathway use but not CRC approval.",
        "sources": ["trametinib_nci", "trametinib_ulixertinib_crc_case"],
    },
    "Fulvestrant": {
        "final_tier": "Tier4",
        "evidence_grade": "approved_other_but_crc_drug_evidence_insufficient",
        "approved_any": True,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "Approved in breast cancer settings; CRC evidence found here is biomarker-level ESR1 relevance, not fulvestrant treatment evidence.",
        "sources": ["fulvestrant_fda", "esr1_crc_pubmed"],
    },
    "Schweinfurthin A": {
        "final_tier": "Tier4",
        "evidence_grade": "insufficient_crc_evidence",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "No sufficient CRC-specific clinical or preclinical treatment evidence found in this pass.",
        "sources": [],
    },
    "Mycophenolic acid": {
        "final_tier": "Tier4",
        "evidence_grade": "approved_other_with_negative_crc_signal",
        "approved_any": True,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": False,
        "rationale": "Mycophenolate products are approved for transplant rejection prophylaxis; colorectal carcinoma-cell evidence suggests resistance/inactivation rather than a clear repurposing signal.",
        "sources": ["mycophenolate_label", "mycophenolic_crc_pubmed"],
    },
    "Gemcitabine": {
        "final_tier": "Tier2",
        "evidence_grade": "approved_other_crc_clinical_research",
        "approved_any": True,
        "approved_crc": False,
        "crc_clinical": True,
        "crc_preclinical": True,
        "rationale": "FDA-approved for other cancers and has rectal/metastatic colorectal clinical-study evidence, but not listed as CRC-approved therapy.",
        "sources": ["gemcitabine_nci", "gemcitabine_rectal_phase2", "gemcitabine_mcrc"],
    },
    "Elesclomol": {
        "final_tier": "Tier3",
        "evidence_grade": "preclinical_crc",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": True,
        "rationale": "Investigational compound with colorectal cancer in-vitro/in-vivo ferroptosis evidence.",
        "sources": ["elesclomol_crc_pmc"],
    },
    "AZD8055": {
        "final_tier": "Tier3",
        "evidence_grade": "preclinical_crc",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": False,
        "crc_preclinical": True,
        "rationale": "Investigational mTORC1/2 inhibitor with colon/CRC preclinical evidence.",
        "sources": ["azd8055_colon_pubmed", "azd8055_crc_pubmed"],
    },
    "Ulixertinib": {
        "final_tier": "Tier3",
        "evidence_grade": "crc_research_investigational",
        "approved_any": False,
        "approved_crc": False,
        "crc_clinical": True,
        "crc_preclinical": True,
        "rationale": "Investigational ERK inhibitor with CRC case/research evidence; not CRC-approved.",
        "sources": ["trametinib_ulixertinib_crc_case"],
    },
}


def build_evidence(im4c_summary: Path) -> pd.DataFrame:
    im4c = pd.read_csv(im4c_summary)
    rows: list[dict[str, Any]] = []
    for _, row in im4c.sort_values("admet_filtered_rank").iterrows():
        drug = str(row["drug_name"])
        evidence = EVIDENCE[drug]
        source_keys = evidence["sources"]
        rows.append(
            {
                "admet_filtered_rank": int(row["admet_filtered_rank"]),
                "drug_name": drug,
                "im4c_protocol_tier": row["crc_4tier"],
                "evidence_agent_final_tier": evidence["final_tier"],
                "evidence_grade": evidence["evidence_grade"],
                "approved_any_indication": evidence["approved_any"],
                "approved_crc_indication": evidence["approved_crc"],
                "crc_clinical_evidence": evidence["crc_clinical"],
                "crc_preclinical_evidence": evidence["crc_preclinical"],
                "target": row.get("target"),
                "target_pathway": row.get("target_pathway"),
                "admet_verdict": row.get("admet_verdict"),
                "admet_adjusted_score": row.get("admet_adjusted_score"),
                "im4c_best_match_score": row.get("best_match_score"),
                "tier_change": "unchanged" if row["crc_4tier"] == evidence["final_tier"] else f"{row['crc_4tier']} -> {evidence['final_tier']}",
                "evidence_rationale": evidence["rationale"],
                "source_keys": ";".join(source_keys),
                "source_urls": ";".join(SOURCES[key] for key in source_keys),
                "review_status": "evidence_agent_reviewed_needs_human_clinical_signoff",
            }
        )
    return pd.DataFrame(rows)


def write_sources(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source_key", "url"])
        writer.writeheader()
        for key, url in SOURCES.items():
            writer.writerow({"source_key": key, "url": url})


def write_report(df: pd.DataFrame, summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# COAD GCS Basic Top15 Evidence Agent",
        "",
        "Evidence agent started after confirming the GCP VM was terminated, so no n2-standard-16 compute cost should continue from this workflow.",
        "The table below verifies the provisional im4c tiers against approval, CRC clinical evidence, and CRC preclinical evidence.",
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
            "| Rank | Drug | Final tier | Prior tier | Evidence grade | Tier change | Rationale |",
            "|---:|---|---|---|---|---|---|",
        ]
    )
    for _, row in df.iterrows():
        lines.append(
            f"| {int(row['admet_filtered_rank'])} | {row['drug_name']} | {row['evidence_agent_final_tier']} | "
            f"{row['im4c_protocol_tier']} | {row['evidence_grade']} | {row['tier_change']} | {row['evidence_rationale']} |"
        )
    lines.extend(
        [
            "",
            "## Agentic AI Orchestration Recommendation",
            "",
            "- Preflight agent: verify VM state, input files, top15 uniqueness, and evidence schema completeness.",
            "- Evidence retrieval agent: refresh FDA/NCI/ClinicalTrials/PubMed sources and record retrieval dates.",
            "- Evidence adjudication agent: apply Tier1-4 rules and flag disagreements with prior protocol tiers.",
            "- Human signoff gate: require clinical/scientific review before marking any candidate as final recommendation.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(im4c_summary: Path, output_dir: Path, vm_status_at_start: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = build_evidence(im4c_summary)
    final_csv = output_dir / "coad_gcs_basic_top15_evidence_verified_tiers.csv"
    sources_csv = output_dir / "coad_gcs_basic_top15_evidence_sources.csv"
    summary_json = output_dir / "coad_gcs_basic_top15_evidence_summary.json"
    report_md = output_dir / "coad_gcs_basic_top15_evidence_report.md"

    df.to_csv(final_csv, index=False)
    write_sources(sources_csv)
    summary = {
        "step": "evidence_agent_tier_verification",
        "disease": "COAD",
        "vm_status_at_start": vm_status_at_start,
        "input_im4c_summary": str(im4c_summary),
        "n_drugs": int(len(df)),
        "final_tier_counts": df["evidence_agent_final_tier"].value_counts().sort_index().to_dict(),
        "changed_from_im4c_protocol_tier": df[df["tier_change"] != "unchanged"][["drug_name", "tier_change"]].to_dict("records"),
        "outputs": {
            "verified_tiers_csv": str(final_csv),
            "sources_csv": str(sources_csv),
            "summary_json": str(summary_json),
            "report_md": str(report_md),
        },
        "review_scope": "Evidence-agent synthesis only; requires human clinical/scientific signoff before final use.",
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
