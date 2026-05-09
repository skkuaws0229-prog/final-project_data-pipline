from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "local_data" / "lihc_image_modal_20260501_v1"
OUT = BASE / "0.Image_modal_LIHC"
STEP4C = OUT / "step_im4c"
INPUT = BASE / "input"

CURRENT_HCC_THERAPIES = {
    "sorafenib",
    "lenvatinib",
    "regorafenib",
    "cabozantinib",
    "ramucirumab",
    "atezolizumab",
    "bevacizumab",
    "durvalumab",
    "tremelimumab",
    "nivolumab",
    "pembrolizumab",
    "ipilimumab",
}


def norm(value: object) -> str:
    if not isinstance(value, str):
        value = "" if pd.isna(value) else str(value)
    return value.strip().lower().replace("(50 um)", "").replace(" ", "")


def first_text(row: pd.Series, columns: list[str]) -> str:
    for col in columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            return str(row[col]).strip()
    return ""


def classify(row: pd.Series) -> tuple[str, str]:
    name = first_text(row, ["drug_name_display", "drug_name", "DRUG_NAME", "drug_name_admet"])
    name_key = norm(name)
    smiles = first_text(row, ["canonical_smiles", "drug__canonical_smiles", "smiles"])
    verdict = str(row.get("admet_verdict", "")).strip().upper()
    clinical_tier = str(row.get("clinical_tier", "")).strip()
    is_hcc_anchor = str(row.get("is_hcc_approved_anchor", "")).strip().lower() == "true"

    if not name or name.lower() == "nan" or not smiles or smiles.lower() == "nan":
        return "Tier4", "Excluded: missing drug identity or structure for actionable repurposing."
    if verdict == "FAIL":
        return "Tier4", "Excluded: ADMET gate marked this compound as FAIL."
    if is_hcc_anchor or clinical_tier == "1" or any(anchor in name_key for anchor in CURRENT_HCC_THERAPIES):
        return "Tier1", "Current/reference hepatocellular carcinoma therapy; validation control."
    if clinical_tier == "2":
        return "Tier2", "Liver cancer/HCC investigation or adjacent oncology repositioning evidence."
    if verdict in {"PASS", "WARNING", ""}:
        return "Tier3", "Repurposing candidate retained after ADMET screen, without current HCC treatment status."
    return "Tier3", "Repurposing candidate retained for hypothesis generation."


def admet_decision(row: pd.Series) -> tuple[str, str]:
    verdict = str(row.get("admet_verdict", "")).strip().upper()
    smiles = first_text(row, ["canonical_smiles", "drug__canonical_smiles", "smiles"])
    pains = str(row.get("pains_alert", "")).strip().lower() == "true"
    if not smiles or smiles.lower() == "nan":
        return "EXCLUDE", "Missing structure."
    if verdict == "FAIL":
        return "EXCLUDE", "ADMET FAIL."
    if verdict == "PASS" and not pains:
        return "KEEP", "ADMET PASS."
    if pains:
        return "CAUTION", "PAINS alert or assay-interference caution."
    return "CAUTION", "ADMET WARNING or limited assay support."


def build_mapping(tiered: pd.DataFrame) -> pd.DataFrame:
    profiles = pd.read_csv(OUT / "step_im4b" / "lihc_cluster_pathway_profiles.csv")
    rows = []
    for _, drug in tiered.iterrows():
        if drug["lihc_4tier"] == "Tier4":
            continue
        target_text = " ".join(
            str(drug.get(c, ""))
            for c in [
                "TARGET",
                "target",
                "target_pathway",
                "drug__target_list_x",
                "drug__target_list_y",
                "putative_target",
                "drug_name_display",
                "DRUG_NAME",
            ]
        ).upper()
        for _, profile in profiles.iterrows():
            keywords = [x.strip().upper() for x in str(profile["Candidate_Targets"]).split(";")]
            matches = [kw for kw in keywords if kw and kw in target_text]
            if not matches and "KINASE" in target_text and "KINASE" in keywords:
                matches = ["KINASE"]
            if not matches:
                continue
            rows.append(
                {
                    "cluster": int(profile["cluster"]),
                    "cluster_label": profile["Cluster_Label"],
                    "dominant_pathway": profile["Dominant_Pathway"],
                    "drug_name": first_text(drug, ["drug_name_display", "drug_name", "DRUG_NAME"]),
                    "canonical_drug_id": drug.get("canonical_drug_id"),
                    "target": first_text(drug, ["TARGET", "target", "putative_target"]),
                    "target_pathway": first_text(drug, ["target_pathway"]),
                    "lihc_4tier": drug["lihc_4tier"],
                    "admet_decision": drug["admet_decision"],
                    "admet_verdict": drug.get("admet_verdict", ""),
                    "safety_score": drug.get("safety_score", ""),
                    "match_keywords": "; ".join(matches),
                    "hypothesis": (
                        f"{first_text(drug, ['drug_name_display', 'drug_name', 'DRUG_NAME'])} "
                        f"({drug['lihc_4tier']}, ADMET {drug['admet_decision']}) may fit "
                        f"{profile['Cluster_Label']} through {profile['Dominant_Pathway']}."
                    ),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    STEP4C.mkdir(parents=True, exist_ok=True)
    top30 = pd.read_csv(STEP4C / "lihc_top30_4tier_classification.csv")
    admet = pd.read_csv(INPUT / "lihc_drugs_with_admet.csv").rename(
        columns={
            "drug_name": "drug_name_admet",
            "smiles": "admet_smiles",
            "verdict": "admet_verdict",
            "target": "admet_target",
            "target_pathway": "admet_target_pathway",
        }
    )
    top30["canonical_drug_id"] = top30["canonical_drug_id"].astype(str)
    admet["canonical_drug_id"] = admet["canonical_drug_id"].astype(str)
    merged = top30.merge(admet, on="canonical_drug_id", how="left", suffixes=("", "_admet"))
    if "admet_smiles" in merged.columns:
        merged["smiles"] = merged["admet_smiles"].combine_first(merged.get("canonical_smiles"))
    merged[["admet_decision", "admet_reason"]] = merged.apply(lambda r: pd.Series(admet_decision(r)), axis=1)
    merged[["lihc_4tier", "lihc_4tier_rationale"]] = merged.apply(lambda r: pd.Series(classify(r)), axis=1)

    admet_cols = [
        "rank",
        "canonical_drug_id",
        "drug_name_display",
        "drug_name_admet",
        "admet_decision",
        "admet_reason",
        "admet_verdict",
        "safety_score",
        "n_total_matches",
        "n_exact",
        "n_close_analog",
        "n_analog",
        "pains_alert",
        "mw",
        "logp",
        "hbd",
        "hba",
        "tpsa",
        "rotatable_bonds",
    ]
    available_admet_cols = [c for c in admet_cols if c in merged.columns]
    merged[available_admet_cols].to_csv(STEP4C / "lihc_top30_admet_filtering.csv", index=False)
    merged.to_csv(STEP4C / "lihc_top30_4tier_classification.csv", index=False)
    merged.to_csv(OUT / "lihc_top30_4tier_classification.csv", index=False)

    mapping = build_mapping(merged)
    mapping.to_csv(STEP4C / "lihc_top30_cluster_drug_hypotheses.csv", index=False)
    mapping.to_csv(OUT / "im4c_lihc_cluster_drug_mapping.csv", index=False)

    summary = {
        "top30_count": int(len(merged)),
        "admet_decision_counts": merged["admet_decision"].value_counts(dropna=False).to_dict(),
        "tier_counts": merged["lihc_4tier"].value_counts(dropna=False).to_dict(),
        "cluster_drug_links": int(len(mapping)),
        "outputs": {
            "admet": str(STEP4C / "lihc_top30_admet_filtering.csv"),
            "tier": str(STEP4C / "lihc_top30_4tier_classification.csv"),
            "mapping": str(STEP4C / "lihc_top30_cluster_drug_hypotheses.csv"),
        },
    }
    (STEP4C / "lihc_drug_recommendation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
