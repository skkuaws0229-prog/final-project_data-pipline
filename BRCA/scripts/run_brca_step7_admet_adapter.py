#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs, Descriptors, FilterCatalog
from rdkit.Chem.FilterCatalog import FilterCatalogParams


WORKSPACE = Path(__file__).resolve().parent.parent
OUT_DIR = WORKSPACE / "20260428_new_BRCA_data" / "step7_admet_22assay"
TOP30_CSV = WORKSPACE / "20260428_new_BRCA_data" / "brca_directive_top30_unique_candidates.csv"
TIERED_CSV = WORKSPACE / "20260428_new_BRCA_data" / "brca_directive_top30_tiered_candidates.csv"
DRUG_CATALOG = WORKSPACE / "20260415_preproject_protocol_choi" / "data" / "drug_features_catalog.parquet"

ASSAY_DIR_CANDIDATES = [
    WORKSPACE
    / "20260415_preproject_choi_protocol_v1_bisotest-1"
    / "20260415_preproject_choi_protocol_v1_bisotest"
    / "curated_data"
    / "admet"
    / "tdc_admet_group"
    / "admet_group",
    WORKSPACE
    / "20260416_new_pre_project_biso_Lung"
    / "curated_data"
    / "admet"
    / "tdc_admet_group"
    / "admet_group",
]

ADMET_ASSAYS = {
    "ames": {"category": "Toxicity", "weight": -2.0},
    "dili": {"category": "Toxicity", "weight": -2.0},
    "herg": {"category": "Toxicity", "weight": -1.5},
    "ld50_zhu": {"category": "Toxicity", "weight": 1.0},
    "bioavailability_ma": {"category": "Absorption", "weight": 1.0},
    "bbb_martins": {"category": "Distribution", "weight": 0.5},
    "caco2_wang": {"category": "Absorption", "weight": 0.5},
    "hia_hou": {"category": "Absorption", "weight": 0.5},
    "pgp_broccatelli": {"category": "Absorption", "weight": -0.5},
    "ppbr_az": {"category": "Distribution", "weight": 0.3},
    "vdss_lombardo": {"category": "Distribution", "weight": 0.3},
    "cyp2c9_veith": {"category": "Metabolism", "weight": -0.5},
    "cyp2d6_veith": {"category": "Metabolism", "weight": -0.5},
    "cyp3a4_veith": {"category": "Metabolism", "weight": -0.5},
    "cyp2c9_substrate_carbonmangels": {"category": "Metabolism", "weight": 0.2},
    "cyp2d6_substrate_carbonmangels": {"category": "Metabolism", "weight": 0.2},
    "cyp3a4_substrate_carbonmangels": {"category": "Metabolism", "weight": 0.2},
    "clearance_hepatocyte_az": {"category": "Excretion", "weight": 0.5},
    "clearance_microsome_az": {"category": "Excretion", "weight": 0.5},
    "half_life_obach": {"category": "Excretion", "weight": 0.5},
    "lipophilicity_astrazeneca": {"category": "Properties", "weight": 0.3},
    "solubility_aqsoldb": {"category": "Properties", "weight": 0.5},
}

SIMILARITY_THRESHOLDS = {"exact": 1.0, "close_analog": 0.85, "analog": 0.70}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BRCA Step7 ADMET 22-assay evaluation on current Top30.")
    parser.add_argument("--top30-csv", type=Path, default=TOP30_CSV)
    parser.add_argument("--tiered-csv", type=Path, default=TIERED_CSV)
    parser.add_argument("--drug-catalog", type=Path, default=DRUG_CATALOG)
    parser.add_argument("--assay-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def resolve_assay_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        if explicit.exists():
            return explicit
        raise FileNotFoundError(f"ADMET assay dir not found: {explicit}")
    for candidate in ASSAY_DIR_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = "\n".join(f"  - {p}" for p in ASSAY_DIR_CANDIDATES)
    raise FileNotFoundError(f"ADMET assay dir not found. Searched:\n{searched}")


def build_pains_catalog() -> FilterCatalog.FilterCatalog:
    params = FilterCatalogParams()
    params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
    return FilterCatalog.FilterCatalog(params)


def get_fingerprint(smiles: str):
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    except Exception:
        return None
    return None


def load_top30(top30_csv: Path, tiered_csv: Path, drug_catalog_path: Path) -> pd.DataFrame:
    top30 = pd.read_csv(top30_csv).rename(columns={"canonical_drug_id": "drug_id"}).copy()
    top30["drug_id"] = top30["drug_id"].astype(int)
    tiered = pd.read_csv(tiered_csv)[["canonical_drug_id", "tier", "tier_name", "tier_validation_goal"]].copy()
    tiered = tiered.rename(columns={"canonical_drug_id": "drug_id"})
    tiered["drug_id"] = tiered["drug_id"].astype(int)
    top30 = top30.merge(tiered, on="drug_id", how="left")

    catalog = pd.read_parquet(drug_catalog_path)[["DRUG_ID", "canonical_smiles"]].copy()
    catalog = catalog.rename(columns={"DRUG_ID": "drug_id", "canonical_smiles": "catalog_smiles"})
    catalog["drug_id"] = catalog["drug_id"].astype(int)
    top30 = top30.merge(catalog, on="drug_id", how="left")
    top30["canonical_smiles"] = top30["canonical_smiles"].fillna(top30["catalog_smiles"])
    top30 = top30.drop(columns=["catalog_smiles"])
    return top30.sort_values("rank").reset_index(drop=True)


def load_assay_libraries(assay_dir: Path) -> dict[str, dict]:
    libraries: dict[str, dict] = {}
    for assay_name in ADMET_ASSAYS:
        train_path = assay_dir / assay_name / "train_val.csv"
        df = pd.read_csv(train_path)
        fps = []
        y_values = []
        for _, row in df.iterrows():
            smiles = row.get("Drug")
            y_val = row.get("Y")
            if not isinstance(smiles, str):
                continue
            fp = get_fingerprint(smiles)
            if fp is None or pd.isna(y_val):
                continue
            fps.append(fp)
            y_values.append(float(y_val))
        libraries[assay_name] = {
            "fps": fps,
            "y_values": y_values,
            "n_compounds": len(fps),
        }
    return libraries


def match_assays(df: pd.DataFrame, libraries: dict[str, dict]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for _, row in df.iterrows():
        drug_name = row["drug_name"]
        smiles = row["canonical_smiles"]
        if pd.isna(smiles):
            continue
        drug_fp = get_fingerprint(smiles)
        if drug_fp is None:
            continue

        result = {
            "drug_id": int(row["drug_id"]),
            "drug_name": drug_name,
            "smiles": smiles,
            "assays": {},
            "n_exact": 0,
            "n_close_analog": 0,
            "n_analog": 0,
            "n_total_matches": 0,
        }
        for assay_name, lib in libraries.items():
            best_similarity = 0.0
            best_value = None
            for fp, y_val in zip(lib["fps"], lib["y_values"]):
                similarity = DataStructs.TanimotoSimilarity(drug_fp, fp)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_value = y_val
            if best_similarity >= SIMILARITY_THRESHOLDS["analog"]:
                match_type = "analog"
                if best_similarity >= SIMILARITY_THRESHOLDS["close_analog"]:
                    match_type = "close_analog"
                if best_similarity >= SIMILARITY_THRESHOLDS["exact"]:
                    match_type = "exact"
                result["assays"][assay_name] = {
                    "similarity": float(best_similarity),
                    "value": float(best_value) if best_value is not None else None,
                    "match_type": match_type,
                }
                result[f"n_{match_type}"] += 1
                result["n_total_matches"] += 1
        results[drug_name] = result
    return results


def calc_lipinski_violations(props: dict[str, float | int | None]) -> int:
    violations = 0
    if props["mw"] is not None and props["mw"] > 500:
        violations += 1
    if props["logp"] is not None and props["logp"] > 5:
        violations += 1
    if props["hbd"] is not None and props["hbd"] > 5:
        violations += 1
    if props["hba"] is not None and props["hba"] > 10:
        violations += 1
    return violations


def rdkit_properties(smiles: str) -> dict[str, float | int | None]:
    mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
    if mol is None:
        return {
            "mw": None,
            "logp": None,
            "hbd": None,
            "hba": None,
            "tpsa": None,
            "rotatable_bonds": None,
        }
    return {
        "mw": float(Descriptors.MolWt(mol)),
        "logp": float(Descriptors.MolLogP(mol)),
        "hbd": int(Descriptors.NumHDonors(mol)),
        "hba": int(Descriptors.NumHAcceptors(mol)),
        "tpsa": float(Descriptors.TPSA(mol)),
        "rotatable_bonds": int(Descriptors.NumRotatableBonds(mol)),
    }


def score_and_filter(df: pd.DataFrame, results: dict[str, dict]) -> pd.DataFrame:
    pains_catalog = build_pains_catalog()
    rows: list[dict] = []
    for _, row in df.iterrows():
        drug_name = row["drug_name"]
        smiles = row["canonical_smiles"]
        props = rdkit_properties(smiles) if isinstance(smiles, str) else {
            "mw": None, "logp": None, "hbd": None, "hba": None, "tpsa": None, "rotatable_bonds": None
        }
        lipinski_violations = calc_lipinski_violations(props)
        mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) else None
        pains_alerts = int(bool(mol and pains_catalog.HasMatch(mol)))

        result = results.get(
            drug_name,
            {
                "assays": {},
                "n_exact": 0,
                "n_close_analog": 0,
                "n_analog": 0,
                "n_total_matches": 0,
            },
        )

        safety_score = 5.0
        for assay_name, assay_meta in ADMET_ASSAYS.items():
            match = result["assays"].get(assay_name)
            if match and match["value"] is not None:
                safety_score += match["value"] * assay_meta["weight"]

        herg_value = result["assays"].get("herg", {}).get("value")
        ames_value = result["assays"].get("ames", {}).get("value")
        dili_value = result["assays"].get("dili", {}).get("value")
        cyp3a4_value = result["assays"].get("cyp3a4_veith", {}).get("value")
        ppbr_value = result["assays"].get("ppbr_az", {}).get("value")
        caco2_value = result["assays"].get("caco2_wang", {}).get("value")
        bioavailability_value = result["assays"].get("bioavailability_ma", {}).get("value")
        half_life_value = result["assays"].get("half_life_obach", {}).get("value")

        hard_fail_reasons = []
        if herg_value is not None and herg_value > 0.7:
            hard_fail_reasons.append("hERG>0.7")
        if pains_alerts > 0:
            hard_fail_reasons.append("PAINS>0")
        if lipinski_violations > 2:
            hard_fail_reasons.append("Lipinski>2")

        soft_flags = []
        if herg_value is not None and 0.5 <= herg_value <= 0.7:
            soft_flags.append("hERG_0.5_0.7")
        if dili_value is not None and dili_value > 0.5:
            soft_flags.append("DILI")
        if ames_value is not None and ames_value > 0.5:
            soft_flags.append("Ames")
        if cyp3a4_value is not None and cyp3a4_value > 0.5:
            soft_flags.append("CYP3A4")
        if ppbr_value is not None and ppbr_value > 95:
            soft_flags.append("PPBR_high")
        if caco2_value is not None and caco2_value < -5:
            soft_flags.append("Caco2_low")

        context_flags = []
        if bioavailability_value is not None and bioavailability_value < 0.5:
            context_flags.append("Oral_bio_low")
        if half_life_value is not None and half_life_value < 1.0:
            context_flags.append("Half_life_low")

        if hard_fail_reasons or safety_score < 4.0:
            verdict = "FAIL"
        elif safety_score >= 6.0 and len(soft_flags) == 0:
            verdict = "PASS"
        else:
            verdict = "WARNING"

        rows.append(
            {
                "drug_id": int(row["drug_id"]),
                "rank": int(row["rank"]),
                "drug_name": drug_name,
                "tier": row.get("tier"),
                "tier_name": row.get("tier_name"),
                "tier_validation_goal": row.get("tier_validation_goal"),
                "selected_config": row.get("selected_config"),
                "ensemble_method": row.get("ensemble_method"),
                "drug_level_score": row.get("drug_level_score"),
                "confidence_grade": row.get("confidence_grade"),
                "canonical_smiles": smiles,
                "safety_score": float(safety_score),
                "verdict": verdict,
                "n_total_matches": int(result["n_total_matches"]),
                "n_exact": int(result["n_exact"]),
                "n_close_analog": int(result["n_close_analog"]),
                "n_analog": int(result["n_analog"]),
                "hard_fail": int(len(hard_fail_reasons) > 0),
                "hard_fail_reasons": ";".join(hard_fail_reasons),
                "soft_flag_count": int(len(soft_flags)),
                "soft_flags": ";".join(soft_flags),
                "context_flag_count": int(len(context_flags)),
                "context_flags": ";".join(context_flags),
                "herg_value": herg_value,
                "ames_value": ames_value,
                "dili_value": dili_value,
                "cyp3a4_value": cyp3a4_value,
                "ppbr_value": ppbr_value,
                "caco2_value": caco2_value,
                "bioavailability_value": bioavailability_value,
                "half_life_value": half_life_value,
                "pains_alerts": pains_alerts,
                "lipinski_violations": lipinski_violations,
                **props,
            }
        )
    return pd.DataFrame(rows)


def select_final15(df_scored: pd.DataFrame) -> pd.DataFrame:
    verdict_priority = {"PASS": 0, "WARNING": 1, "FAIL": 2}
    confidence_priority = {"A": 0, "B": 1, "C": 2}
    ranked = df_scored.copy()
    ranked["verdict_priority"] = ranked["verdict"].map(verdict_priority).fillna(9)
    ranked["confidence_priority"] = ranked["confidence_grade"].map(confidence_priority).fillna(9)
    ranked = ranked.sort_values(
        [
            "hard_fail",
            "verdict_priority",
            "safety_score",
            "n_total_matches",
            "soft_flag_count",
            "confidence_priority",
            "rank",
        ],
        ascending=[True, True, False, False, True, True, True],
    ).reset_index(drop=True)
    final15 = ranked.head(15).copy()
    final15["final_admet_rank"] = np.arange(1, len(final15) + 1)
    return final15


def build_summary_markdown(df_scored: pd.DataFrame, final15: pd.DataFrame, assay_dir: Path) -> str:
    verdict_counts = df_scored["verdict"].value_counts().to_dict()
    lines = [
        "# BRCA Step7 ADMET 22-Assay",
        "",
        "- Date: 2026-04-28",
        "- Input: current BRCA Top30 (all drugs entered Step7)",
        "- Method: TDC ADMET 22 assays + Tanimoto similarity v1",
        f"- Assay source: `{assay_dir}`",
        "",
        "## Summary",
        "",
        f"- Total evaluated: **{len(df_scored)}**",
        f"- PASS: **{verdict_counts.get('PASS', 0)}**",
        f"- WARNING: **{verdict_counts.get('WARNING', 0)}**",
        f"- FAIL: **{verdict_counts.get('FAIL', 0)}**",
        f"- Hard fail: **{int(df_scored['hard_fail'].sum())}**",
        "",
        "## Final 15",
        "",
        "| Final Rank | Orig Rank | Drug | Tier | Verdict | Safety Score | Hard Fail | Soft Flags |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for _, row in final15.iterrows():
        lines.append(
            f"| {int(row['final_admet_rank'])} | {int(row['rank'])} | {row['drug_name']} | "
            f"{row['tier_name']} | {row['verdict']} | {row['safety_score']:.3f} | "
            f"{int(row['hard_fail'])} | {row['soft_flags'] or '-'} |"
        )
    lines += [
        "",
        "## Note",
        "",
        "- This Step7 selection keeps all 30 drugs as input and selects the final 15 after ADMET filtering.",
        "- Tier 1/2/3/4 labels are preserved from the existing BRCA classification table.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    assay_dir = resolve_assay_dir(args.assay_dir)

    top30 = load_top30(args.top30_csv, args.tiered_csv, args.drug_catalog)
    libraries = load_assay_libraries(assay_dir)
    results = match_assays(top30, libraries)
    df_scored = score_and_filter(top30, results)
    final15 = select_final15(df_scored)

    detailed_csv = args.output_dir / "brca_admet_22assay_top30_detailed.csv"
    final15_csv = args.output_dir / "brca_final15_after_admet.csv"
    results_json = args.output_dir / "brca_admet_22assay_matches.json"
    summary_json = args.output_dir / "brca_admet_22assay_summary.json"
    summary_md = args.output_dir / "brca_admet_22assay_summary.md"

    df_scored.to_csv(detailed_csv, index=False)
    final15.to_csv(final15_csv, index=False)
    results_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {
        "input_top30_rows": int(len(top30)),
        "assay_dir": str(assay_dir),
        "verdict_counts": df_scored["verdict"].value_counts().to_dict(),
        "hard_fail_count": int(df_scored["hard_fail"].sum()),
        "final15_csv": str(final15_csv),
        "detailed_csv": str(detailed_csv),
    }
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary_md.write_text(build_summary_markdown(df_scored, final15, assay_dir), encoding="utf-8")

    print(f"wrote: {detailed_csv}")
    print(f"wrote: {final15_csv}")
    print(f"wrote: {results_json}")
    print(f"wrote: {summary_json}")
    print(f"wrote: {summary_md}")


if __name__ == "__main__":
    main()
