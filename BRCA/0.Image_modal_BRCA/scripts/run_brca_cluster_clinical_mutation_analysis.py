#!/usr/bin/env python3
"""Attach TCGA-BRCA clinical/subtype/mutation annotations to image clusters.

Sources:
- GDC cases endpoint: case_id, age, stage, grade, vital_status, follow-up.
- cBioPortal PanCancer Atlas: OS/PAM50-like subtype and mutations.
- cBioPortal Firehose Legacy: ER/PR/HER2 receptor status.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy.stats import chi2_contingency, fisher_exact


GDC_CASES_URL = "https://api.gdc.cancer.gov/cases"
CBIO = "https://www.cbioportal.org/api"
PAN_STUDY = "brca_tcga_pan_can_atlas_2018"
LEGACY_STUDY = "brca_tcga"
PAN_MUT_PROFILE = "brca_tcga_pan_can_atlas_2018_mutations"
GENES = {"TP53": 7157, "PIK3CA": 5290, "BRCA1": 672, "BRCA2": 675}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cluster-assignments",
        default="results/brca_image_clustering_20260430_v1/slide_cluster_assignments_20260430_v1.csv",
    )
    parser.add_argument("--output-dir", default="results/brca_cluster_clinical_mutation_20260430_v1")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def request_get(url: str, *, params: dict | None = None, timeout: int = 60) -> requests.Response:
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r


def request_post(url: str, *, params: dict | None = None, json_payload: dict | None = None, timeout: int = 60) -> requests.Response:
    r = requests.post(url, params=params, json=json_payload, timeout=timeout)
    r.raise_for_status()
    return r


def majority_cluster(slide_clusters: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for case_id, sub in slide_clusters.groupby("tcga_case_id"):
        counts = Counter(sub["best_cluster"])
        cluster, n = counts.most_common(1)[0]
        rows.append(
            {
                "tcga_case_id": case_id,
                "majority_cluster": cluster,
                "n_slides": len(sub),
                "n_majority_slides": n,
                "is_mixed_cluster_case": len(counts) > 1,
                "all_slide_clusters": ";".join(f"{k}:{v}" for k, v in sorted(counts.items())),
            }
        )
    return pd.DataFrame(rows)


def fetch_gdc_clinical(case_ids: list[str], timeout: int) -> tuple[pd.DataFrame, dict]:
    fields = ",".join(
        [
            "case_id",
            "submitter_id",
            "demographic.vital_status",
            "demographic.days_to_death",
            "diagnoses.age_at_diagnosis",
            "diagnoses.ajcc_pathologic_stage",
            "diagnoses.tumor_grade",
            "diagnoses.days_to_last_follow_up",
            "follow_ups.days_to_follow_up",
        ]
    )
    filters = {
        "op": "and",
        "content": [
            {"op": "=", "content": {"field": "project.project_id", "value": "TCGA-BRCA"}},
            {"op": "in", "content": {"field": "submitter_id", "value": case_ids}},
        ],
    }
    payload = {"filters": filters, "fields": fields, "format": "JSON", "size": len(case_ids) + 20}
    data = request_post(GDC_CASES_URL, json_payload=payload, timeout=timeout).json()["data"]
    rows = []
    for hit in data["hits"]:
        diag = (hit.get("diagnoses") or [{}])[0]
        demo = hit.get("demographic") or {}
        follow_ups = hit.get("follow_ups") or []
        follow_days = [fu.get("days_to_follow_up") for fu in follow_ups if fu.get("days_to_follow_up") is not None]
        age_days = diag.get("age_at_diagnosis")
        days_to_death = demo.get("days_to_death")
        days_lfu = diag.get("days_to_last_follow_up")
        rows.append(
            {
                "tcga_case_id": hit.get("submitter_id"),
                "gdc_case_uuid": hit.get("case_id"),
                "age_at_diagnosis_years": round(age_days / 365.25, 2) if age_days else np.nan,
                "gdc_stage": diag.get("ajcc_pathologic_stage"),
                "gdc_grade": diag.get("tumor_grade"),
                "gdc_vital_status": demo.get("vital_status"),
                "gdc_days_to_death": days_to_death,
                "gdc_days_to_last_follow_up": days_lfu if days_lfu is not None else (max(follow_days) if follow_days else np.nan),
            }
        )
    df = pd.DataFrame(rows)
    meta = {"source": "GDC cases endpoint", "requested_cases": len(case_ids), "downloaded_cases": len(df)}
    return df, meta


def fetch_cbio_clinical(study_id: str, ids: list[str], clinical_data_type: str, timeout: int) -> pd.DataFrame:
    url = f"{CBIO}/studies/{study_id}/clinical-data/fetch"
    data = request_post(
        url,
        params={"clinicalDataType": clinical_data_type, "projection": "DETAILED"},
        json_payload={"ids": ids},
        timeout=timeout,
    ).json()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(
        [
            {
                "patientId": row.get("patientId"),
                "sampleId": row.get("sampleId"),
                "attributeId": row.get("clinicalAttribute", {}).get("clinicalAttributeId"),
                "value": row.get("value"),
            }
            for row in data
        ]
    )
    id_col = "patientId" if clinical_data_type == "PATIENT" else "sampleId"
    pivot = df.pivot_table(index=id_col, columns="attributeId", values="value", aggfunc="first").reset_index()
    if clinical_data_type == "PATIENT":
        pivot = pivot.rename(columns={"patientId": "tcga_case_id"})
    return pivot


def fetch_cbio_samples(case_ids: list[str], timeout: int) -> pd.DataFrame:
    data = request_get(
        f"{CBIO}/studies/{PAN_STUDY}/samples",
        params={"projection": "SUMMARY", "pageSize": 2000},
        timeout=timeout,
    ).json()
    df = pd.DataFrame(data)
    df = df[df["patientId"].isin(case_ids)].copy()
    df["is_primary"] = df["sampleId"].astype(str).str.endswith("-01")
    df = df.sort_values(["patientId", "is_primary", "sampleId"], ascending=[True, False, True])
    return df.drop_duplicates("patientId")


def fetch_mutations(sample_ids: list[str], timeout: int) -> pd.DataFrame:
    url = f"{CBIO}/molecular-profiles/{PAN_MUT_PROFILE}/mutations/fetch"
    payload = {"entrezGeneIds": list(GENES.values()), "sampleIds": sample_ids}
    data = request_post(url, params={"projection": "DETAILED"}, json_payload=payload, timeout=timeout).json()
    if not data:
        return pd.DataFrame(columns=["patientId", "sampleId", "gene", "mutationType", "proteinChange"])
    return pd.DataFrame(
        [
            {
                "tcga_case_id": row.get("patientId"),
                "sampleId": row.get("sampleId"),
                "gene": row.get("gene", {}).get("hugoGeneSymbol"),
                "mutationType": row.get("mutationType"),
                "proteinChange": row.get("proteinChange"),
            }
            for row in data
        ]
    )


def mutation_binary(case_ids: Iterable[str], mutations: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({"tcga_case_id": sorted(set(case_ids))})
    for gene in GENES:
        mutated = set(mutations.loc[mutations["gene"] == gene, "tcga_case_id"]) if not mutations.empty else set()
        out[f"{gene}_mut"] = out["tcga_case_id"].isin(mutated).astype(int)
    out["any_target_gene_mut"] = out[[f"{g}_mut" for g in GENES]].any(axis=1).astype(int)
    return out


def clean_stage(stage: object) -> str:
    if pd.isna(stage):
        return "Unknown"
    s = str(stage).replace("Stage ", "").strip()
    return s if s else "Unknown"


def event_from_os_status(value: object) -> float:
    if pd.isna(value):
        return np.nan
    s = str(value).upper()
    return 1.0 if "DECEASED" in s or s.startswith("1") or "DEAD" in s else 0.0


def add_survival_fields(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "OS_MONTHS" in df:
        df["os_months"] = pd.to_numeric(df["OS_MONTHS"], errors="coerce")
        df["os_event"] = df["OS_STATUS"].map(event_from_os_status) if "OS_STATUS" in df else np.nan
    else:
        days = pd.to_numeric(df["gdc_days_to_death"], errors="coerce").fillna(
            pd.to_numeric(df["gdc_days_to_last_follow_up"], errors="coerce")
        )
        df["os_months"] = days / 30.4375
        df["os_event"] = df["gdc_vital_status"].map(lambda x: 1.0 if str(x).lower() == "dead" else 0.0)
    df["stage_clean"] = df.get("gdc_stage", pd.Series(index=df.index, dtype=object)).map(clean_stage)
    return df


def km_curve(time: np.ndarray, event: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    valid = ~(np.isnan(time) | np.isnan(event))
    time = np.asarray(time[valid], dtype=float)
    event = np.asarray(event[valid], dtype=int)
    if len(time) == 0:
        return np.array([]), np.array([])
    event_times = np.sort(np.unique(time[event == 1]))
    xs = [0.0]
    ys = [1.0]
    surv = 1.0
    for t in event_times:
        at_risk = np.sum(time >= t)
        deaths = np.sum((time == t) & (event == 1))
        if at_risk > 0:
            surv *= 1.0 - deaths / at_risk
        xs.extend([t, t])
        ys.extend([ys[-1], surv])
    return np.array(xs), np.array(ys)


def plot_km(df: pd.DataFrame, output_dir: Path) -> None:
    plt.figure(figsize=(8, 6))
    for cluster, sub in df.groupby("majority_cluster"):
        x, y = km_curve(sub["os_months"].to_numpy(dtype=float), sub["os_event"].to_numpy(dtype=float))
        if len(x):
            plt.step(x, y, where="post", label=f"{cluster} (n={sub['os_months'].notna().sum()})")
    plt.xlabel("Overall survival (months)")
    plt.ylabel("Survival probability")
    plt.ylim(0, 1.03)
    plt.title("BRCA Image Cluster Kaplan-Meier")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "cluster_kaplan_meier_os_20260430_v1.png", dpi=180)
    plt.close()


def distribution_table(df: pd.DataFrame, col: str, output_dir: Path, name: str) -> pd.DataFrame:
    if col not in df:
        out = pd.DataFrame()
    else:
        out = pd.crosstab(df["majority_cluster"], df[col].fillna("Unknown"), normalize="index") * 100
        out = out.round(2).reset_index()
    out.to_csv(output_dir / f"cluster_{name}_distribution_20260430_v1.csv", index=False)
    return out


def mutation_frequency(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    cols = [f"{g}_mut" for g in GENES]
    rows = []
    for cluster, sub in df.groupby("majority_cluster"):
        row = {"majority_cluster": cluster, "n_cases": len(sub)}
        for col in cols:
            row[col.replace("_mut", "_mut_pct")] = round(float(sub[col].mean() * 100), 2)
            row[col.replace("_mut", "_mut_n")] = int(sub[col].sum())
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "cluster_mutation_frequency_20260430_v1.csv", index=False)
    return out


def association_tests(df: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    rows = []
    for col in ["stage_clean", "SUBTYPE", "ER_STATUS_BY_IHC", "PR_STATUS_BY_IHC", "IHC_HER2", "HER2_FISH_STATUS"]:
        if col in df and df[col].notna().any():
            tab = pd.crosstab(df["majority_cluster"], df[col].fillna("Unknown"))
            if tab.shape[0] > 1 and tab.shape[1] > 1:
                chi2, p, dof, _ = chi2_contingency(tab)
                rows.append({"feature": col, "test": "chi2", "p_value": p, "dof": dof})
    for gene in GENES:
        col = f"{gene}_mut"
        tab = pd.crosstab(df["majority_cluster"], df[col])
        if tab.shape[0] > 1 and tab.shape[1] > 1:
            chi2, p, dof, _ = chi2_contingency(tab)
            rows.append({"feature": col, "test": "chi2", "p_value": p, "dof": dof})
    out = pd.DataFrame(rows).sort_values("p_value") if rows else pd.DataFrame()
    out.to_csv(output_dir / "cluster_association_tests_20260430_v1.csv", index=False)
    return out


def link_drugs_to_clusters(df: pd.DataFrame, top30_path: Path, drug_anno_path: Path, output_dir: Path) -> pd.DataFrame:
    top30 = pd.read_csv(top30_path)
    anno = pd.read_parquet(drug_anno_path)
    top = top30.merge(anno, left_on="canonical_drug_id", right_on="DRUG_ID", how="left")
    rows = []
    for cluster, sub in df.groupby("majority_cluster"):
        mut_rates = {g: float(sub[f"{g}_mut"].mean()) for g in GENES}
        subtype_top = sub["SUBTYPE"].dropna().astype(str).value_counts().head(2).to_dict() if "SUBTYPE" in sub else {}
        candidate_pathways = set()
        rationale = []
        if mut_rates["PIK3CA"] >= 0.2:
            candidate_pathways.add("PI3K/MTOR signaling")
            rationale.append(f"PIK3CA mutation {mut_rates['PIK3CA']:.0%}")
        if mut_rates["TP53"] >= 0.2:
            candidate_pathways.update(["p53 pathway", "DNA replication"])
            rationale.append(f"TP53 mutation {mut_rates['TP53']:.0%}")
        if mut_rates["BRCA1"] > 0 or mut_rates["BRCA2"] > 0:
            candidate_pathways.update(["DNA replication", "Genome integrity"])
            rationale.append(f"BRCA1/2 mutation {(mut_rates['BRCA1'] + mut_rates['BRCA2']):.0%}")
        if any("Basal" in k for k in subtype_top):
            candidate_pathways.update(["DNA replication", "Cell cycle"])
            rationale.append(f"Basal-enriched subtype {subtype_top}")
        if not candidate_pathways:
            candidate_pathways.update(["Other", "DNA replication"])
            rationale.append("No strong target-gene enrichment detected; keep broad Top30 exploratory set")

        candidates = top[top["PATHWAY_NAME"].isin(candidate_pathways)].head(8)
        for _, drug in candidates.iterrows():
            rows.append(
                {
                    "majority_cluster": cluster,
                    "cluster_n_cases": len(sub),
                    "drug_rank": drug.get("rank"),
                    "drug_name": drug.get("drug_name"),
                    "canonical_drug_id": drug.get("canonical_drug_id"),
                    "target": drug.get("PUTATIVE_TARGET"),
                    "pathway": drug.get("PATHWAY_NAME"),
                    "rationale": "; ".join(rationale),
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "cluster_top30_drug_hypotheses_20260430_v1.csv", index=False)
    return out


def write_report(
    output_dir: Path,
    meta: dict,
    merged: pd.DataFrame,
    stage_dist: pd.DataFrame,
    subtype_dist: pd.DataFrame,
    mutation_freq: pd.DataFrame,
    assoc: pd.DataFrame,
    drug_links: pd.DataFrame,
) -> None:
    lines = [
        "# BRCA Image Cluster Clinical/Mutation Analysis",
        "",
        "## Downloads",
        "",
        f"- GDC clinical cases: {meta['gdc']['downloaded_cases']}/{meta['gdc']['requested_cases']}",
        f"- cBioPortal PanCancer clinical matched cases: {meta['cbio_pan_matched_cases']}",
        f"- cBioPortal legacy receptor matched cases: {meta['cbio_legacy_matched_cases']}",
        f"- cBioPortal mutation rows: {meta['mutation_rows']}",
        "",
        "## Case Coverage",
        "",
        f"- Clustered TCGA cases: {merged['tcga_case_id'].nunique()}",
        f"- Cases with OS months: {int(merged['os_months'].notna().sum())}",
        f"- Cases with subtype: {int(merged['SUBTYPE'].notna().sum()) if 'SUBTYPE' in merged else 0}",
        "",
        "## Stage Distribution (%)",
        "",
        stage_dist.to_markdown(index=False) if not stage_dist.empty else "No stage data.",
        "",
        "## Molecular Subtype Distribution (%)",
        "",
        subtype_dist.to_markdown(index=False) if not subtype_dist.empty else "No subtype data.",
        "",
        "## Mutation Frequency",
        "",
        mutation_freq.to_markdown(index=False),
        "",
        "## Association Tests",
        "",
        assoc.head(12).to_markdown(index=False) if not assoc.empty else "No association tests available.",
        "",
        "## Top30 Drug Hypotheses by Cluster",
        "",
        drug_links.head(30).to_markdown(index=False) if not drug_links.empty else "No drug hypotheses generated.",
        "",
        "## Note",
        "",
        "Drug links are hypothesis-generating only. They map cluster-enriched subtype/mutation patterns to Top30 drug target/pathway annotations; they are not patient-level response predictions.",
        "",
    ]
    (output_dir / "brca_cluster_clinical_mutation_report_20260430_v1.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slide_clusters = pd.read_csv(args.cluster_assignments)
    case_clusters = majority_cluster(slide_clusters)
    case_ids = sorted(case_clusters["tcga_case_id"].unique())

    gdc, gdc_meta = fetch_gdc_clinical(case_ids, args.timeout)
    gdc.to_csv(output_dir / "gdc_brca_clinical_raw_20260430_v1.csv", index=False)

    pan = fetch_cbio_clinical(PAN_STUDY, case_ids, "PATIENT", args.timeout)
    pan.to_csv(output_dir / "cbio_brca_pancan_patient_clinical_20260430_v1.csv", index=False)

    legacy = fetch_cbio_clinical(LEGACY_STUDY, case_ids, "PATIENT", args.timeout)
    legacy.to_csv(output_dir / "cbio_brca_legacy_receptor_clinical_20260430_v1.csv", index=False)

    samples = fetch_cbio_samples(case_ids, args.timeout)
    samples.to_csv(output_dir / "cbio_brca_pancan_samples_matched_20260430_v1.csv", index=False)

    mutations = fetch_mutations(samples["sampleId"].tolist(), args.timeout)
    mutations.to_csv(output_dir / "cbio_brca_target_gene_mutations_20260430_v1.csv", index=False)
    mut_bin = mutation_binary(case_ids, mutations)

    merged = case_clusters.merge(gdc, on="tcga_case_id", how="left")
    merged = merged.merge(pan, on="tcga_case_id", how="left", suffixes=("", "_pan"))
    receptor_cols = [
        "tcga_case_id",
        "ER_STATUS_BY_IHC",
        "PR_STATUS_BY_IHC",
        "IHC_HER2",
        "HER2_FISH_STATUS",
        "HER2_COPY_NUMBER",
        "HISTOLOGICAL_SUBTYPE",
    ]
    legacy_keep = legacy[[c for c in receptor_cols if c in legacy.columns]].copy() if not legacy.empty else pd.DataFrame({"tcga_case_id": []})
    merged = merged.merge(legacy_keep, on="tcga_case_id", how="left")
    merged = merged.merge(mut_bin, on="tcga_case_id", how="left")
    for gene in GENES:
        merged[f"{gene}_mut"] = merged[f"{gene}_mut"].fillna(0).astype(int)
    merged = add_survival_fields(merged)
    merged.to_csv(output_dir / "brca_cluster_clinical_mutation_merged_20260430_v1.csv", index=False)

    plot_km(merged, output_dir)
    stage_dist = distribution_table(merged, "stage_clean", output_dir, "stage")
    subtype_dist = distribution_table(merged, "SUBTYPE", output_dir, "subtype")
    distribution_table(merged, "ER_STATUS_BY_IHC", output_dir, "er_status")
    distribution_table(merged, "PR_STATUS_BY_IHC", output_dir, "pr_status")
    distribution_table(merged, "IHC_HER2", output_dir, "her2_ihc")
    mut_freq = mutation_frequency(merged, output_dir)
    assoc = association_tests(merged, output_dir)
    drug_links = link_drugs_to_clusters(
        merged,
        Path("brca_data/brca_directive_top30_tiered_candidates.csv"),
        Path("brca_data/gdsc2_drug_annotation_master_20260406.parquet"),
        output_dir,
    )

    meta = {
        "gdc": gdc_meta,
        "cbio_pan_matched_cases": int(pan["tcga_case_id"].isin(case_ids).sum()) if not pan.empty else 0,
        "cbio_legacy_matched_cases": int(legacy["tcga_case_id"].isin(case_ids).sum()) if not legacy.empty else 0,
        "mutation_rows": int(len(mutations)),
        "target_genes": list(GENES),
        "sources": {
            "gdc": GDC_CASES_URL,
            "cbio_pan_study": PAN_STUDY,
            "cbio_legacy_study": LEGACY_STUDY,
            "cbio_mutation_profile": PAN_MUT_PROFILE,
        },
    }
    write_json(output_dir / "clinical_mutation_download_summary_20260430_v1.json", meta)
    write_report(output_dir, meta, merged, stage_dist, subtype_dist, mut_freq, assoc, drug_links)

    print("[done]", output_dir)
    print(json.dumps(meta, indent=2))
    print(mut_freq.to_string(index=False))


if __name__ == "__main__":
    main()
