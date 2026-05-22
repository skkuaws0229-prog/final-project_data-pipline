#!/usr/bin/env python3
import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELECTED_SOURCES = ROOT / "02_schema_mapping" / "image_modal_selected_sources.csv"
RAW_DIR = ROOT / "01_image_modal_selected"
OUT_DIR = ROOT / "03_normalized"


def stable_id(prefix, *parts):
    material = "|".join(str(part or "").strip().lower() for part in parts)
    return f"{prefix}_{hashlib.sha1(material.encode('utf-8')).hexdigest()[:16]}"


def first_value(row, names):
    for name in names:
        if name in row and row[name] is not None and str(row[name]).strip() != "":
            return str(row[name]).strip()
    return ""


def read_sources():
    with SELECTED_SOURCES.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_cluster(cluster_rows_by_id, disease_id, cluster, cluster_label, pathway_summary, source_file, raw_json):
    if not cluster:
        return ""
    cluster_id = stable_id("imcluster", disease_id, cluster)
    existing = cluster_rows_by_id.get(cluster_id)
    if not existing:
        cluster_rows_by_id[cluster_id] = {
            "cluster_id": cluster_id,
            "disease_id": disease_id,
            "cluster_key": cluster,
            "cluster_label": cluster_label,
            "n_observations": "",
            "clinical_summary": "",
            "pathway_summary": pathway_summary,
            "source_file": source_file,
            "raw_json": raw_json,
        }
    else:
        if cluster_label and not existing["cluster_label"]:
            existing["cluster_label"] = cluster_label
        if pathway_summary and not existing["pathway_summary"]:
            existing["pathway_summary"] = pathway_summary
    return cluster_id


def parse_markdown_pipe_tables(text):
    tables = []
    current = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current.append(stripped)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)

    parsed = []
    for table in tables:
        if len(table) < 3:
            continue
        headers = [cell.strip() for cell in table[0].strip("|").split("|")]
        rows = []
        for line in table[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != len(headers):
                continue
            rows.append(dict(zip(headers, cells)))
        parsed.append(rows)
    return parsed


def split_drug_list(value):
    if not value:
        return []
    normalized = value.replace(" and ", ", ")
    parts = re.split(r";|,", normalized)
    return [part.strip() for part in parts if part.strip()]


def parse_markdown_drug_linkage(disease_id, source_id, local_file, text, cluster_rows_by_id):
    evidence_rows = []
    report_rows = []
    title = next((line.strip("# ").strip() for line in text.splitlines() if line.strip().startswith("#")), local_file)
    report_rows.append({
        "report_id": stable_id("imrep", disease_id, "drug_linkage", local_file),
        "disease_id": disease_id,
        "source_id": source_id,
        "report_kind": "drug_linkage",
        "title": title,
        "report_text": text,
        "source_file": local_file,
    })

    cleaned = text.replace("\r", "\n")
    if disease_id == "Colon" and "## Top Recommendations" in cleaned:
        section = cleaned.split("## Top Recommendations", 1)[1]
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        csv_lines = []
        for line in lines:
            if line.startswith("#"):
                break
            if "," in line:
                csv_lines.append(line)
        if csv_lines:
            for row_number, row in enumerate(csv.DictReader(csv_lines), start=1):
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                cluster = row.get("cluster", "").strip()
                cluster_id = add_cluster(
                    cluster_rows_by_id,
                    disease_id,
                    cluster,
                    row.get("cluster_label", "").strip(),
                    row.get("target_pathway", "").strip(),
                    local_file,
                    raw_json,
                )
                evidence_rows.append({
                    "evidence_id": stable_id("imev", disease_id, local_file, row_number),
                    "disease_id": disease_id,
                    "cluster_id": cluster_id,
                    "drug_id": row.get("canonical_drug_id", "").strip(),
                    "drug_name": row.get("drug_name", "").strip(),
                    "rank": row.get("rank", "").strip(),
                    "tier": row.get("crc_4tier", "").strip(),
                    "target": row.get("target", "").strip(),
                    "target_pathway": row.get("target_pathway", "").strip(),
                    "evidence_text": row.get("hypothesis", "").strip(),
                    "source_file": local_file,
                    "source_row_number": str(row_number),
                    "raw_json": raw_json,
                })
        return evidence_rows, report_rows

    for table in parse_markdown_pipe_tables(cleaned):
        if not table:
            continue
        headers = set(table[0].keys())
        if disease_id == "IPF" and "Tier1_2_Drug_Candidates" in headers:
            for row_number, row in enumerate(table, start=1):
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                cluster = row.get("Cluster", "").strip()
                cluster_id = add_cluster(
                    cluster_rows_by_id,
                    disease_id,
                    cluster,
                    row.get("Label", "").strip(),
                    row.get("Key_Pathway", "").strip(),
                    local_file,
                    raw_json,
                )
                for drug_index, drug_name in enumerate(split_drug_list(row.get("Tier1_2_Drug_Candidates", "")), start=1):
                    evidence_rows.append({
                        "evidence_id": stable_id("imev", disease_id, local_file, row_number, drug_index),
                        "disease_id": disease_id,
                        "cluster_id": cluster_id,
                        "drug_id": "",
                        "drug_name": drug_name,
                        "rank": str(drug_index),
                        "tier": "Tier1_2",
                        "target": "",
                        "target_pathway": row.get("Key_Pathway", "").strip(),
                        "evidence_text": row.get("Rationale", "").strip(),
                        "source_file": local_file,
                        "source_row_number": str(row_number),
                        "raw_json": raw_json,
                    })
        if disease_id == "PAH" and "Drug Candidates" in headers:
            for row_number, row in enumerate(table, start=1):
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                cluster = row.get("Cluster", "").strip()
                cluster_id = add_cluster(
                    cluster_rows_by_id,
                    disease_id,
                    cluster,
                    row.get("Label", "").strip(),
                    row.get("Key Pathway", "").strip(),
                    local_file,
                    raw_json,
                )
                for drug_index, drug_name in enumerate(split_drug_list(row.get("Drug Candidates", "")), start=1):
                    evidence_rows.append({
                        "evidence_id": stable_id("imev", disease_id, local_file, row_number, drug_index),
                        "disease_id": disease_id,
                        "cluster_id": cluster_id,
                        "drug_id": "",
                        "drug_name": drug_name,
                        "rank": str(drug_index),
                        "tier": "",
                        "target": "",
                        "target_pathway": row.get("Key Pathway", "").strip(),
                        "evidence_text": row.get("PAH Interpretation", "").strip(),
                        "source_file": local_file,
                        "source_row_number": str(row_number),
                        "raw_json": raw_json,
                    })
    return evidence_rows, report_rows


def main():
    sources = read_sources()
    source_rows = []
    cluster_rows_by_id = {}
    member_rows = []
    evidence_rows = []
    report_rows = []

    for src in sources:
        disease_id = src["disease"]
        kind = src["kind"]
        local_file = src["local_file"]
        source_path = RAW_DIR / local_file
        source_id = stable_id("imsrc", disease_id, kind, local_file)
        source_rows.append({
            "source_id": source_id,
            "disease_id": disease_id,
            "source_kind": kind,
            "local_file": local_file,
            "source_s3_key": src["s3_key"],
        })

        if not source_path.exists():
            continue

        if source_path.suffix.lower() == ".md":
            text = source_path.read_text(errors="replace")
            if kind == "drug_linkage":
                parsed_evidence, parsed_reports = parse_markdown_drug_linkage(
                    disease_id,
                    source_id,
                    local_file,
                    text,
                    cluster_rows_by_id,
                )
                evidence_rows.extend(parsed_evidence)
                report_rows.extend(parsed_reports)
                continue
            title = next((line.strip("# ").strip() for line in text.splitlines() if line.strip().startswith("#")), local_file)
            report_rows.append({
                "report_id": stable_id("imrep", disease_id, kind, local_file),
                "disease_id": disease_id,
                "source_id": source_id,
                "report_kind": kind,
                "title": title,
                "report_text": text,
                "source_file": local_file,
            })
            continue

        if source_path.suffix.lower() != ".csv":
            continue

        with source_path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=1):
                raw_json = json.dumps(row, ensure_ascii=False, sort_keys=True)
                cluster = first_value(row, ["cluster", "majority_cluster", "Cluster"])
                cluster_id = stable_id("imcluster", disease_id, cluster or "unclustered")
                cluster_label = first_value(row, ["cluster_label", "label", "severity_label", "hnsc_4tier", "pdac_4tier", "stad_4tier"])

                if cluster:
                    add_cluster(
                        cluster_rows_by_id,
                        disease_id,
                        cluster,
                        cluster_label,
                        first_value(row, ["dominant_pathway", "Key_Pathway", "pathway", "target_pathway"]),
                        local_file,
                        raw_json,
                    )

                if kind == "clinical_cluster":
                    member_id = stable_id("immem", disease_id, local_file, row_number)
                    member_rows.append({
                        "member_id": member_id,
                        "disease_id": disease_id,
                        "cluster_id": cluster_id if cluster else "",
                        "patient_id": first_value(row, ["patient_id", "patient_barcode", "patientId", "Patient", "PATIENT_ID"]),
                        "sample_id": first_value(row, ["sample_id", "sampleId", "SAMPLE_ID", "bcr_sample_barcode"]),
                        "slide_id": first_value(row, ["slide_id"]),
                        "image_id": first_value(row, ["image_id"]),
                        "source_file": local_file,
                        "source_row_number": str(row_number),
                        "raw_json": raw_json,
                    })
                    if cluster:
                        current = cluster_rows_by_id[cluster_id]
                        count = int(current["n_observations"] or "0") + 1
                        current["n_observations"] = str(count)

                if kind == "drug_linkage":
                    drug_name = first_value(row, ["drug_name", "Drug_Name"])
                    drug_id = first_value(row, ["canonical_drug_id", "ChEMBL_ID"])
                    if not drug_name and not drug_id:
                        continue
                    evidence_rows.append({
                        "evidence_id": stable_id("imev", disease_id, local_file, row_number),
                        "disease_id": disease_id,
                        "cluster_id": cluster_id if cluster else "",
                        "drug_id": drug_id,
                        "drug_name": drug_name,
                        "rank": first_value(row, ["drug_rank", "rank", "best_rank"]),
                        "tier": first_value(row, ["tier", "selection_tier", "luad_4tier", "lihc_4tier", "pdac_4tier", "psoriasis_4tier", "stad_4tier"]),
                        "target": first_value(row, ["target", "targets", "target_axis"]),
                        "target_pathway": first_value(row, ["target_pathway", "pathway", "dominant_pathway"]),
                        "evidence_text": first_value(row, ["hypothesis", "rationale", "linkage_hypothesis", "moa"]),
                        "source_file": local_file,
                        "source_row_number": str(row_number),
                        "raw_json": raw_json,
                    })

    write_csv(
        OUT_DIR / "image_modal_sources.csv",
        source_rows,
        ["source_id", "disease_id", "source_kind", "local_file", "source_s3_key"],
    )
    write_csv(
        OUT_DIR / "image_modal_clusters.csv",
        list(cluster_rows_by_id.values()),
        ["cluster_id", "disease_id", "cluster_key", "cluster_label", "n_observations", "clinical_summary", "pathway_summary", "source_file", "raw_json"],
    )
    write_csv(
        OUT_DIR / "image_modal_cluster_members.csv",
        member_rows,
        ["member_id", "disease_id", "cluster_id", "patient_id", "sample_id", "slide_id", "image_id", "source_file", "source_row_number", "raw_json"],
    )
    write_csv(
        OUT_DIR / "image_modal_drug_evidence.csv",
        evidence_rows,
        ["evidence_id", "disease_id", "cluster_id", "drug_id", "drug_name", "rank", "tier", "target", "target_pathway", "evidence_text", "source_file", "source_row_number", "raw_json"],
    )
    write_csv(
        OUT_DIR / "image_modal_reports.csv",
        report_rows,
        ["report_id", "disease_id", "source_id", "report_kind", "title", "report_text", "source_file"],
    )

    print(f"image_modal_sources={len(source_rows)}")
    print(f"image_modal_clusters={len(cluster_rows_by_id)}")
    print(f"image_modal_cluster_members={len(member_rows)}")
    print(f"image_modal_drug_evidence={len(evidence_rows)}")
    print(f"image_modal_reports={len(report_rows)}")


if __name__ == "__main__":
    main()
