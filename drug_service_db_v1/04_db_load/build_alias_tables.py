#!/usr/bin/env python3
import csv
import hashlib
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = ROOT / "03_normalized"


MANUAL_DRUG_ALIASES = {
    "bleomycin (50 um)": "bleomycin",
    "bleomycin (50 μm)": "bleomycin",
    "tofacitinib citrate": "tofacitinib",
}


DISEASE_ALIASES = {
    "BRCA": ["BRCA", "breast cancer"],
    "Colon": ["Colon", "COAD", "CRC", "colorectal cancer", "colon cancer"],
    "HNSC": ["HNSC", "head and neck squamous cell carcinoma"],
    "IPF": ["IPF", "idiopathic pulmonary fibrosis"],
    "LUNG": ["LUNG", "LUAD", "lung cancer", "lung adenocarcinoma"],
    "Liver": ["Liver", "LIHC", "HCC", "liver cancer", "hepatocellular carcinoma"],
    "PAH": ["PAH", "pulmonary arterial hypertension"],
    "PDAC": ["PDAC", "PAAD", "pancreatic ductal adenocarcinoma"],
    "Psoriasis": ["Psoriasis"],
    "RA": ["RA", "rheumatoid arthritis"],
    "STAD": ["STAD", "gastric cancer", "stomach adenocarcinoma"],
}


def stable_id(prefix, *parts):
    material = "|".join(str(part or "").strip().lower() for part in parts)
    return f"{prefix}_{hashlib.sha1(material.encode('utf-8')).hexdigest()[:16]}"


def normalize_drug_name(name):
    value = str(name or "").strip().lower()
    value = value.replace("μ", "u")
    value = re.sub(r"\s+", " ", value)
    value = MANUAL_DRUG_ALIASES.get(value, value)
    return value


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def choose_primary(records):
    with_smiles = [r for r in records if r.get("canonical_smiles")]
    chembl = [r for r in records if str(r["drug_id"]).upper().startswith("CHEMBL")]
    pool = chembl or with_smiles or records
    return sorted(pool, key=lambda r: (len(r["drug_name"]), r["drug_name"], r["drug_id"]))[0]


class DisjointSet:
    def __init__(self):
        self.parent = {}

    def find(self, item):
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left, right):
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def main():
    drugs = read_csv(NORMALIZED_DIR / "drugs.csv")
    evidence = read_csv(NORMALIZED_DIR / "image_modal_drug_evidence.csv")
    disease_rows = read_csv(NORMALIZED_DIR / "diseases.csv")

    dsu = DisjointSet()
    for drug in drugs:
        dsu.find(drug["drug_id"])
        if drug.get("canonical_smiles"):
            dsu.union(drug["drug_id"], f"smiles:{drug['canonical_smiles']}")
        else:
            dsu.union(drug["drug_id"], f"name:{normalize_drug_name(drug['drug_name'])}")
        dsu.union(drug["drug_id"], f"name:{normalize_drug_name(drug['drug_name'])}")

    by_norm_name = defaultdict(list)
    for drug in drugs:
        by_norm_name[normalize_drug_name(drug["drug_name"])].append(drug)
    for norm_name, records in by_norm_name.items():
        if len(records) > 1:
            first = records[0]["drug_id"]
            for record in records[1:]:
                dsu.union(first, record["drug_id"])

    grouped = defaultdict(list)
    for drug in drugs:
        grouped[dsu.find(drug["drug_id"])].append(drug)

    canonical_rows = []
    alias_rows = []
    assigned_drug_ids = set()
    for group_key, records in sorted(grouped.items(), key=lambda item: item[0]):
        primary = choose_primary(records)
        group_smiles = sorted({r.get("canonical_smiles", "") for r in records if r.get("canonical_smiles")})
        group_names = sorted({normalize_drug_name(r["drug_name"]) for r in records})
        canonical_drug_id = stable_id("cdrug", "smiles", group_smiles[0]) if group_smiles else stable_id("cdrug", "name", group_names[0])
        canonical_rows.append({
            "canonical_drug_id": canonical_drug_id,
            "primary_drug_name": primary["drug_name"],
            "primary_smiles": primary.get("canonical_smiles", ""),
            "primary_source_drug_id": primary["drug_id"],
        })
        for record in records:
            assigned_drug_ids.add(record["drug_id"])
            alias_rows.append({
                "alias_id": stable_id("dalias", canonical_drug_id, record["drug_id"], record["drug_name"]),
                "canonical_drug_id": canonical_drug_id,
                "source_drug_id": record["drug_id"],
                "alias_name": record["drug_name"],
                "normalized_alias": normalize_drug_name(record["drug_name"]),
                "alias_type": "source_drug",
            })

    for drug in drugs:
        if drug["drug_id"] in assigned_drug_ids:
            continue
        canonical_drug_id = stable_id("cdrug", "solo", drug["drug_id"])
        canonical_rows.append({
            "canonical_drug_id": canonical_drug_id,
            "primary_drug_name": drug["drug_name"],
            "primary_smiles": drug.get("canonical_smiles", ""),
            "primary_source_drug_id": drug["drug_id"],
        })
        alias_rows.append({
            "alias_id": stable_id("dalias", canonical_drug_id, drug["drug_id"], drug["drug_name"]),
            "canonical_drug_id": canonical_drug_id,
            "source_drug_id": drug["drug_id"],
            "alias_name": drug["drug_name"],
            "normalized_alias": normalize_drug_name(drug["drug_name"]),
            "alias_type": "source_drug",
        })

    alias_by_norm = {}
    for row in alias_rows:
        alias_by_norm.setdefault(row["normalized_alias"], row["canonical_drug_id"])

    evidence_names = {}
    for row in evidence:
        normalized = normalize_drug_name(row["drug_name"])
        if normalized and normalized not in alias_by_norm:
            evidence_names.setdefault(normalized, row["drug_name"])
    for normalized, original_name in sorted(evidence_names.items()):
        canonical_drug_id = stable_id("cdrug", "evidence_only", normalized)
        canonical_rows.append({
            "canonical_drug_id": canonical_drug_id,
            "primary_drug_name": original_name,
            "primary_smiles": "",
            "primary_source_drug_id": "",
        })
        alias_rows.append({
            "alias_id": stable_id("dalias", canonical_drug_id, original_name),
            "canonical_drug_id": canonical_drug_id,
            "source_drug_id": "",
            "alias_name": original_name,
            "normalized_alias": normalized,
            "alias_type": "evidence_only",
        })
        alias_by_norm[normalized] = canonical_drug_id

    evidence_alias_rows = []
    for row in evidence:
        normalized = normalize_drug_name(row["drug_name"])
        canonical_drug_id = alias_by_norm.get(normalized, "")
        evidence_alias_rows.append({
            "evidence_id": row["evidence_id"],
            "disease_id": row["disease_id"],
            "drug_name": row["drug_name"],
            "normalized_drug_name": normalized,
            "canonical_drug_id": canonical_drug_id,
            "match_status": "matched" if canonical_drug_id and normalized not in evidence_names else "evidence_only",
        })

    disease_alias_rows = []
    valid_diseases = {r["disease_id"] for r in disease_rows}
    for disease_id, aliases in DISEASE_ALIASES.items():
        if disease_id not in valid_diseases:
            continue
        for alias in aliases:
            disease_alias_rows.append({
                "alias_id": stable_id("disalias", disease_id, alias),
                "disease_id": disease_id,
                "alias": alias,
                "normalized_alias": alias.lower(),
            })

    write_csv(
        NORMALIZED_DIR / "canonical_drugs.csv",
        sorted(canonical_rows, key=lambda r: r["primary_drug_name"].lower()),
        ["canonical_drug_id", "primary_drug_name", "primary_smiles", "primary_source_drug_id"],
    )
    write_csv(
        NORMALIZED_DIR / "drug_aliases.csv",
        sorted(alias_rows, key=lambda r: (r["canonical_drug_id"], r["alias_name"])),
        ["alias_id", "canonical_drug_id", "source_drug_id", "alias_name", "normalized_alias", "alias_type"],
    )
    write_csv(
        NORMALIZED_DIR / "image_modal_evidence_drug_matches.csv",
        evidence_alias_rows,
        ["evidence_id", "disease_id", "drug_name", "normalized_drug_name", "canonical_drug_id", "match_status"],
    )
    write_csv(
        NORMALIZED_DIR / "disease_aliases.csv",
        disease_alias_rows,
        ["alias_id", "disease_id", "alias", "normalized_alias"],
    )

    print(f"canonical_drugs={len(canonical_rows)}")
    print(f"drug_aliases={len(alias_rows)}")
    print(f"disease_aliases={len(disease_alias_rows)}")
    print(f"image_modal_evidence_matches={len(evidence_alias_rows)}")
    print(f"matched_evidence={sum(1 for r in evidence_alias_rows if r['match_status'] == 'matched')}")
    print(f"unmatched_evidence={sum(1 for r in evidence_alias_rows if r['match_status'] == 'unmatched')}")


if __name__ == "__main__":
    main()
