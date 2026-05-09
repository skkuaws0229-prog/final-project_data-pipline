#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu


WORKSPACE = Path(__file__).resolve().parent.parent
LEGACY_DIR = WORKSPACE / "20260415_preproject_protocol_choi"
OUT_DIR = WORKSPACE / "20260428_new_BRCA_data" / "step6_metabric_validation"
TOP30_CSV = WORKSPACE / "20260428_new_BRCA_data" / "brca_directive_top30_unique_candidates.csv"
TIERED_CSV = WORKSPACE / "20260428_new_BRCA_data" / "brca_directive_top30_tiered_candidates.csv"
DRUG_ANN = LEGACY_DIR / "data" / "gdsc2_drug_annotation_master_20260406.parquet"


KNOWN_BRCA_DRUGS = {
    "Docetaxel", "Paclitaxel", "Vinorelbine", "Vinblastine",
    "Doxorubicin", "Epirubicin", "Cisplatin", "Carboplatin",
    "Tamoxifen", "Fulvestrant", "Letrozole", "Anastrozole",
    "Trastuzumab", "Lapatinib", "Pertuzumab", "Neratinib",
    "Palbociclib", "Ribociclib", "Abemaciclib",
    "Olaparib", "Talazoparib",
    "Everolimus", "Rapamycin",
    "Capecitabine", "Fluorouracil", "5-Fluorouracil", "Gemcitabine", "Eribulin",
    "Bortezomib", "Romidepsin",
    "Dinaciclib", "Staurosporine",
    "Camptothecin", "SN-38", "Irinotecan", "Topotecan",
    "Dactinomycin", "Actinomycin",
    "Luminespib", "Cyclophosphamide", "Oxaliplatin", "Fludarabine",
}

BRCA_PATHWAYS = {
    "ERK MAPK signaling", "PI3K/MTOR signaling", "Cell cycle",
    "Apoptosis regulation", "Chromatin histone acetylation",
    "DNA replication", "Mitosis", "Genome integrity",
    "Protein stability and degradation",
}

DEFAULT_EXPR_CANDIDATES = [
    WORKSPACE / "metabric_expression_basic_clean_20260406.parquet",
    LEGACY_DIR / "data" / "metabric" / "metabric_expression_basic_clean_20260406.parquet",
]

DEFAULT_CLIN_CANDIDATES = [
    WORKSPACE / "metabric_clinical_patient_basic_clean_20260406.parquet",
    LEGACY_DIR / "data" / "metabric" / "metabric_clinical_patient_basic_clean_20260406.parquet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BRCA Step6 METABRIC A/B/C validation on current directive ensemble Top30."
    )
    parser.add_argument("--top30-csv", type=Path, default=TOP30_CSV)
    parser.add_argument("--tiered-csv", type=Path, default=TIERED_CSV)
    parser.add_argument("--drug-ann", type=Path, default=DRUG_ANN)
    parser.add_argument("--expr-path", type=Path, default=None)
    parser.add_argument("--clin-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def resolve_existing_path(explicit: Path | None, candidates: list[Path], label: str) -> Path:
    if explicit is not None:
        if explicit.exists():
            return explicit
        raise FileNotFoundError(f"{label} file not found: {explicit}")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = "\n".join(f"  - {p}" for p in candidates)
    raise FileNotFoundError(
        f"{label} file not found. Searched:\n{searched}\n"
        "Provide --expr-path/--clin-path with a local parquet path."
    )


def load_top30(top30_csv: Path, tiered_csv: Path | None, drug_ann_path: Path) -> pd.DataFrame:
    top30 = pd.read_csv(top30_csv).copy()
    top30 = top30.rename(
        columns={
            "canonical_drug_id": "drug_id",
            "drug_level_score": "ensemble_score",
            "mean_prediction_score": "mean_pred_score",
        }
    )
    top30["drug_id"] = top30["drug_id"].astype(int)
    top30["rank"] = top30["rank"].astype(int)

    if tiered_csv is not None and tiered_csv.exists():
        tiered = pd.read_csv(tiered_csv)[["canonical_drug_id", "tier", "tier_name"]].copy()
        tiered = tiered.rename(columns={"canonical_drug_id": "drug_id"})
        tiered["drug_id"] = tiered["drug_id"].astype(int)
        top30 = top30.merge(tiered, on="drug_id", how="left")

    drug_ann = pd.read_parquet(drug_ann_path)[
        ["DRUG_ID", "DRUG_NAME", "PUTATIVE_TARGET_NORMALIZED", "PATHWAY_NAME_NORMALIZED"]
    ].copy()
    drug_ann = drug_ann.rename(
        columns={
            "DRUG_ID": "drug_id",
            "DRUG_NAME": "drug_name_ann",
            "PUTATIVE_TARGET_NORMALIZED": "target",
            "PATHWAY_NAME_NORMALIZED": "pathway",
        }
    )
    drug_ann["drug_id"] = drug_ann["drug_id"].astype(int)
    top30 = top30.merge(drug_ann, on="drug_id", how="left")
    top30["drug_name"] = top30["drug_name_ann"].fillna(top30["drug_name"])
    top30 = top30.drop(columns=["drug_name_ann"])
    return top30.sort_values("rank").reset_index(drop=True)


def method_a_target_expression(expr: pd.DataFrame, top30: pd.DataFrame) -> pd.DataFrame:
    patient_cols = [c for c in expr.columns if c.startswith("MB-")]
    gene_names = expr["Hugo_Symbol"].astype(str).values
    all_expr = expr[patient_cols].values.astype(float)
    global_median = np.nanmedian(all_expr)
    gene_means = np.nanmean(all_expr, axis=1)

    rows: list[dict] = []
    for _, row in top30.iterrows():
        target = str(row.get("target", ""))
        pathway = str(row.get("pathway", ""))
        target_genes = [g.strip() for g in target.split(",") if g.strip() and g.strip().lower() != "nan"]
        gene_mask = np.isin(gene_names, target_genes)
        matched_genes = gene_names[gene_mask]

        if len(matched_genes) > 0:
            target_expr = expr.loc[gene_mask, patient_cols].values.astype(float)
            mean_expr = float(np.nanmean(target_expr))
            pct_expressing = float(np.nanmean(target_expr > global_median))
            expr_rank_pct = float(np.mean(gene_means < np.nanmean(target_expr)) * 100)
            target_expressed = bool(pct_expressing > 0.3)
        else:
            mean_expr = 0.0
            pct_expressing = 0.0
            expr_rank_pct = 50.0
            target_expressed = False

        rows.append(
            {
                "drug_id": int(row["drug_id"]),
                "drug_name": row["drug_name"],
                "target": target or "N/A",
                "pathway": pathway or "N/A",
                "target_expressed": target_expressed,
                "mean_expr": mean_expr,
                "pct_patients_expressing": pct_expressing,
                "expr_rank_pct": expr_rank_pct,
                "brca_pathway_relevant": pathway in BRCA_PATHWAYS,
                "matched_genes": list(matched_genes),
            }
        )

    return pd.DataFrame(rows)


def method_b_survival(expr: pd.DataFrame, clin: pd.DataFrame, top30: pd.DataFrame) -> pd.DataFrame:
    clin = clin.copy()
    clin["os_months"] = pd.to_numeric(clin["OS_MONTHS"], errors="coerce")
    clin["os_event"] = clin["OS_STATUS"].apply(
        lambda x: 1 if "DECEASED" in str(x).upper() or "1:" in str(x) else 0
    )
    clin = clin.dropna(subset=["os_months"])

    patient_cols = [c for c in expr.columns if c.startswith("MB-")]
    gene_names = expr["Hugo_Symbol"].astype(str).values
    common_patients = sorted(set(patient_cols) & set(clin["PATIENT_ID"].astype(str).values))
    clin_sub = clin[clin["PATIENT_ID"].isin(common_patients)].set_index("PATIENT_ID")

    rows: list[dict] = []
    for _, row in top30.iterrows():
        target = str(row.get("target", ""))
        target_genes = [g.strip() for g in target.split(",") if g.strip() and g.strip().lower() != "nan"]
        gene_mask = np.isin(gene_names, target_genes)

        if gene_mask.sum() == 0:
            rows.append(
                {
                    "drug_id": int(row["drug_id"]),
                    "drug_name": row["drug_name"],
                    "survival_significant": False,
                    "log_rank_p": 1.0,
                    "median_os_high": 0.0,
                    "median_os_low": 0.0,
                    "hr_direction": "no_target_match",
                    "n_high": 0,
                    "n_low": 0,
                }
            )
            continue

        target_expr = expr.loc[gene_mask, common_patients].values.astype(float)
        mean_target_expr = np.nanmean(target_expr, axis=0)
        median_expr = np.nanmedian(mean_target_expr)
        high_mask = mean_target_expr >= median_expr
        low_mask = ~high_mask

        high_patients = [p for p, m in zip(common_patients, high_mask) if m]
        low_patients = [p for p, m in zip(common_patients, low_mask) if m]
        os_high = clin_sub.loc[clin_sub.index.isin(high_patients), "os_months"].values
        os_low = clin_sub.loc[clin_sub.index.isin(low_patients), "os_months"].values

        if len(os_high) > 10 and len(os_low) > 10:
            _, p_val = mannwhitneyu(os_high, os_low, alternative="two-sided")
            median_high = float(np.median(os_high))
            median_low = float(np.median(os_low))
            hr_dir = "protective" if median_high > median_low else "risk"
            significant = bool(p_val < 0.05)
        else:
            p_val = 1.0
            median_high = 0.0
            median_low = 0.0
            hr_dir = "insufficient"
            significant = False

        rows.append(
            {
                "drug_id": int(row["drug_id"]),
                "drug_name": row["drug_name"],
                "survival_significant": significant,
                "log_rank_p": float(p_val),
                "median_os_high": median_high,
                "median_os_low": median_low,
                "hr_direction": hr_dir,
                "n_high": int(len(os_high)),
                "n_low": int(len(os_low)),
            }
        )

    return pd.DataFrame(rows)


def method_c_precision(top30: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    top30_names = top30["drug_name"].astype(str).tolist()
    result: dict[str, dict[str, float | int]] = {}
    for k in [5, 10, 15, 20, 25, 30]:
        top_k = top30_names[: min(k, len(top30_names))]
        hits = sum(1 for name in top_k if name in KNOWN_BRCA_DRUGS)
        denom = len(top_k)
        result[f"P@{denom}"] = {
            "precision": float(hits / denom) if denom else 0.0,
            "hits": int(hits),
            "total": int(denom),
        }
    return result


def select_top15(top30: pd.DataFrame, df_a: pd.DataFrame, df_b: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = top30.copy()
    a_map = df_a.set_index("drug_id")
    b_map = df_b.set_index("drug_id")

    scores["target_expressed"] = scores["drug_id"].map(a_map["target_expressed"]).fillna(False).astype(int)
    scores["brca_pathway"] = scores["drug_id"].map(a_map["brca_pathway_relevant"]).fillna(False).astype(int)
    scores["survival_sig"] = scores["drug_id"].map(b_map["survival_significant"]).fillna(False).astype(int)
    scores["survival_p"] = scores["drug_id"].map(b_map["log_rank_p"]).fillna(1.0)
    scores["known_brca"] = scores["drug_name"].apply(lambda x: 1 if x in KNOWN_BRCA_DRUGS else 0)
    scores["confidence_points"] = scores["confidence_grade"].map({"A": 1.0, "B": 0.5, "C": 0.0}).fillna(0.0)

    rank_bonus = (31 - scores["rank"]) / 30.0
    score_min = float(scores["ensemble_score"].min())
    score_max = float(scores["ensemble_score"].max())
    if score_max > score_min:
        score_bonus = (scores["ensemble_score"] - score_min) / (score_max - score_min)
    else:
        score_bonus = pd.Series(0.0, index=scores.index)

    scores["validation_score"] = (
        scores["target_expressed"] * 2.0
        + scores["brca_pathway"] * 1.5
        + scores["survival_sig"] * 2.5
        + scores["known_brca"] * 2.0
        + scores["confidence_points"] * 1.0
        + rank_bonus * 1.0
        + score_bonus * 1.0
    )

    top15 = (
        scores.sort_values(["validation_score", "rank"], ascending=[False, True])
        .head(15)
        .sort_values(["validation_score", "rank"], ascending=[False, True])
        .reset_index(drop=True)
    )
    top15["final_rank"] = np.arange(1, len(top15) + 1)
    return top15, scores


def build_summary_markdown(
    top30: pd.DataFrame,
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    p_at_k: dict[str, dict[str, float | int]],
    top15: pd.DataFrame,
    expr_path: Path,
    clin_path: Path,
) -> str:
    known_hits = top30[top30["drug_name"].isin(KNOWN_BRCA_DRUGS)][["rank", "drug_name"]]
    lines = [
        "# BRCA Step6 METABRIC Validation",
        "",
        "- Date: 2026-04-28",
        "- Input Top30: `brca_directive_top30_unique_candidates.csv`",
        "- Validation scope: `METABRIC Method A/B/C`",
        f"- Expression input: `{expr_path}`",
        f"- Clinical input: `{clin_path}`",
        "",
        "## Summary",
        "",
        f"- Top30 drugs evaluated: **{len(top30)}**",
        f"- Method A target-expressed drugs: **{int(df_a['target_expressed'].sum())}/{len(df_a)}**",
        f"- Method A BRCA-pathway drugs: **{int(df_a['brca_pathway_relevant'].sum())}/{len(df_a)}**",
        f"- Method B survival-significant drugs: **{int(df_b['survival_significant'].sum())}/{len(df_b)}**",
        "",
        "## Method C",
        "",
        "| Metric | Precision | Hits | Total |",
        "| --- | ---: | ---: | ---: |",
    ]
    for key, value in p_at_k.items():
        lines.append(
            f"| {key} | {value['precision']:.3f} | {value['hits']} | {value['total']} |"
        )

    lines += [
        "",
        "## Known BRCA Matches In Top30",
        "",
        "| Rank | Drug |",
        "| --- | --- |",
    ]
    if known_hits.empty:
        lines.append("| - | none |")
    else:
        for _, row in known_hits.iterrows():
            lines.append(f"| {int(row['rank'])} | {row['drug_name']} |")

    lines += [
        "",
        "## Top15 After METABRIC A/B/C",
        "",
        "| Final Rank | Original Rank | Drug | Validation Score | Expr | Pathway | Survival | Known BRCA | Tier |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in top15.iterrows():
        tier_label = row["tier_name"] if "tier_name" in row and pd.notna(row["tier_name"]) else "-"
        lines.append(
            f"| {int(row['final_rank'])} | {int(row['rank'])} | {row['drug_name']} | "
            f"{row['validation_score']:.2f} | {int(row['target_expressed'])} | "
            f"{int(row['brca_pathway'])} | {int(row['survival_sig'])} | {int(row['known_brca'])} | {tier_label} |"
        )

    lines += [
        "",
        "## Next",
        "",
        "- Supplemental interpretation can be done with `ClinicalTrials.gov + manual review`.",
        "- Step7 ADMET remains a separate stage and is not included in this Step6 output.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    expr_path = resolve_existing_path(args.expr_path, DEFAULT_EXPR_CANDIDATES, "METABRIC expression")
    clin_path = resolve_existing_path(args.clin_path, DEFAULT_CLIN_CANDIDATES, "METABRIC clinical")

    expr = pd.read_parquet(expr_path)
    clin = pd.read_parquet(clin_path)
    top30 = load_top30(args.top30_csv, args.tiered_csv, args.drug_ann)

    df_a = method_a_target_expression(expr, top30)
    df_b = method_b_survival(expr, clin, top30)
    p_at_k = method_c_precision(top30)
    top15, all30 = select_top15(top30, df_a, df_b)

    top15_csv = args.output_dir / "brca_top15_metabric_validated.csv"
    all30_csv = args.output_dir / "brca_top30_metabric_scored.csv"
    method_a_csv = args.output_dir / "brca_metabric_method_a.csv"
    method_b_csv = args.output_dir / "brca_metabric_method_b.csv"
    summary_json = args.output_dir / "brca_metabric_validation_summary.json"
    summary_md = args.output_dir / "brca_metabric_validation_summary.md"

    top15.to_csv(top15_csv, index=False)
    all30.to_csv(all30_csv, index=False)
    df_a.to_csv(method_a_csv, index=False)
    df_b.to_csv(method_b_csv, index=False)

    summary = {
        "input_top30_csv": str(args.top30_csv),
        "input_expr_path": str(expr_path),
        "input_clin_path": str(clin_path),
        "top30_rows": int(len(top30)),
        "method_a": {
            "n_targets_expressed": int(df_a["target_expressed"].sum()),
            "n_brca_pathway": int(df_a["brca_pathway_relevant"].sum()),
            "n_total": int(len(df_a)),
        },
        "method_b": {
            "n_significant": int(df_b["survival_significant"].sum()),
            "n_total": int(len(df_b)),
        },
        "method_c": p_at_k,
        "top15_csv": str(top15_csv),
        "all30_csv": str(all30_csv),
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_md.write_text(
        build_summary_markdown(top30, df_a, df_b, p_at_k, top15, expr_path, clin_path),
        encoding="utf-8",
    )

    print(f"wrote: {top15_csv}")
    print(f"wrote: {all30_csv}")
    print(f"wrote: {method_a_csv}")
    print(f"wrote: {method_b_csv}")
    print(f"wrote: {summary_json}")
    print(f"wrote: {summary_md}")


if __name__ == "__main__":
    main()
