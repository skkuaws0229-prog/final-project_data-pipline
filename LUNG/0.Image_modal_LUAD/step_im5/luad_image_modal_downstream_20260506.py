from __future__ import annotations

import json
import math
import os
import re
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


DATE_TAG = "20260506"
DRIVER_GENES = {
    "EGFR": 1956,
    "KRAS": 3845,
    "ALK": 238,
    "STK11": 6794,
    "KEAP1": 9817,
    "TP53": 7157,
}
CBIO_STUDY_ID = "luad_tcga_pan_can_atlas_2018"
CBIO_MUT_PROFILE = f"{CBIO_STUDY_ID}_mutations"
CBIO_SAMPLE_LIST = f"{CBIO_STUDY_ID}_sequenced"


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


ROOT = package_root()
OUT_ROOT = ROOT / "local_data" / "luad_image_modal_20260501_v1" / "0.Image_modal_LUAD"
MPL_DIR = OUT_ROOT / ".mplconfig"
MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_DIR))


def tcga_patient_barcode(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", value.upper())
    return match.group(1) if match else None


def ensure_dirs() -> dict[str, Path]:
    dirs = {
        "root": OUT_ROOT,
        "step_im2": OUT_ROOT / "step_im2",
        "step_im3": OUT_ROOT / "step_im3",
        "step_im4a": OUT_ROOT / "step_im4a",
        "step_im4b": OUT_ROOT / "step_im4b",
        "step_im4c": OUT_ROOT / "step_im4c",
        "step_im5": OUT_ROOT / "step_im5",
        "raw": OUT_ROOT / "_raw_downloads",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def read_embeddings(embedding_root: Path) -> tuple[pd.DataFrame, np.ndarray]:
    files = sorted(embedding_root.rglob("all_slide_embeddings_20260430_v1.parquet"))
    if not files:
        raise FileNotFoundError(f"No slide embedding parquet files under {embedding_root}")
    frames = []
    for path in files:
        frame = pd.read_parquet(path)
        frame["source_part"] = path.parents[1].name
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    df["patient_barcode"] = df["slide_id"].map(tcga_patient_barcode)
    df = df.dropna(subset=["patient_barcode"]).drop_duplicates(subset=["slide_id"], keep="last")
    emb_cols = [c for c in df.columns if c.startswith("emb_")]
    if not emb_cols:
        raise ValueError("No emb_* columns found in slide embeddings")
    emb_cols = sorted(emb_cols, key=lambda x: int(x.split("_", 1)[1]))
    matrix = df[emb_cols].to_numpy(dtype=np.float32)
    order = np.argsort(df["slide_id"].to_numpy())
    df = df.iloc[order].reset_index(drop=True)
    matrix = matrix[order]
    return df, matrix


def download_cbio_clinical(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    base = "https://www.cbioportal.org/api"
    out = {}
    for level in ["PATIENT", "SAMPLE"]:
        path = raw_dir / f"cbio_luad_{level.lower()}_clinical_long_{DATE_TAG}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            response = session.get(
                f"{base}/studies/{CBIO_STUDY_ID}/clinical-data",
                params={"clinicalDataType": level, "projection": "DETAILED"},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload), encoding="utf-8")
        long_df = pd.DataFrame(payload)
        id_col = "patientId" if level == "PATIENT" else "sampleId"
        wide = long_df.pivot_table(
            index=["patientId"] if level == "PATIENT" else ["patientId", "sampleId"],
            columns="clinicalAttributeId",
            values="value",
            aggfunc="first",
        ).reset_index()
        out[level] = wide
    return out["PATIENT"], out["SAMPLE"]


def download_cbio_mutations(raw_dir: Path) -> pd.DataFrame:
    path = raw_dir / f"cbio_luad_driver_mutations_{DATE_TAG}.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        session = requests.Session()
        session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        response = session.post(
            f"https://www.cbioportal.org/api/molecular-profiles/{CBIO_MUT_PROFILE}/mutations/fetch",
            json={"sampleListId": CBIO_SAMPLE_LIST, "entrezGeneIds": list(DRIVER_GENES.values())},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        path.write_text(json.dumps(payload), encoding="utf-8")
    mut = pd.DataFrame(payload)
    if mut.empty:
        return pd.DataFrame(columns=["patientId", "sampleId", "hugoGeneSymbol", "mutationType", "proteinChange"])
    entrez_to_gene = {v: k for k, v in DRIVER_GENES.items()}
    mut["hugoGeneSymbol"] = mut["entrezGeneId"].map(entrez_to_gene)
    return mut


def infer_subtype(row: pd.Series) -> str:
    subtype = str(row.get("SUBTYPE", "")).strip()
    if subtype and subtype.lower() not in {"nan", "none", "not reported", "luad", "lung adenocarcinoma"}:
        return subtype
    if bool(row.get("EGFR_mut", False)) or bool(row.get("ALK_mut", False)):
        return "TRU_proxy"
    if bool(row.get("KRAS_mut", False)) or bool(row.get("STK11_mut", False)) or bool(row.get("KEAP1_mut", False)):
        return "PP_proxy"
    if bool(row.get("TP53_mut", False)):
        return "PI_proxy"
    return "Unassigned"


def plot_pca(clusters: pd.DataFrame, out_path: Path, best_k: int, best_sil: float) -> None:
    plt.figure(figsize=(7.2, 5.4))
    sns.scatterplot(data=clusters, x="pca1", y="pca2", hue="cluster", palette="tab10", s=58)
    plt.title(f"TCGA-LUAD WSI Embedding PCA Clusters (K={best_k}, silhouette={best_sil:.3f})")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()


def chi_square_table(df: pd.DataFrame, column: str) -> dict[str, object]:
    table = pd.crosstab(df["cluster"], df[column].fillna("Unknown"))
    if table.shape[0] < 2 or table.shape[1] < 2:
        return {"variable": column, "chi2": np.nan, "p_value": np.nan, "dof": np.nan}
    chi2, pval, dof, _ = chi2_contingency(table)
    return {"variable": column, "chi2": float(chi2), "p_value": float(pval), "dof": int(dof)}


def survival_event(status: object) -> float:
    text = str(status).upper()
    return 1.0 if "DECEASED" in text or text.startswith("1:") else 0.0


def run_survival(analysis: pd.DataFrame, out_dir: Path) -> dict[str, float]:
    surv = analysis.copy()
    surv["OS_MONTHS"] = pd.to_numeric(surv.get("OS_MONTHS"), errors="coerce")
    surv["OS_EVENT"] = surv.get("OS_STATUS").map(survival_event)
    surv = surv.dropna(subset=["OS_MONTHS", "OS_EVENT", "cluster"])
    if surv.empty or surv["cluster"].nunique() < 2:
        return {"n": int(len(surv)), "logrank_p_value": np.nan}
    kmf = KaplanMeierFitter()
    plt.figure(figsize=(7.4, 5.4))
    for cluster_id, grp in surv.groupby("cluster"):
        kmf.fit(grp["OS_MONTHS"], event_observed=grp["OS_EVENT"], label=f"Cluster {cluster_id} (n={len(grp)})")
        kmf.plot_survival_function(ci_show=False)
    result = multivariate_logrank_test(surv["OS_MONTHS"], surv["cluster"], surv["OS_EVENT"])
    plt.title(f"TCGA-LUAD Overall Survival by WSI Cluster (log-rank p={result.p_value:.3g})")
    plt.xlabel("Months")
    plt.ylabel("Overall survival probability")
    plt.tight_layout()
    plt.savefig(out_dir / "cluster_survival_km.png", dpi=180)
    plt.close()
    return {"n": int(len(surv)), "logrank_p_value": float(result.p_value), "test_statistic": float(result.test_statistic)}


def classify_tier(row: pd.Series) -> tuple[str, str]:
    existing = str(row.get("tier_code", "")).strip()
    name = str(row.get("drug_name_display", row.get("DRUG_NAME", ""))).strip()
    smiles = str(row.get("canonical_smiles", "")).strip()
    ct_count = pd.to_numeric(row.get("ct_match_count", 0), errors="coerce")
    if existing == "Tier1":
        return "Tier1", "Current/reference lung cancer therapy; validation control."
    if existing == "Tier2" or (not math.isnan(float(ct_count)) and float(ct_count) > 0):
        return "Tier2", "Evidence of lung cancer clinical investigation, but not current standard-control tier."
    if not name or name.lower() == "nan" or not smiles or smiles.lower() == "nan":
        return "Tier4", "Excluded or weakly actionable because drug identity/structure is incomplete."
    if existing == "Tier4":
        return "Tier4", "Excluded by prior LUNG tiering as weak/non-actionable for this protocol."
    return "Tier3", "Named repurposing candidate without direct current-lung-treatment status."


def cluster_profile(row: pd.Series) -> tuple[str, str, list[str]]:
    muts = {g: float(row.get(f"{g}_mut_rate", 0.0)) for g in DRIVER_GENES}
    if max(muts["EGFR"], muts["ALK"]) >= max(muts["KRAS"], muts["STK11"], muts["KEAP1"], muts["TP53"]):
        return "TRU/RTK-like WSI Cluster", "EGFR/ALK RTK signaling and differentiated terminal-respiratory-unit biology", ["EGFR", "ALK", "ERBB", "RTK", "MAPK"]
    if muts["TP53"] >= max(muts["KRAS"], muts["STK11"], muts["KEAP1"]):
        return "PI/TP53-Proliferative-like WSI Cluster", "TP53/cell-cycle/proliferative injury biology", ["TP53", "CDK", "DNA", "TOP", "MITOSIS", "MICROTUBULE"]
    if max(muts["KRAS"], muts["STK11"], muts["KEAP1"]) > 0:
        return "PP/KRAS-LKB1-Oxidative-Stress-like WSI Cluster", "KRAS-MAPK, STK11/LKB1 metabolism, KEAP1/NRF2 oxidative-stress biology", ["KRAS", "MEK", "ERK", "MAPK", "STK11", "KEAP1", "NRF2"]
    return "Mixed/Unassigned WSI Cluster", "Mixed LUAD histology without a dominant driver proxy", ["MAPK", "CELL CYCLE", "RTK"]


def drug_cluster_mapping(top30: pd.DataFrame, cluster_profiles: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    tier_rows = []
    for _, row in top30.iterrows():
        tier, reason = classify_tier(row)
        out = row.to_dict()
        out["luad_4tier"] = tier
        out["luad_4tier_rationale"] = reason
        tier_rows.append(out)
    tiered = pd.DataFrame(tier_rows)

    mapping_rows = []
    for _, drug in tiered.iterrows():
        target_text = " ".join(str(drug.get(c, "")) for c in ["TARGET", "TARGET_PATHWAY", "prism_moa", "drug_name_display", "DRUG_NAME"]).upper()
        for _, profile in cluster_profiles.iterrows():
            keywords = [x.strip().upper() for x in str(profile["Candidate_Targets"]).split(";")]
            matches = [kw for kw in keywords if kw and kw in target_text]
            broad_match = False
            if "Mitosis".upper() in target_text and "MITOSIS" in keywords:
                broad_match = True
            if "Other".upper() in target_text and str(drug.get("luad_4tier")) in {"Tier1", "Tier2", "Tier3"}:
                broad_match = True
            if matches or broad_match:
                mapping_rows.append(
                    {
                        "cluster": int(profile["cluster"]),
                        "cluster_label": profile["Cluster_Label"],
                        "dominant_pathway": profile["Dominant_Pathway"],
                        "drug_name": drug.get("drug_name_display", drug.get("DRUG_NAME")),
                        "canonical_drug_id": drug.get("canonical_drug_id"),
                        "target": drug.get("TARGET"),
                        "target_pathway": drug.get("TARGET_PATHWAY"),
                        "moa": drug.get("prism_moa"),
                        "luad_4tier": drug.get("luad_4tier"),
                        "match_keywords": "; ".join(matches) if matches else "broad_lung_tier_context",
                        "hypothesis": (
                            f"{drug.get('drug_name_display', drug.get('DRUG_NAME'))} is a {drug.get('luad_4tier')} "
                            f"candidate for {profile['Cluster_Label']} through {profile['Dominant_Pathway']}."
                        ),
                    }
                )
    return tiered, pd.DataFrame(mapping_rows)


def main() -> None:
    dirs = ensure_dirs()
    embedding_root = ROOT / "local_data" / "luad_image_modal_20260501_v1" / "output" / "embeddings_mid"
    top30_path = ROOT / "local_data" / "luad_image_modal_20260501_v1" / "input" / "luad_top30_tiered_candidates.csv"

    slide_df, emb = read_embeddings(embedding_root)
    np.save(dirs["step_im2"] / "all_slide_embeddings_luad_merged.npy", emb)
    slide_df.to_csv(dirs["step_im2"] / "all_slide_embeddings_luad_merged_metadata.csv", index=False)
    qc = {
        "requested_shape_note": "User requested 254 x 1536d; available Step3 parquet contains 250 slide rows.",
        "actual_shape": [int(emb.shape[0]), int(emb.shape[1])],
        "n_nan": int(np.isnan(emb).sum()),
        "n_pos_inf": int(np.isposinf(emb).sum()),
        "n_neg_inf": int(np.isneginf(emb).sum()),
        "n_unique_patients": int(slide_df["patient_barcode"].nunique()),
        "n_source_parts": int(slide_df["source_part"].nunique()),
    }
    (dirs["step_im2"] / "embedding_merge_qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")

    x = StandardScaler().fit_transform(emb)
    opt_rows, labels_by_k = [], {}
    for k in [3, 4, 5]:
        km = KMeans(n_clusters=k, random_state=42, n_init=50)
        labels = km.fit_predict(x)
        sil = silhouette_score(x, labels)
        opt_rows.append({"k": k, "silhouette": float(sil), "inertia": float(km.inertia_)})
        labels_by_k[k] = labels
    opt = pd.DataFrame(opt_rows)
    best_k = int(opt.sort_values("silhouette", ascending=False).iloc[0]["k"])
    labels = labels_by_k[best_k]
    pca = PCA(n_components=2, random_state=42)
    xy = pca.fit_transform(x)
    clusters = slide_df[["slide_id", "patient_barcode", "source_part"]].copy()
    clusters["cluster"] = labels
    clusters["pca1"] = xy[:, 0]
    clusters["pca2"] = xy[:, 1]
    patient_clusters = clusters.sort_values(["patient_barcode", "slide_id"]).drop_duplicates("patient_barcode")
    opt.to_csv(dirs["step_im3"] / "clustering_optimization.csv", index=False)
    clusters.to_csv(dirs["step_im3"] / "slide_clusters.csv", index=False)
    patient_clusters.to_csv(dirs["step_im3"] / "patient_clusters.csv", index=False)
    plot_pca(clusters, dirs["step_im3"] / "pca_cluster_plot.png", best_k, float(opt["silhouette"].max()))
    (dirs["step_im3"] / "step_im3_clustering_report.md").write_text(
        "# LUAD Step IM-3 Clustering\n\n"
        f"- Slide embeddings: {emb.shape[0]}\n"
        f"- Embedding dimension: {emb.shape[1]}\n"
        f"- Unique TCGA patients: {patient_clusters['patient_barcode'].nunique()}\n"
        f"- Candidate K: 3, 4, 5\n"
        f"- Best K by silhouette: {best_k}\n"
        f"- Best silhouette: {opt['silhouette'].max():.4f}\n",
        encoding="utf-8",
    )

    patient_clin, sample_clin = download_cbio_clinical(dirs["raw"])
    mutations = download_cbio_mutations(dirs["raw"])
    patient_clin.to_csv(dirs["raw"] / "cbio_luad_patient_clinical_wide.csv", index=False)
    sample_clin.to_csv(dirs["raw"] / "cbio_luad_sample_clinical_wide.csv", index=False)
    mutations.to_csv(dirs["raw"] / "cbio_luad_driver_mutations.csv", index=False)

    driver_matrix = pd.DataFrame({"patientId": sorted(patient_clusters["patient_barcode"].unique())})
    if not mutations.empty:
        mut_flags = mutations.assign(mutated=True).pivot_table(index="patientId", columns="hugoGeneSymbol", values="mutated", aggfunc="max", fill_value=False)
        mut_flags = mut_flags.reindex(columns=list(DRIVER_GENES), fill_value=False).reset_index()
        driver_matrix = driver_matrix.merge(mut_flags, on="patientId", how="left")
    for gene in DRIVER_GENES:
        if gene not in driver_matrix.columns:
            driver_matrix[gene] = False
        driver_matrix[f"{gene}_mut"] = driver_matrix[gene].fillna(False).astype(bool)
        driver_matrix = driver_matrix.drop(columns=[gene])

    analysis = patient_clusters.rename(columns={"patient_barcode": "patientId"}).merge(patient_clin, on="patientId", how="left")
    analysis = analysis.merge(sample_clin.drop_duplicates("patientId"), on="patientId", how="left", suffixes=("", "_sample"))
    analysis = analysis.merge(driver_matrix, on="patientId", how="left")
    for gene in DRIVER_GENES:
        analysis[f"{gene}_mut"] = analysis[f"{gene}_mut"].fillna(False).astype(bool)
    analysis["molecular_subtype"] = analysis.apply(infer_subtype, axis=1)
    analysis.to_csv(dirs["step_im4a"] / "luad_cluster_clinical_mutation_table.csv", index=False)

    survival_stats = run_survival(analysis, dirs["step_im4a"])
    chi_rows = []
    for column in ["molecular_subtype", "AJCC_PATHOLOGIC_TUMOR_STAGE", "GRADE", "PATH_T_STAGE", "PATH_N_STAGE"]:
        if column in analysis.columns:
            chi_rows.append(chi_square_table(analysis, column))
    for gene in DRIVER_GENES:
        chi_rows.append(chi_square_table(analysis.assign(**{f"{gene}_mut": analysis[f"{gene}_mut"].map({True: "mut", False: "wt"})}), f"{gene}_mut"))
    pd.DataFrame(chi_rows).to_csv(dirs["step_im4a"] / "cluster_statistical_tests.csv", index=False)

    driver_freq = analysis.groupby("cluster")[[f"{g}_mut" for g in DRIVER_GENES]].mean().reset_index()
    driver_freq = driver_freq.rename(columns={f"{g}_mut": f"{g}_mut_rate" for g in DRIVER_GENES})
    driver_freq.to_csv(dirs["step_im4a"] / "cluster_driver_mutation_frequency.csv", index=False)
    pd.crosstab(analysis["cluster"], analysis["molecular_subtype"], normalize="index").to_csv(dirs["step_im4a"] / "cluster_molecular_subtype_distribution.csv")
    if "AJCC_PATHOLOGIC_TUMOR_STAGE" in analysis.columns:
        pd.crosstab(analysis["cluster"], analysis["AJCC_PATHOLOGIC_TUMOR_STAGE"], normalize="index").to_csv(dirs["step_im4a"] / "cluster_stage_distribution.csv")
    if "GRADE" in analysis.columns:
        pd.crosstab(analysis["cluster"], analysis["GRADE"], normalize="index").to_csv(dirs["step_im4a"] / "cluster_grade_distribution.csv")

    profile_rows = []
    for _, row in driver_freq.iterrows():
        label, pathway, targets = cluster_profile(row)
        row_out = row.to_dict()
        row_out.update({"Cluster_Label": label, "Dominant_Pathway": pathway, "Candidate_Targets": "; ".join(targets)})
        profile_rows.append(row_out)
    cluster_profiles = pd.DataFrame(profile_rows)
    cluster_profiles.to_csv(dirs["step_im4b"] / "luad_cluster_pathway_profiles.csv", index=False)

    top30 = pd.read_csv(top30_path)
    tiered, mapping = drug_cluster_mapping(top30, cluster_profiles)
    tiered.to_csv(dirs["step_im4c"] / "luad_top30_4tier_classification.csv", index=False)
    mapping.to_csv(dirs["step_im4c"] / "luad_top30_cluster_drug_hypotheses.csv", index=False)
    tiered.to_csv(OUT_ROOT / "luad_top30_4tier_classification.csv", index=False)
    mapping.to_csv(OUT_ROOT / "im4c_luad_cluster_drug_mapping.csv", index=False)

    report = [
        "# LUAD Image Modal Downstream Report",
        "",
        "## Embedding Merge",
        f"- Actual merged matrix: `{emb.shape[0]} x {emb.shape[1]}`",
        f"- NaN: `{qc['n_nan']}`, +Inf: `{qc['n_pos_inf']}`, -Inf: `{qc['n_neg_inf']}`",
        "- Note: request expected 254 rows; available LUAD Step3 parquet contains 250 rows.",
        "",
        "## Clustering",
        f"- Best K: `{best_k}` by silhouette.",
        f"- Silhouette table: `step_im3/clustering_optimization.csv`",
        "",
        "## Clinical / Mutation",
        "- Source: cBioPortal TCGA-LUAD PanCancer Atlas 2018 API.",
        "- Driver genes: EGFR, KRAS, ALK, STK11, KEAP1, TP53.",
        f"- Survival log-rank p-value: `{survival_stats.get('logrank_p_value')}`",
        "- Molecular subtype uses cBioPortal `SUBTYPE` when present; otherwise driver-proxy labels are used.",
        "",
        "## Drug Mapping",
        "- LUNG Top30 candidates were connected to WSI clusters by target/MoA/pathway keyword overlap and existing LUNG tier evidence.",
        "- This is a stratification hypothesis only, not direct patient-level drug-response inference.",
        "",
        "## WSI Cleanup",
        "- Raw WSI deletion was not executed automatically because it is destructive.",
        "- Suggested cleanup commands are in `step_im5/s3_cleanup_manifest.json`.",
    ]
    (OUT_ROOT / "step_im5_luad_image_modal_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    cleanup = {
        "raw_wsi_prefix": "s3://say2-4team/luad_image_modal_20260501_v1/wsi_raw/",
        "delete_command": "aws s3 rm s3://say2-4team/luad_image_modal_20260501_v1/wsi_raw/ --recursive",
        "status": "not_executed",
        "reason": "destructive cleanup requires explicit user confirmation after verifying Step3 and downstream outputs",
    }
    (dirs["step_im5"] / "s3_cleanup_manifest.json").write_text(json.dumps(cleanup, indent=2), encoding="utf-8")

    zip_path = dirs["step_im5"] / "luad_image_modal_downstream_results.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in OUT_ROOT.rglob("*"):
            if path.is_file() and path != zip_path:
                zf.write(path, path.relative_to(OUT_ROOT))
    summary = {
        "actual_embedding_shape": list(emb.shape),
        "best_k": best_k,
        "best_silhouette": float(opt["silhouette"].max()),
        "survival_logrank_p_value": survival_stats.get("logrank_p_value"),
        "output_root": str(OUT_ROOT),
        "zip": str(zip_path),
    }
    (OUT_ROOT / "luad_image_modal_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
