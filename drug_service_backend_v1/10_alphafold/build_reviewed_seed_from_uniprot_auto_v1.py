from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
DOCS = ROOT / "docs"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stable_id(prefix: str, *parts: str, length: int = 16) -> str:
    raw = "||".join(part.strip().lower() for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def split_pipe(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def build_seed_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    rows = read_csv(ALPHAFOLD / "uniprot_auto_mapping_candidates_v1.csv")

    protein_rows: dict[str, dict[str, str]] = {}
    link_rows: dict[tuple[str, str], dict[str, str]] = {}
    hold_rows: list[dict[str, str]] = []

    for row in rows:
        status = row["auto_mapping_status"]
        if status != "auto_suggested":
            hold_rows.append(
                {
                    "suggested_gene_symbol": row["suggested_gene_symbol"],
                    "raw_text": row["raw_text"],
                    "auto_uniprot_id": row["auto_uniprot_id"],
                    "hit_count": row["hit_count"],
                    "auto_mapping_status": status,
                    "reason": "auto_suggested가 아니므로 reviewed seed v1에서 보류",
                    "mapping_notes": row["mapping_notes"],
                }
            )
            continue

        uniprot_id = row["auto_uniprot_id"].strip()
        protein_id = f"protein_{uniprot_id.lower()}"
        source_raw_texts = split_pipe(row["raw_text"])
        diseases = split_pipe(row["diseases"])
        gene_symbol = row["uniprot_primary_gene"].strip() or row["suggested_gene_symbol"].strip()

        if protein_id not in protein_rows:
            protein_rows[protein_id] = {
                "protein_id": protein_id,
                "gene_symbol": gene_symbol,
                "uniprot_id": uniprot_id,
                "uniprot_entry_name": row["uniprot_entry_name"],
                "protein_name": row["protein_name"],
                "organism": "Homo sapiens",
                "source": "uniprot_auto_mapping_v1",
                "review_status": "auto_suggested_pending_final_review",
                "source_raw_texts": "|".join(source_raw_texts),
                "diseases": "|".join(diseases),
                "notes": "AlphaFold DB 구조 다운로드 전 seed 후보",
            }
        else:
            existing = protein_rows[protein_id]
            existing["source_raw_texts"] = "|".join(
                dict.fromkeys(split_pipe(existing["source_raw_texts"]) + source_raw_texts)
            )
            existing["diseases"] = "|".join(dict.fromkeys(split_pipe(existing["diseases"]) + diseases))

        for raw_text in source_raw_texts:
            key = (raw_text.lower(), protein_id)
            if key in link_rows:
                continue
            mapping_status = "exact" if raw_text.upper() == gene_symbol.upper() else "alias"
            confidence = "0.95" if mapping_status == "exact" else "0.80"
            payload = {
                "source": row["source"],
                "priority": row["priority"],
                "suggested_gene_symbol": row["suggested_gene_symbol"],
                "uniprot_primary_gene": row["uniprot_primary_gene"],
                "uniprot_gene_names": row["uniprot_gene_names"],
                "candidate_class": row["candidate_class"],
                "mentions": row["mentions"],
                "diseases": row["diseases"],
                "mapping_notes": row["mapping_notes"],
            }
            link_rows[key] = {
                "link_id": stable_id("tplink", raw_text, protein_id),
                "target_text": raw_text,
                "normalized_target_text": raw_text.lower(),
                "protein_id": protein_id,
                "gene_symbol": gene_symbol,
                "uniprot_id": uniprot_id,
                "mapping_status": mapping_status,
                "confidence": confidence,
                "source": "uniprot_auto_mapping_v1",
                "raw_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            }

    return (
        sorted(protein_rows.values(), key=lambda item: item["gene_symbol"]),
        sorted(link_rows.values(), key=lambda item: (item["gene_symbol"], item["target_text"])),
        sorted(hold_rows, key=lambda item: item["suggested_gene_symbol"]),
    )


def validate_seed(
    proteins: list[dict[str, str]],
    links: list[dict[str, str]],
    holds: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    protein_ids = Counter(row["protein_id"] for row in proteins)
    uniprot_ids = Counter(row["uniprot_id"] for row in proteins)
    gene_symbols = Counter(row["gene_symbol"].upper() for row in proteins)
    link_keys = Counter((row["target_text"].lower(), row["protein_id"]) for row in links)
    protein_id_set = set(protein_ids)

    for label, counter in {
        "protein_id": protein_ids,
        "uniprot_id": uniprot_ids,
        "gene_symbol": gene_symbols,
    }.items():
        dupes = [key for key, count in counter.items() if count > 1]
        if dupes:
            errors.append(f"{label} duplicate: {dupes}")

    link_dupes = [key for key, count in link_keys.items() if count > 1]
    if link_dupes:
        errors.append(f"target_text+protein_id duplicate: {link_dupes}")

    missing_fk = [row["protein_id"] for row in links if row["protein_id"] not in protein_id_set]
    if missing_fk:
        errors.append(f"link protein_id missing from protein seed: {missing_fk}")

    if len(holds) != 1 or holds[0]["suggested_gene_symbol"].upper() != "MET":
        errors.append("hold list expected to contain only MET for v1")

    return errors


def write_summary(
    proteins: list[dict[str, str]],
    links: list[dict[str, str]],
    holds: list[dict[str, str]],
    errors: list[str],
) -> None:
    mapping_status_counts = Counter(row["mapping_status"] for row in links)
    disease_counts = Counter()
    for row in proteins:
        disease_counts.update(split_pipe(row["diseases"]))

    lines = [
        "# Reviewed UniProt Seed 생성 결과 v1",
        "",
        "## 목적",
        "",
        "UniProt 자동 매핑 후보 중 `auto_suggested`만 DB seed 후보로 분리했다.",
        "이 단계에서는 AlphaFold DB 구조 조회, 구조 다운로드, DB 적재를 실행하지 않았다.",
        "",
        "## 생성 파일",
        "",
        "```text",
        "10_alphafold/protein_targets_seed_reviewed_v1.csv",
        "10_alphafold/target_protein_links_seed_reviewed_v1.csv",
        "10_alphafold/uniprot_mapping_hold_v1.csv",
        "```",
        "",
        "## Row Count",
        "",
        "| file | rows |",
        "| --- | ---: |",
        f"| protein_targets_seed_reviewed_v1.csv | {len(proteins)} |",
        f"| target_protein_links_seed_reviewed_v1.csv | {len(links)} |",
        f"| uniprot_mapping_hold_v1.csv | {len(holds)} |",
        "",
        "## Link Mapping Status",
        "",
        "| mapping_status | rows |",
        "| --- | ---: |",
        *[f"| {key} | {mapping_status_counts[key]} |" for key in sorted(mapping_status_counts)],
        "",
        "## Disease Coverage",
        "",
        "| disease | proteins |",
        "| --- | ---: |",
        *[f"| {key} | {disease_counts[key]} |" for key in sorted(disease_counts)],
        "",
        "## 보류 항목",
        "",
        "| gene | uniprot_id | status | reason |",
        "| --- | --- | --- | --- |",
        *[
            f"| {row['suggested_gene_symbol']} | {row['auto_uniprot_id']} | {row['auto_mapping_status']} | {row['reason']} |"
            for row in holds
        ],
        "",
        "## 무결성 결과",
        "",
    ]

    if errors:
        lines.extend(["```text", *errors, "```", "", "판정: 실패"])
    else:
        lines.extend(
            [
                "```text",
                "protein_id duplicate: 0",
                "uniprot_id duplicate: 0",
                "gene_symbol duplicate: 0",
                "target_text + protein_id duplicate: 0",
                "target_protein_links -> protein_targets FK missing: 0",
                "hold list: MET only",
                "```",
                "",
                "판정: 통과",
            ]
        )

    lines.extend(
        [
            "",
            "## 다음 단계",
            "",
            "```text",
            "1. reviewed seed CSV를 사람이 최종 확인",
            "2. MET multi-hit를 수동 검토",
            "3. protein_targets / target_protein_links DB seed 적재 스크립트 작성",
            "4. 이후 AlphaFold DB 구조 조회는 별도 단계에서 실행",
            "```",
        ]
    )
    (ALPHAFOLD / "reviewed_seed_summary_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (DOCS / "reviewed_seed_integrity_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    proteins, links, holds = build_seed_rows()
    errors = validate_seed(proteins, links, holds)

    write_csv(
        ALPHAFOLD / "protein_targets_seed_reviewed_v1.csv",
        [
            "protein_id",
            "gene_symbol",
            "uniprot_id",
            "uniprot_entry_name",
            "protein_name",
            "organism",
            "source",
            "review_status",
            "source_raw_texts",
            "diseases",
            "notes",
        ],
        proteins,
    )
    write_csv(
        ALPHAFOLD / "target_protein_links_seed_reviewed_v1.csv",
        [
            "link_id",
            "target_text",
            "normalized_target_text",
            "protein_id",
            "gene_symbol",
            "uniprot_id",
            "mapping_status",
            "confidence",
            "source",
            "raw_json",
        ],
        links,
    )
    write_csv(
        ALPHAFOLD / "uniprot_mapping_hold_v1.csv",
        [
            "suggested_gene_symbol",
            "raw_text",
            "auto_uniprot_id",
            "hit_count",
            "auto_mapping_status",
            "reason",
            "mapping_notes",
        ],
        holds,
    )
    write_summary(proteins, links, holds, errors)

    if errors:
        raise SystemExit("\n".join(errors))


if __name__ == "__main__":
    main()
