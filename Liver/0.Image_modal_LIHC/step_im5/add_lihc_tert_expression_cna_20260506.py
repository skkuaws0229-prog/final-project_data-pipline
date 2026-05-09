from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy.stats import chi2_contingency, kruskal


ROOT = Path(__file__).resolve().parents[1]
STEP_DIR = (
    ROOT
    / "local_data"
    / "lihc_image_modal_20260501_v1"
    / "0.Image_modal_LIHC"
    / "step_im4a"
)
STEP5_DIR = (
    ROOT
    / "local_data"
    / "lihc_image_modal_20260501_v1"
    / "0.Image_modal_LIHC"
    / "step_im5"
)

CLINICAL_TABLE = STEP_DIR / "lihc_cluster_clinical_mutation_table.csv"
EXPR_STATS_OUT = STEP_DIR / "cluster_tert_expression_stats.csv"
CNA_STATS_OUT = STEP_DIR / "cluster_tert_cna_stats.csv"
LINK_OUT = STEP_DIR / "cluster_tert_expression_survival_link.csv"
TESTS_OUT = STEP_DIR / "tert_expression_cna_statistical_tests.csv"
PLOT_OUT = STEP_DIR / "cluster_tert_mrna_expression_boxplot.png"
SUMMARY_OUT = STEP_DIR / "tert_expression_cna_summary.json"
REPORT_OUT = STEP_DIR / "tert_expression_cna_report.md"

CBIO_BASE = "https://www.cbioportal.org/api"
STUDY_ID = "lihc_tcga_pan_can_atlas_2018"
TERT_ENTREZ_ID = 7015
PROFILES = {
    "TERT_mrna_rsem": "lihc_tcga_pan_can_atlas_2018_rna_seq_v2_mrna",
    "TERT_mrna_zscore_diploid": "lihc_tcga_pan_can_atlas_2018_rna_seq_v2_mrna_median_Zscores",
    "TERT_mrna_zscore_all": "lihc_tcga_pan_can_atlas_2018_rna_seq_v2_mrna_median_all_sample_Zscores",
    "TERT_gistic_cna": "lihc_tcga_pan_can_atlas_2018_gistic",
    "TERT_log2_cna": "lihc_tcga_pan_can_atlas_2018_log2CNA",
}


def fetch_profile(profile_id: str, sample_ids: list[str]) -> pd.DataFrame:
    url = f"{CBIO_BASE}/molecular-profiles/{profile_id}/molecular-data/fetch"
    body: dict[str, Any] = {"entrezGeneIds": [TERT_ENTREZ_ID], "sampleIds": sample_ids}
    response = requests.post(
        url,
        params={"projection": "DETAILED"},
        json=body,
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload:
        return pd.DataFrame(columns=["sampleId", "patientId", "value"])
    return pd.DataFrame(payload)[["sampleId", "patientId", "value"]]


def survival_status_to_event(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.upper()
    return text.str.contains("DECEASED|DEAD|1:")


def main() -> None:
    STEP5_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLINICAL_TABLE)
    sample_ids = df["sampleId"].dropna().astype(str).drop_duplicates().tolist()

    fetched_counts: dict[str, int] = {}
    for column, profile_id in PROFILES.items():
        profile_df = fetch_profile(profile_id, sample_ids)
        fetched_counts[column] = int(profile_df["sampleId"].nunique()) if not profile_df.empty else 0
        profile_df = profile_df.rename(columns={"value": column})[["sampleId", column]]
        df = df.drop(columns=[column], errors="ignore").merge(profile_df, on="sampleId", how="left")

    df["TERT_cna_amplified"] = pd.to_numeric(df["TERT_gistic_cna"], errors="coerce") >= 1
    df["TERT_cna_high_level_amplified"] = pd.to_numeric(df["TERT_gistic_cna"], errors="coerce") >= 2
    df.to_csv(CLINICAL_TABLE, index=False)

    expr_col = "TERT_mrna_zscore_diploid"
    expr_rows = []
    for cluster, grp in df.groupby("cluster", dropna=False):
        values = pd.to_numeric(grp[expr_col], errors="coerce")
        expr_rows.append(
            {
                "cluster": cluster,
                "n_patients": int(len(grp)),
                "TERT_mrna_available_n": int(values.notna().sum()),
                "TERT_mrna_zscore_median": float(values.median()) if values.notna().any() else np.nan,
                "TERT_mrna_zscore_mean": float(values.mean()) if values.notna().any() else np.nan,
                "TERT_mrna_zscore_q1": float(values.quantile(0.25)) if values.notna().any() else np.nan,
                "TERT_mrna_zscore_q3": float(values.quantile(0.75)) if values.notna().any() else np.nan,
                "TERT_mrna_rsem_median": float(pd.to_numeric(grp["TERT_mrna_rsem"], errors="coerce").median()),
            }
        )
    expr_stats = pd.DataFrame(expr_rows).sort_values("cluster")
    expr_stats.to_csv(EXPR_STATS_OUT, index=False)

    cna_rows = []
    for cluster, grp in df.groupby("cluster", dropna=False):
        gistic = pd.to_numeric(grp["TERT_gistic_cna"], errors="coerce")
        log2cna = pd.to_numeric(grp["TERT_log2_cna"], errors="coerce")
        amplified = gistic >= 1
        high_amp = gistic >= 2
        cna_rows.append(
            {
                "cluster": cluster,
                "n_patients": int(len(grp)),
                "TERT_cna_available_n": int(gistic.notna().sum()),
                "TERT_cna_amp_n": int(amplified.sum()),
                "TERT_cna_amp_rate": float(amplified.mean()) if gistic.notna().any() else np.nan,
                "TERT_cna_high_amp_n": int(high_amp.sum()),
                "TERT_cna_high_amp_rate": float(high_amp.mean()) if gistic.notna().any() else np.nan,
                "TERT_log2_cna_median": float(log2cna.median()) if log2cna.notna().any() else np.nan,
                "TERT_log2_cna_mean": float(log2cna.mean()) if log2cna.notna().any() else np.nan,
            }
        )
    cna_stats = pd.DataFrame(cna_rows).sort_values("cluster")
    cna_stats.to_csv(CNA_STATS_OUT, index=False)

    link = expr_stats.merge(cna_stats, on=["cluster", "n_patients"], how="left")
    os_months = pd.to_numeric(df.get("OS_MONTHS"), errors="coerce")
    os_event = survival_status_to_event(df.get("OS_STATUS", pd.Series("", index=df.index)))
    survival_rows = []
    for cluster, grp in df.assign(_os_months=os_months, _os_event=os_event).groupby("cluster", dropna=False):
        survival_rows.append(
            {
                "cluster": cluster,
                "OS_available_n": int(grp["_os_months"].notna().sum()),
                "OS_months_median": float(grp["_os_months"].median()) if grp["_os_months"].notna().any() else np.nan,
                "OS_event_rate": float(grp["_os_event"].mean()),
            }
        )
    link = link.merge(pd.DataFrame(survival_rows), on="cluster", how="left")
    high_cluster = link.sort_values("TERT_mrna_zscore_median", ascending=False).iloc[0]["cluster"]
    link["TERT_expression_rank"] = link["TERT_mrna_zscore_median"].rank(ascending=False, method="dense").astype(int)
    link["interpretation"] = np.where(
        link["cluster"].eq(high_cluster),
        "highest_TERT_expression_cluster_telomerase_activity_proxy",
        "lower_TERT_expression_cluster",
    )
    link.to_csv(LINK_OUT, index=False)

    test_rows = []
    grouped_expr = [
        pd.to_numeric(grp[expr_col], errors="coerce").dropna().values
        for _, grp in df.groupby("cluster")
    ]
    if sum(len(v) > 0 for v in grouped_expr) >= 2:
        stat, p_value = kruskal(*grouped_expr)
        test_rows.append(
            {
                "variable": expr_col,
                "test": "Kruskal-Wallis",
                "statistic": float(stat),
                "p_value": float(p_value),
                "status": "tested",
                "note": "TERT mRNA expression z-score across image clusters.",
            }
        )

    grouped_log2 = [
        pd.to_numeric(grp["TERT_log2_cna"], errors="coerce").dropna().values
        for _, grp in df.groupby("cluster")
    ]
    if sum(len(v) > 0 for v in grouped_log2) >= 2:
        stat, p_value = kruskal(*grouped_log2)
        test_rows.append(
            {
                "variable": "TERT_log2_cna",
                "test": "Kruskal-Wallis",
                "statistic": float(stat),
                "p_value": float(p_value),
                "status": "tested",
                "note": "TERT log2 copy-number values across image clusters.",
            }
        )

    amp_table = pd.crosstab(df["cluster"], df["TERT_cna_amplified"])
    if amp_table.shape[1] == 2:
        stat, p_value, dof, _ = chi2_contingency(amp_table)
        test_rows.append(
            {
                "variable": "TERT_cna_amplified",
                "test": "Chi-squared",
                "statistic": float(stat),
                "p_value": float(p_value),
                "dof": int(dof),
                "status": "tested",
                "note": "GISTIC >= 1 amplification frequency across image clusters.",
            }
        )
    pd.DataFrame(test_rows).to_csv(TESTS_OUT, index=False)

    plot_data = [
        pd.to_numeric(grp[expr_col], errors="coerce").dropna().values
        for _, grp in df.sort_values("cluster").groupby("cluster")
    ]
    labels = [str(cluster) for cluster in sorted(df["cluster"].dropna().unique())]
    plt.figure(figsize=(7, 4.5))
    plt.boxplot(plot_data, labels=labels, showfliers=False, patch_artist=True)
    x_positions = np.arange(1, len(plot_data) + 1)
    rng = np.random.default_rng(20260506)
    for x, values in zip(x_positions, plot_data):
        jitter = rng.normal(0, 0.035, len(values))
        plt.scatter(np.full(len(values), x) + jitter, values, s=14, alpha=0.55)
    plt.axhline(0, color="#777777", linewidth=0.8, linestyle="--")
    plt.xlabel("LIHC image cluster")
    plt.ylabel("TERT mRNA z-score")
    plt.title("TCGA-LIHC TERT mRNA expression by image cluster")
    plt.tight_layout()
    plt.savefig(PLOT_OUT, dpi=200)
    plt.close()

    summary = {
        "cancer_type": "LIHC",
        "analysis_date": "2026-05-06",
        "local_patient_count": int(df["patientId"].nunique()),
        "local_sample_count": int(len(df)),
        "cbioportal_study_id": STUDY_ID,
        "profiles_fetched": PROFILES,
        "matched_counts": fetched_counts,
        "highest_tert_expression_cluster": int(high_cluster),
        "highest_cluster_median_zscore": float(
            link.loc[link["cluster"].eq(high_cluster), "TERT_mrna_zscore_median"].iloc[0]
        ),
        "test_results": test_rows,
    }
    SUMMARY_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = f"""# LIHC TERT expression and copy-number update

## What was added

- TERT mRNA expression from cBioPortal TCGA-LIHC PanCancer Atlas RNA-seq.
- TERT mRNA z-scores, using diploid samples as the primary comparison scale.
- TERT GISTIC copy-number calls and log2 copy-number values.
- Cluster-level expression, copy-number, and survival-link summary tables.

## Key result

- Highest TERT mRNA cluster: cluster {int(high_cluster)}
- Median TERT mRNA z-score in highest cluster: {summary['highest_cluster_median_zscore']:.4f}

## Files

- `cluster_tert_expression_stats.csv`
- `cluster_tert_cna_stats.csv`
- `cluster_tert_expression_survival_link.csv`
- `tert_expression_cna_statistical_tests.csv`
- `cluster_tert_mrna_expression_boxplot.png`
- `tert_expression_cna_summary.json`

## Note

This complements, but does not replace, TERT promoter mutation analysis.
Patient-level TERT promoter mutation status remains unavailable in the current
cBioPortal default mutation/clinical export, so mRNA expression is used here as
a telomerase activity proxy.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")

    script_copy = STEP5_DIR / Path(__file__).name
    script_copy.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
