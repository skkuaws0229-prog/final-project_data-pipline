from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact


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
MUT_FREQ_OUT = STEP_DIR / "cluster_driver_mutation_frequency.csv"
MUT_FREQ_ALIAS_OUT = STEP_DIR / "cluster_mutation_frequency.csv"
TESTS_OUT = STEP_DIR / "cluster_statistical_tests.csv"
COOCCURRENCE_OUT = STEP_DIR / "tert_mutation_cooccurrence.csv"
AVAILABILITY_OUT = STEP_DIR / "tert_promoter_data_availability.json"
REPORT_OUT = STEP_DIR / "tert_promoter_status_report.md"

DRIVER_GENES = ["TERT", "TP53", "CTNNB1", "AXIN1", "ARID1A"]
NON_TERT_DRIVER_GENES = ["TP53", "CTNNB1", "AXIN1", "ARID1A"]


def _as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False})
        .fillna(False)
    )


def _driver_test(df: pd.DataFrame, col: str) -> dict[str, object]:
    table = pd.crosstab(df["cluster"], df[col])
    if table.shape[1] < 2:
        return {
            "variable": col,
            "chi2": np.nan,
            "p_value": np.nan,
            "dof": np.nan,
            "status": "not_tested",
            "note": "Only one mutation status observed.",
        }
    chi2, p_value, dof, _ = chi2_contingency(table)
    return {
        "variable": col,
        "chi2": chi2,
        "p_value": p_value,
        "dof": dof,
        "status": "tested",
        "note": "",
    }


def main() -> None:
    STEP5_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLINICAL_TABLE)

    if "TERT_mut" in df.columns and "TERT_coding_mut" not in df.columns:
        df["TERT_coding_mut"] = _as_bool_series(df["TERT_mut"])

    # TERT promoter mutation is noncoding and was not present in the local
    # cBioPortal-derived mutation table. Keep an explicit placeholder so
    # downstream tables do not mistake rare coding TERT calls for promoter calls.
    df["TERT_promoter_mut"] = pd.NA
    df["TERT_promoter_data_status"] = "not_available_in_cbioportal_pan_can_atlas_default_mutation_profile"

    for gene in NON_TERT_DRIVER_GENES:
        col = f"{gene}_mut"
        if col in df.columns:
            df[col] = _as_bool_series(df[col])
        else:
            df[col] = False

    df.to_csv(CLINICAL_TABLE, index=False)

    freq_rows: list[dict[str, object]] = []
    for cluster, grp in df.groupby("cluster", dropna=False):
        row: dict[str, object] = {
            "cluster": cluster,
            "n_patients": int(len(grp)),
            "TERT_promoter_mut_rate": np.nan,
            "TERT_promoter_mut_n": np.nan,
            "TERT_promoter_available_n": 0,
        }
        if "TERT_coding_mut" in grp.columns:
            coding = _as_bool_series(grp["TERT_coding_mut"])
            row["TERT_coding_mut_rate_not_promoter"] = float(coding.mean())
            row["TERT_coding_mut_n_not_promoter"] = int(coding.sum())
        for gene in NON_TERT_DRIVER_GENES:
            col = f"{gene}_mut"
            values = _as_bool_series(grp[col])
            row[f"{gene}_mut_rate"] = float(values.mean())
            row[f"{gene}_mut_n"] = int(values.sum())
            row[f"{gene}_available_n"] = int(values.notna().sum())
        freq_rows.append(row)

    freq = pd.DataFrame(freq_rows).sort_values("cluster")
    freq.to_csv(MUT_FREQ_OUT, index=False)
    freq.to_csv(MUT_FREQ_ALIAS_OUT, index=False)

    tests = pd.read_csv(TESTS_OUT)
    if "status" not in tests.columns:
        tests["status"] = "tested"
    if "note" not in tests.columns:
        tests["note"] = ""
    tests = tests[~tests["variable"].isin(["TERT_mut", "ALB_mut"])]
    tests = pd.concat(
        [
            tests,
            pd.DataFrame(
                [
                    {
                        "variable": "TERT_promoter_mut",
                        "chi2": np.nan,
                        "p_value": np.nan,
                        "dof": np.nan,
                        "status": "not_tested",
                        "note": (
                            "TERT promoter status is absent from the local "
                            "cBioPortal PanCancer Atlas default mutation/clinical data; "
                            "coding TERT mutations are not used as promoter calls."
                        ),
                    }
                ]
            ),
        ],
        ignore_index=True,
    )

    existing_vars = set(tests["variable"])
    add_rows = []
    for gene in NON_TERT_DRIVER_GENES:
        variable = f"{gene}_mut"
        if variable not in existing_vars:
            add_rows.append(_driver_test(df, variable))
    if add_rows:
        tests = pd.concat([tests, pd.DataFrame(add_rows)], ignore_index=True)
    tests.to_csv(TESTS_OUT, index=False)

    co_rows = []
    for partner in ["CTNNB1", "TP53"]:
        partner_col = f"{partner}_mut"
        if "TERT_coding_mut" in df.columns:
            table = pd.crosstab(_as_bool_series(df["TERT_coding_mut"]), _as_bool_series(df[partner_col]))
            odds_ratio = np.nan
            p_value = np.nan
            if table.shape == (2, 2):
                odds_ratio, p_value = fisher_exact(table)
            co_rows.append(
                {
                    "pair": f"TERT_coding_not_promoter__{partner}",
                    "status": "exploratory_not_promoter",
                    "n_tert_coding_mut": int(_as_bool_series(df["TERT_coding_mut"]).sum()),
                    "n_partner_mut": int(_as_bool_series(df[partner_col]).sum()),
                    "odds_ratio": odds_ratio,
                    "p_value": p_value,
                    "note": "Coding TERT only; not interpretable as TERT promoter co-occurrence.",
                }
            )
        co_rows.append(
            {
                "pair": f"TERT_promoter__{partner}",
                "status": "not_tested",
                "n_tert_promoter_available": 0,
                "n_partner_mut": int(_as_bool_series(df[partner_col]).sum()),
                "odds_ratio": np.nan,
                "p_value": np.nan,
                "note": "Patient-level TERT promoter mutation status is unavailable in the current local data.",
            }
        )
    pd.DataFrame(co_rows).to_csv(COOCCURRENCE_OUT, index=False)

    coding_tert_count = int(_as_bool_series(df.get("TERT_coding_mut", pd.Series(False, index=df.index))).sum())
    availability = {
        "cancer_type": "LIHC",
        "analysis_date": "2026-05-06",
        "driver_gene_list_requested": DRIVER_GENES,
        "tert_promoter_status": "not_available_in_current_local_cbioportal_pan_can_atlas_export",
        "cbioportal_study_id_checked": "lihc_tcga_pan_can_atlas_2018",
        "cbioportal_profiles_checked": [
            "lihc_tcga_pan_can_atlas_2018_mutations",
            "clinical_attributes",
            "generic_assay_profiles",
        ],
        "local_patient_count": int(df["patientId"].nunique()),
        "local_slide_count": int(len(df)),
        "coding_tert_mutation_count_not_promoter": coding_tert_count,
        "tcga_lihc_paper_context": {
            "reported_tert_promoter_frequency": "87/196 HCCs analyzed, 44%",
            "source": "Comprehensive and Integrative Genomic Characterization of Hepatocellular Carcinoma, Cell 2017",
        },
        "action_taken": [
            "Added explicit TERT_promoter_mut placeholder to clinical/mutation table.",
            "Removed coding-only TERT_mut from driver frequency/statistical interpretation.",
            "Updated driver frequency and statistical test files with requested driver list.",
            "Added co-occurrence status file documenting that promoter-level CTNNB1/TP53 tests were not possible.",
        ],
    }
    AVAILABILITY_OUT.write_text(json.dumps(availability, indent=2), encoding="utf-8")

    report = f"""# LIHC TERT promoter mutation status update

## Summary

TERT promoter mutation was reviewed for the LIHC image-modal cluster analysis.
The TCGA LIHC paper reports TERT promoter mutations as the most common somatic
event in the assayed subset: 87 of 196 HCCs analyzed in the promoter region
(44%). However, the current local cBioPortal PanCancer Atlas export used by
this pipeline does not contain patient-level TERT promoter mutation status.

## Current local data finding

- Local LIHC image-modal table patients: {df['patientId'].nunique()}
- Local LIHC image-modal rows/slides: {len(df)}
- cBioPortal default mutation profile TERT coding calls found locally: {coding_tert_count}
- Interpretation: these coding calls are not promoter mutations and should not
  be interpreted as the expected 40-60% LIHC TERT promoter signal.

## Pipeline update

- `TERT_promoter_mut` was added to `lihc_cluster_clinical_mutation_table.csv`
  as an explicit unavailable field.
- `cluster_driver_mutation_frequency.csv` and `cluster_mutation_frequency.csv`
  now use the requested driver set:
  TERT promoter, TP53, CTNNB1, AXIN1, ARID1A.
- `cluster_statistical_tests.csv` now includes `TERT_promoter_mut` as
  `not_tested` because patient-level promoter status is unavailable.
- `tert_mutation_cooccurrence.csv` documents that TERT promoter with CTNNB1
  and TP53 co-occurrence/mutual-exclusivity tests were not possible in the
  current data.

## Required future addition

TERT promoter mutation is biologically important in LIHC/HCC and should be
added once a patient-level supplement table can be mapped to the 223 local
TCGA-LIHC patients. Until then, cluster-level TERT promoter frequency,
chi-squared testing, and TERT+CTNNB1 / TERT+TP53 relationship tests are not
quantitatively reported.
"""
    REPORT_OUT.write_text(report, encoding="utf-8")

    script_copy = STEP5_DIR / Path(__file__).name
    script_copy.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    print(json.dumps(availability, indent=2))


if __name__ == "__main__":
    main()
