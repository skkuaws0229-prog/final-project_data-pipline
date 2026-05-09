#!/usr/bin/env python3
from __future__ import annotations

import json
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parent.parent
LUNG_ROOT = WORKSPACE / "20260416_new_pre_project_biso_Lung"
RESULTS_DIR = LUNG_ROOT / "results"
REPORT_DIR = WORKSPACE / "reports" / "lung_step6_current_package"
TOP30_CSV = WORKSPACE / "reports" / "lung_step6_package" / "lung_step6_top30_tiered_candidates.csv"

CT_ALL = LUNG_ROOT / "curated_data" / "validation" / "clinicaltrials" / "clinicaltrials_lung_cancer_all_studies.json"
PRISM_TREATMENT = LUNG_ROOT / "curated_data" / "validation" / "prism" / "prism-repurposing-20q2-primary-screen-replicate-collapsed-treatment-info.csv"
COSMIC_DIR = LUNG_ROOT / "curated_data" / "validation" / "cosmic"
CPTAC_DIR = LUNG_ROOT / "curated_data" / "cptac"


def load_top30() -> pd.DataFrame:
    df = pd.read_csv(TOP30_CSV)
    df["canonical_drug_id"] = df["canonical_drug_id"].astype(str)
    if "SYNONYMS" not in df.columns:
        df["SYNONYMS"] = ""
    return df


def collect_phase_bridge_files(top30: pd.DataFrame) -> None:
    phase_cols = [
        "canonical_drug_id",
        "DRUG_NAME",
        "TARGET",
        "TARGET_PATHWAY",
        "SYNONYMS",
        "dedup_rank",
        "pred_ic50_weighted_mean",
    ]
    bridge = top30[phase_cols].copy()
    bridge = bridge.rename(columns={"dedup_rank": "rank", "pred_ic50_weighted_mean": "pred_ic50_mean"})
    bridge["canonical_drug_id"] = pd.to_numeric(bridge["canonical_drug_id"], errors="coerce").astype("Int64")
    bridge.to_csv(RESULTS_DIR / "lung_top30_phase2c_catboost_with_names.csv", index=False)
    bridge.to_csv(RESULTS_DIR / "lung_top30_unified_2b_and_2c_with_names.csv", index=False)


def match_prism(top30: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    treatment = pd.read_csv(PRISM_TREATMENT)
    treatment["name_key"] = treatment["name"].astype(str).str.strip().str.lower()
    rows: list[dict[str, object]] = []

    for _, row in top30.iterrows():
        names = {str(row["DRUG_NAME"]).strip().lower()}
        synonyms = [s.strip().lower() for s in str(row.get("SYNONYMS", "")).split(",") if s.strip()]
        names.update(synonyms)
        matched = treatment[treatment["name_key"].isin(names)]
        for _, hit in matched.drop_duplicates(subset=["broad_id"]).iterrows():
            rows.append(
                {
                    "canonical_drug_id": row["canonical_drug_id"],
                    "DRUG_NAME": row["DRUG_NAME"],
                    "prism_broad_id": hit["broad_id"],
                    "prism_name": hit["name"],
                    "prism_target": hit.get("target", ""),
                    "prism_moa": hit.get("moa", ""),
                    "prism_phase": hit.get("phase", ""),
                    "match_type": "exact_name_or_synonym",
                }
            )

    matches = pd.DataFrame(rows).drop_duplicates()
    summary = {
        "package_drug_count": int(len(top30)),
        "prism_matched_drugs": int(matches["canonical_drug_id"].nunique()) if not matches.empty else 0,
        "prism_match_rate": float(matches["canonical_drug_id"].nunique() / len(top30)) if len(top30) else 0.0,
    }
    return matches, summary


def load_ct_interventions() -> pd.DataFrame:
    with open(CT_ALL, "r") as f:
        data = json.load(f)
    studies = data["studies"] if isinstance(data, dict) and "studies" in data else data
    rows: list[dict[str, object]] = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        nct_id = protocol.get("identificationModule", {}).get("nctId", "")
        status = protocol.get("statusModule", {}).get("overallStatus", "")
        arms = protocol.get("armsInterventionsModule", {}).get("interventions", [])
        for intervention in arms:
            if intervention.get("type", "").upper() != "DRUG":
                continue
            name = str(intervention.get("name", "")).strip().lower()
            if name:
                rows.append(
                    {
                        "nct_id": nct_id,
                        "drug_name": name,
                        "ct_status": status,
                        "description": intervention.get("description", ""),
                    }
                )
    return pd.DataFrame(rows).drop_duplicates()


def match_clinical_trials(top30: pd.DataFrame, interventions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    rows: list[dict[str, object]] = []
    for _, row in top30.iterrows():
        names = {str(row["DRUG_NAME"]).strip().lower()}
        synonyms = [s.strip().lower() for s in str(row.get("SYNONYMS", "")).split(",") if s.strip()]
        names.update(synonyms)
        matched = interventions[interventions["drug_name"].isin(names)]
        for _, hit in matched.iterrows():
            rows.append(
                {
                    "canonical_drug_id": row["canonical_drug_id"],
                    "DRUG_NAME": row["DRUG_NAME"],
                    "nct_id": hit["nct_id"],
                    "ct_drug_name": hit["drug_name"],
                    "ct_status": hit["ct_status"],
                    "match_type": "exact_name_or_synonym",
                }
            )
    matches = pd.DataFrame(rows).drop_duplicates(subset=["canonical_drug_id", "nct_id"])
    summary = {
        "package_drug_count": int(len(top30)),
        "clinical_trials_matched_drugs": int(matches["canonical_drug_id"].nunique()) if not matches.empty else 0,
        "clinical_trials_match_rate": float(matches["canonical_drug_id"].nunique() / len(top30)) if len(top30) else 0.0,
        "clinical_trials_total_pairs": int(len(matches)),
    }
    return matches, summary


def load_cosmic_actionability() -> pd.DataFrame:
    extract_dir = COSMIC_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)
    actionability_files = list(extract_dir.rglob("*Actionability*.tsv"))
    if not actionability_files:
        for tar_path in COSMIC_DIR.glob("*.tar"):
            with tarfile.open(tar_path, "r") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".tsv"):
                        tar.extract(member, path=extract_dir)
        actionability_files = list(extract_dir.rglob("*Actionability*.tsv"))
    if not actionability_files:
        return pd.DataFrame()
    return pd.read_csv(actionability_files[0], sep="\t", low_memory=False)


def match_cosmic(top30: pd.DataFrame, actionability: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    if actionability.empty:
        return pd.DataFrame(), {
            "package_drug_count": int(len(top30)),
            "cosmic_matched_drugs": 0,
            "cosmic_match_rate": 0.0,
            "cosmic_actionability_records": 0,
        }

    drug_cols = [c for c in actionability.columns if any(key in c.lower() for key in ["drug", "therapy", "compound"])]
    rows: list[dict[str, object]] = []
    for _, row in top30.iterrows():
        names = {str(row["DRUG_NAME"]).strip().lower()}
        synonyms = [s.strip().lower() for s in str(row.get("SYNONYMS", "")).split(",") if s.strip()]
        names.update(synonyms)
        for col in drug_cols:
            series = actionability[col].astype(str).str.lower()
            mask = np.zeros(len(series), dtype=bool)
            for name in names:
                mask |= series.str.contains(name, na=False, regex=False)
            matched = actionability[mask]
            for _, hit in matched.iterrows():
                payload = {
                    "canonical_drug_id": row["canonical_drug_id"],
                    "DRUG_NAME": row["DRUG_NAME"],
                    "cosmic_drug_field": col,
                    "cosmic_drug_value": hit[col],
                }
                for key in ["GENOMIC_MUTATION_ID", "TRIAL_ID", "TUMOUR_TYPE", "MUTATION_CD", "EVIDENCE_TYPE"]:
                    if key in hit.index:
                        payload[key] = hit[key]
                rows.append(payload)
    matches = pd.DataFrame(rows).drop_duplicates()
    summary = {
        "package_drug_count": int(len(top30)),
        "cosmic_matched_drugs": int(matches["canonical_drug_id"].nunique()) if not matches.empty else 0,
        "cosmic_match_rate": float(matches["canonical_drug_id"].nunique() / len(top30)) if len(top30) else 0.0,
        "cosmic_actionability_records": int(len(matches)),
    }
    return matches, summary


def find_cptac_expression_file(dataset_dir: Path) -> Path | None:
    candidates = sorted(dataset_dir.glob("data_mrna*.txt"))
    for candidate in candidates:
        lower = candidate.name.lower()
        if ("fpkm" in lower or "rpkm" in lower) and "zscore" not in lower:
            return candidate
    return candidates[0] if candidates else None


def match_cptac(top30: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    targets = top30[["canonical_drug_id", "DRUG_NAME", "TARGET"]].dropna().copy()
    rows: list[dict[str, object]] = []
    for dataset_dir in sorted(CPTAC_DIR.glob("*")):
        expr_file = find_cptac_expression_file(dataset_dir)
        if expr_file is None:
            continue
        sample = pd.read_csv(expr_file, sep="\t", nrows=1)
        skiprows = 4 if str(sample.columns[0]).startswith("#") or str(sample.iloc[0, 0]).startswith("#") else 0
        expr = pd.read_csv(expr_file, sep="\t", skiprows=skiprows)
        gene_col = expr.columns[0]
        for _, row in targets.iterrows():
            target_names = [t.strip() for t in str(row["TARGET"]).split(",") if t.strip()]
            for target in target_names:
                matched = expr[expr[gene_col] == target]
                if matched.empty:
                    continue
                values = pd.to_numeric(matched.iloc[0, 1:], errors="coerce").dropna()
                if values.empty:
                    continue
                rows.append(
                    {
                        "canonical_drug_id": row["canonical_drug_id"],
                        "drug_name": row["DRUG_NAME"],
                        "target": target,
                        "dataset": dataset_dir.name,
                        "n_patients": int(values.shape[0]),
                        "mean_expression": float(values.mean()),
                        "std_expression": float(values.std()),
                        "median_expression": float(values.median()),
                        "min_expression": float(values.min()),
                        "max_expression": float(values.max()),
                    }
                )
    matches = pd.DataFrame(rows)
    summary = {
        "cptac_datasets": int(matches["dataset"].nunique()) if not matches.empty else 0,
        "drug_target_pairs_with_expression": int(len(matches)),
        "drugs_with_expression_data": int(matches["canonical_drug_id"].nunique()) if not matches.empty else 0,
    }
    return matches, summary


def score_package(
    top30: pd.DataFrame,
    prism_matches: pd.DataFrame,
    ct_matches: pd.DataFrame,
    cosmic_matches: pd.DataFrame,
    cptac_matches: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
    df = top30.copy()
    drug_ids = df["canonical_drug_id"].astype(str)

    prism_set = set(prism_matches["canonical_drug_id"].astype(str)) if not prism_matches.empty else set()
    ct_set = set(ct_matches["canonical_drug_id"].astype(str)) if not ct_matches.empty else set()
    cosmic_set = set(cosmic_matches["canonical_drug_id"].astype(str)) if not cosmic_matches.empty else set()
    cptac_set = set(cptac_matches["canonical_drug_id"].astype(str)) if not cptac_matches.empty else set()

    ct_counts = ct_matches.groupby("canonical_drug_id").size().to_dict() if not ct_matches.empty else {}
    cosmic_counts = cosmic_matches.groupby("canonical_drug_id").size().to_dict() if not cosmic_matches.empty else {}
    expr_means = cptac_matches.groupby("canonical_drug_id")["mean_expression"].mean().to_dict() if not cptac_matches.empty else {}

    scored = pd.DataFrame(
        {
            "canonical_drug_id": drug_ids,
            "drug_name": df["drug_name_display"],
            "target": df["TARGET"],
            "canonical_smiles": df["canonical_smiles"],
            "final_rank": df["dedup_rank"].astype(int),
            "prediction_score": 1.0 / df["dedup_rank"].astype(float),
        }
    )
    scored["prism_validated"] = scored["canonical_drug_id"].isin(prism_set)
    scored["clinical_trials_validated"] = scored["canonical_drug_id"].isin(ct_set)
    scored["cosmic_validated"] = scored["canonical_drug_id"].isin(cosmic_set)
    scored["cptac_validated"] = scored["canonical_drug_id"].isin(cptac_set)
    scored["n_clinical_trials"] = scored["canonical_drug_id"].map(ct_counts).fillna(0).astype(int)
    scored["n_cosmic_records"] = scored["canonical_drug_id"].map(cosmic_counts).fillna(0).astype(int)
    scored["target_expression"] = scored["canonical_drug_id"].map(expr_means).fillna(0.0)
    scored["validation_score"] = (
        scored[["prism_validated", "clinical_trials_validated", "cosmic_validated", "cptac_validated"]].sum(axis=1) / 4.0
    )
    scored["multi_objective_score"] = (
        0.40 * scored["prediction_score"]
        + 0.30 * scored["validation_score"]
        + 0.20 * np.minimum(scored["n_clinical_trials"] / 100.0, 1.0)
        + 0.10 * np.minimum(scored["target_expression"] / 1000.0, 1.0)
    )
    scored["confidence"] = (
        scored[["prism_validated", "clinical_trials_validated", "cosmic_validated", "cptac_validated"]].sum(axis=1) * 25
    )
    scored = scored.sort_values(["multi_objective_score", "prediction_score"], ascending=[False, False]).reset_index(drop=True)
    scored["final_rank"] = np.arange(1, len(scored) + 1)

    summary = {
        "total_drugs": int(len(scored)),
        "validation_sources": 4,
        "avg_confidence": float(scored["confidence"].mean()),
        "avg_validation_score": float(scored["validation_score"].mean()),
        "high_confidence_drugs": int((scored["confidence"] >= 75).sum()),
        "top_10_drugs": scored.head(10)[["drug_name", "multi_objective_score", "confidence"]].to_dict("records"),
    }
    return scored, summary


def save_outputs(
    top30: pd.DataFrame,
    prism_matches: pd.DataFrame,
    prism_summary: dict[str, object],
    ct_matches: pd.DataFrame,
    ct_summary: dict[str, object],
    cosmic_matches: pd.DataFrame,
    cosmic_summary: dict[str, object],
    cptac_matches: pd.DataFrame,
    cptac_summary: dict[str, object],
    scored: pd.DataFrame,
    scoring_summary: dict[str, object],
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    mapping = [
        (prism_matches, RESULTS_DIR / "lung_prism_matched_drugs.csv", REPORT_DIR / "lung_prism_matched_drugs.csv"),
        (ct_matches, RESULTS_DIR / "lung_clinical_trials_matched_drugs.csv", REPORT_DIR / "lung_clinical_trials_matched_drugs.csv"),
        (cosmic_matches, RESULTS_DIR / "lung_cosmic_matched_drugs.csv", REPORT_DIR / "lung_cosmic_matched_drugs.csv"),
        (cptac_matches, RESULTS_DIR / "lung_cptac_target_expression_stats.csv", REPORT_DIR / "lung_cptac_target_expression_stats.csv"),
        (scored, RESULTS_DIR / "lung_final_drug_ranking_with_scores.csv", REPORT_DIR / "lung_final_drug_ranking_with_scores.csv"),
        (scored, RESULTS_DIR / "lung_final_drug_ranking_dedup.csv", REPORT_DIR / "lung_final_drug_ranking_dedup.csv"),
    ]
    for df, primary, secondary in mapping:
        df.to_csv(primary, index=False)
        df.to_csv(secondary, index=False)

    summaries = [
        (prism_summary, RESULTS_DIR / "lung_prism_validation_results.json", REPORT_DIR / "lung_prism_validation_results.json"),
        (ct_summary, RESULTS_DIR / "lung_clinical_trials_validation_results.json", REPORT_DIR / "lung_clinical_trials_validation_results.json"),
        (cosmic_summary, RESULTS_DIR / "lung_cosmic_validation_results.json", REPORT_DIR / "lung_cosmic_validation_results.json"),
        (cptac_summary, RESULTS_DIR / "lung_cptac_validation_results.json", REPORT_DIR / "lung_cptac_validation_results.json"),
        (scoring_summary, RESULTS_DIR / "lung_final_ranking_summary.json", REPORT_DIR / "lung_final_ranking_summary.json"),
        (
            {
                "total_drugs": int(len(scored)),
                "duplicates_removed": 0,
                "validation_sources": 4,
                "avg_confidence": float(scored["confidence"].mean()),
                "avg_validation_score": float(scored["validation_score"].mean()),
                "high_confidence_drugs": int((scored["confidence"] >= 75).sum()),
                "top_10_drugs": scored.head(10)[["drug_name", "multi_objective_score", "confidence"]].to_dict("records"),
            },
            RESULTS_DIR / "lung_final_ranking_dedup_summary.json",
            REPORT_DIR / "lung_final_ranking_dedup_summary.json",
        ),
    ]
    for payload, primary, secondary in summaries:
        primary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        secondary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_lines = [
        "# LUNG Step6 Current Package",
        "",
        f"- Source package: `{TOP30_CSV.relative_to(WORKSPACE)}`",
        f"- Package size: `{len(top30)}`",
        "",
        "## External Validation Counts",
        "",
        f"- PRISM matched drugs: `{prism_summary['prism_matched_drugs']}`",
        f"- ClinicalTrials matched drugs: `{ct_summary['clinical_trials_matched_drugs']}`",
        f"- COSMIC matched drugs: `{cosmic_summary['cosmic_matched_drugs']}`",
        f"- CPTAC expression-supported drugs: `{cptac_summary['drugs_with_expression_data']}`",
        "",
        "## Step7 Input Status",
        "",
        "- `lung_final_drug_ranking_with_scores.csv` regenerated from current package",
        "- `lung_final_drug_ranking_dedup.csv` synced for Step7 input",
        "",
        "## Top10 After Step6 Scoring",
        "",
        scored.head(10)[["final_rank", "drug_name", "multi_objective_score", "confidence", "n_clinical_trials"]]
        .round(4)
        .to_markdown(index=False),
    ]
    (REPORT_DIR / "lung_step6_current_package_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")


def main() -> None:
    top30 = load_top30()
    collect_phase_bridge_files(top30)

    prism_matches, prism_summary = match_prism(top30)
    interventions = load_ct_interventions()
    ct_matches, ct_summary = match_clinical_trials(top30, interventions)
    actionability = load_cosmic_actionability()
    cosmic_matches, cosmic_summary = match_cosmic(top30, actionability)
    cptac_matches, cptac_summary = match_cptac(top30)
    scored, scoring_summary = score_package(top30, prism_matches, ct_matches, cosmic_matches, cptac_matches)

    save_outputs(
        top30,
        prism_matches,
        prism_summary,
        ct_matches,
        ct_summary,
        cosmic_matches,
        cosmic_summary,
        cptac_matches,
        cptac_summary,
        scored,
        scoring_summary,
    )

    print(f"wrote step6 current-package outputs to: {REPORT_DIR}")
    print(f"synced step7 inputs to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
