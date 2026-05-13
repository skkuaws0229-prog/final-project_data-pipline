#!/usr/bin/env python3
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "02_schema_mapping" / "selected_sources.json"
RAW_DIR = ROOT / "01_raw_selected"
OUT_DIR = ROOT / "03_normalized"


def first_value(row, candidates):
    for column in candidates:
        if column in row:
            value = row.get(column)
            if value is not None and str(value).strip() != "":
                return str(value).strip()
    return ""


def stable_id(prefix, *parts):
    material = "|".join(str(part or "").strip().lower() for part in parts)
    digest = hashlib.sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def to_int(value):
    if value == "":
        return ""
    try:
        return str(int(float(value)))
    except ValueError:
        return ""


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    config = json.loads(CONFIG_PATH.read_text())
    diseases = []
    drugs_by_id = {}
    candidates = []
    admet_rows = []
    source_rows = []

    for disease_id, disease_config in config["diseases"].items():
        source_file = disease_config["local_file"]
        source_path = RAW_DIR / source_file
        source_rows.append({
            "disease_id": disease_id,
            "display_name": disease_config["display_name"],
            "local_file": source_file,
            "s3_key": disease_config["s3_key"],
        })
        diseases.append({
            "disease_id": disease_id,
            "display_name": disease_config["display_name"],
            "source_file": source_file,
            "source_s3_key": disease_config["s3_key"],
        })
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        columns = disease_config["columns"]
        with source_path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row_index, row in enumerate(reader, start=1):
                drug_name = first_value(row, columns["drug_name"])
                explicit_drug_id = first_value(row, columns["drug_id"])
                smiles = first_value(row, columns["smiles"])
                drug_id = explicit_drug_id or stable_id("drug", drug_name, smiles)
                if not drug_name:
                    drug_name = drug_id

                drugs_by_id.setdefault(drug_id, {
                    "drug_id": drug_id,
                    "drug_name": drug_name,
                    "canonical_smiles": smiles,
                    "first_seen_disease_id": disease_id,
                })
                if smiles and not drugs_by_id[drug_id]["canonical_smiles"]:
                    drugs_by_id[drug_id]["canonical_smiles"] = smiles

                candidate_id = stable_id("cand", disease_id, drug_id, source_file, row_index)
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                candidates.append({
                    "candidate_id": candidate_id,
                    "disease_id": disease_id,
                    "drug_id": drug_id,
                    "rank": to_int(first_value(row, columns["rank"])),
                    "tier": first_value(row, columns["tier"]),
                    "score": first_value(row, columns["score"]),
                    "target": first_value(row, columns["target"]),
                    "target_pathway": first_value(row, columns["target_pathway"]),
                    "evidence_summary": first_value(row, ["tier_rationale", "definition_basis", "tier_note", "stad_4tier_rationale", "Clinical_Context", "IPF_Relevance"]),
                    "source_file": source_file,
                    "source_row_number": str(row_index),
                    "raw_json": raw_json,
                })
                admet_rows.append({
                    "admet_id": stable_id("admet", disease_id, drug_id, source_file, row_index),
                    "candidate_id": candidate_id,
                    "disease_id": disease_id,
                    "drug_id": drug_id,
                    "safety_score": first_value(row, columns["safety_score"]),
                    "verdict": first_value(row, columns["verdict"]),
                    "admet_status": first_value(row, columns["admet_status"]),
                    "hard_fail": first_value(row, columns["hard_fail"]),
                    "hard_fail_reasons": first_value(row, columns["hard_fail_reasons"]),
                    "soft_flags": first_value(row, columns["soft_flags"]),
                    "raw_json": raw_json,
                })

    write_csv(
        OUT_DIR / "diseases.csv",
        diseases,
        ["disease_id", "display_name", "source_file", "source_s3_key"],
    )
    write_csv(
        OUT_DIR / "drugs.csv",
        sorted(drugs_by_id.values(), key=lambda r: (r["drug_name"], r["drug_id"])),
        ["drug_id", "drug_name", "canonical_smiles", "first_seen_disease_id"],
    )
    write_csv(
        OUT_DIR / "drug_candidates.csv",
        candidates,
        ["candidate_id", "disease_id", "drug_id", "rank", "tier", "score", "target", "target_pathway", "evidence_summary", "source_file", "source_row_number", "raw_json"],
    )
    write_csv(
        OUT_DIR / "admet_results.csv",
        admet_rows,
        ["admet_id", "candidate_id", "disease_id", "drug_id", "safety_score", "verdict", "admet_status", "hard_fail", "hard_fail_reasons", "soft_flags", "raw_json"],
    )
    write_csv(
        OUT_DIR / "selected_sources.csv",
        source_rows,
        ["disease_id", "display_name", "local_file", "s3_key"],
    )
    print(f"normalized_diseases={len(diseases)}")
    print(f"normalized_drugs={len(drugs_by_id)}")
    print(f"normalized_candidates={len(candidates)}")
    print(f"normalized_admet_rows={len(admet_rows)}")


if __name__ == "__main__":
    main()
