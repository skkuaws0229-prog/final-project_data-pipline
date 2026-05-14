#!/usr/bin/env python3
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "01_candidate_pool_selected"
OUT_DIR = ROOT / "03_normalized"


SOURCE_KEYS = {
    "BRCA": "20260408_new_pre_project_biso/202604_Final_data/BRCA/20260415_preproject_choi_protocol_v1_bisotest-1/20260415_preproject_choi_protocol_v1_bisotest/results/20260424_multicancer_stad_protocol_rerun/restored_protocol_top30_ev_top15_admet/step7_admet60_tiered_candidates.csv",
    "Colon": "20260408_new_pre_project_biso/202604_Final_data/Colon/20260428_colon_v2/20260428_colon_v2_step6_external_validation_existing_results/20260428_colon_v2_colon_top50_drugs_ensemble.csv",
    "HNSC": "20260408_new_pre_project_biso/202604_Final_data/HNSC/base_data/20260421_hnsc/outputs/final_selection/hnsc_selected_drugs_top50.csv",
    "IPF": "20260408_new_pre_project_biso/202604_Final_data/IPF/1.Drug_results/ipf_top30_clinical_reranked.csv",
    "LUNG": "20260408_new_pre_project_biso/202604_Final_data/LUNG/project_root/results/lung_top30_phase2b_catboost_with_names.csv",
    "Liver": "20260408_new_pre_project_biso/202604_Final_data/Liver/generated/results/20260428_liver_step4_v2/lihc_top30_directive_ensemble_with_names.csv",
    "PAH": "20260408_new_pre_project_biso/202604_Final_data/PAH/1.Drug_results/pah_top30_clinical_reranked.csv",
    "PDAC": "20260408_new_pre_project_biso/202604_Final_data/PDAC/base_data/20260421_paad/external_validation/paad/groupcv4_drug/top50_external_validation.csv",
    "Psoriasis": "20260408_new_pre_project_biso/202604_Final_data/Psoriasis/model_results/ml/toplists/phase2a_CatBoost_top30.csv",
    "RA": "20260408_new_pre_project_biso/202604_Final_data/RA/model_results/ml/toplists/phase2a_CatBoost_top30.csv",
    "STAD": "20260408_new_pre_project_biso/202604_Final_data/STAD/0.Image_modal_STAD/step_im4c/stad_top30_4tier_classification.csv",
}


def first_value(row: dict[str, str], candidates: list[str]) -> str:
    normalized = {key.lower(): key for key in row}
    for column in candidates:
        key = normalized.get(column.lower())
        if key is None:
            continue
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def stable_id(prefix: str, *parts: object) -> str:
    material = "|".join(str(part or "").strip().lower() for part in parts)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def to_int(value: str) -> str:
    if not value:
        return ""
    try:
        return str(int(float(value)))
    except ValueError:
        return ""


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows: list[dict[str, str]] = []
    source_rows: list[dict[str, str]] = []
    for disease_id in SOURCE_KEYS:
        local_file = f"{disease_id}_candidates_pool.csv"
        source_path = RAW_DIR / local_file
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        source_rows.append(
            {
                "disease_id": disease_id,
                "local_file": local_file,
                "s3_key": SOURCE_KEYS[disease_id],
            }
        )
        with source_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row_index, row in enumerate(reader, start=1):
                drug_name = first_value(row, ["drug_name", "DRUG_NAME", "Drug_Name", "drug_name_norm"])
                canonical_drug_id = first_value(row, ["canonical_drug_id", "ChEMBL_ID", "DRUG_ID"])
                drug_id = canonical_drug_id or stable_id("pooldrug", disease_id, drug_name)
                if not drug_name:
                    drug_name = drug_id
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                rows.append(
                    {
                        "candidate_id": stable_id("poolcand", disease_id, drug_id, local_file, row_index),
                        "disease_id": disease_id,
                        "drug_id": drug_id,
                        "canonical_drug_id": canonical_drug_id,
                        "drug_name": drug_name,
                        "rank": to_int(first_value(row, ["rank", "Rank", "final_rank", "pred_rank", "Model_Rank"])),
                        "tier": first_value(row, ["tier", "Tier", "admet_tier", "clinical_tier", "stad_4tier", "hnsc_relevance_class"]),
                        "score": first_value(row, ["score", "drug_level_score", "final_selection_score", "ensemble_score", "pred_ic50_mean", "pred_label_regression", "mean_pred_score", "ev_composite_0_10"]),
                        "target": first_value(row, ["target", "TARGET", "Primary_Target", "Primary_Gene", "target_genes", "target_list"]),
                        "target_pathway": first_value(row, ["target_pathway", "TARGET_PATHWAY", "Primary_Target_Name"]),
                        "evidence_summary": first_value(row, ["tier_rationale", "tier_rationale_ko", "stad_4tier_rationale", "anchor_note_ko", "Source", "match_source"]),
                        "canonical_smiles": first_value(row, ["canonical_smiles", "smiles"]),
                        "source_file": local_file,
                        "source_row_number": str(row_index),
                        "raw_json": raw_json,
                        "is_final_candidate": "false",
                    }
                )

    drugs = {row["drug_id"]: row for row in csv.DictReader((OUT_DIR / "drugs.csv").open(newline="", encoding="utf-8"))}
    aliases = {row["source_drug_id"]: row["canonical_drug_id"] for row in csv.DictReader((OUT_DIR / "drug_aliases.csv").open(newline="", encoding="utf-8"))}
    final_candidates = list(csv.DictReader((OUT_DIR / "drug_candidates.csv").open(newline="", encoding="utf-8")))
    pool_keys = {(row["disease_id"], row["canonical_drug_id"], row["drug_name"].strip().lower()) for row in rows}
    for final in final_candidates:
        drug = drugs.get(final["drug_id"], {})
        drug_name = drug.get("drug_name") or final["drug_id"]
        canonical_drug_id = aliases.get(final["drug_id"], final["drug_id"])
        matched = False
        for row in rows:
            if row["disease_id"] != final["disease_id"]:
                continue
            if row["canonical_drug_id"] == canonical_drug_id or row["drug_name"].strip().lower() == drug_name.strip().lower():
                row["is_final_candidate"] = "true"
                matched = True
        if matched:
            continue
        key = (final["disease_id"], canonical_drug_id, drug_name.strip().lower())
        if key in pool_keys:
            continue
        rows.append(
            {
                "candidate_id": f"poolfinal_{final['candidate_id']}",
                "disease_id": final["disease_id"],
                "drug_id": final["drug_id"],
                "canonical_drug_id": canonical_drug_id,
                "drug_name": drug_name,
                "rank": final["rank"],
                "tier": final["tier"],
                "score": final["score"],
                "target": final["target"],
                "target_pathway": final["target_pathway"],
                "evidence_summary": final["evidence_summary"],
                "canonical_smiles": drug.get("canonical_smiles", ""),
                "source_file": final["source_file"],
                "source_row_number": final["source_row_number"],
                "raw_json": final["raw_json"],
                "is_final_candidate": "true",
            }
        )
        pool_keys.add(key)

    write_csv(
        OUT_DIR / "candidate_pool.csv",
        rows,
        [
            "candidate_id",
            "disease_id",
            "drug_id",
            "canonical_drug_id",
            "drug_name",
            "rank",
            "tier",
            "score",
            "target",
            "target_pathway",
            "evidence_summary",
            "canonical_smiles",
            "source_file",
            "source_row_number",
            "raw_json",
            "is_final_candidate",
        ],
    )
    write_csv(
        OUT_DIR / "candidate_pool_sources.csv",
        source_rows,
        ["disease_id", "local_file", "s3_key"],
    )
    print(f"normalized_candidate_pool={len(rows)}")


if __name__ == "__main__":
    main()
