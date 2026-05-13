from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
DOCS = ROOT / "docs"
OUT_CSV = ALPHAFOLD / "candidate_protein_structure_links_seed_v1.csv"


def stable_id(prefix: str, *parts: str, length: int = 16) -> str:
    raw = "||".join(str(part or "").strip().lower() for part in parts)
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:length]}"


def target_matches(source_target: str | None, target_text: str) -> bool:
    if not source_target or not target_text:
        return False
    pattern = rf"(?<![A-Za-z0-9]){re.escape(target_text)}(?![A-Za-z0-9])"
    return re.search(pattern, source_target, flags=re.IGNORECASE) is not None


def split_diseases(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split("|") if part.strip()}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fetch_rows(database_url: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  tpl.link_id,
                  tpl.target_text,
                  tpl.protein_id,
                  tpl.mapping_status,
                  tpl.confidence,
                  tpl.raw_json,
                  afs.structure_id
                FROM target_protein_links tpl
                JOIN alphafold_structures afs ON afs.protein_id = tpl.protein_id
                WHERE afs.status IN ('to_fetch', 'available')
                ORDER BY tpl.target_text, tpl.protein_id
                """
            )
            target_links = list(cur.fetchall())
            cur.execute(
                """
                SELECT dc.candidate_id, dc.disease_id, dc.drug_id, d.drug_name, dc.target, dc.target_pathway, dc.source_file
                FROM drug_candidates dc
                LEFT JOIN drugs d ON d.drug_id = dc.drug_id
                WHERE target IS NOT NULL AND target <> ''
                ORDER BY dc.disease_id, dc.candidate_id
                """
            )
            candidates = list(cur.fetchall())
            cur.execute(
                """
                SELECT evidence_id, disease_id, drug_id, drug_name, target, target_pathway, source_file
                FROM image_modal_drug_evidence
                WHERE target IS NOT NULL AND target <> ''
                ORDER BY disease_id, evidence_id
                """
            )
            evidence_rows = list(cur.fetchall())
            cur.execute(
                """
                SELECT source_drug_id, canonical_drug_id
                FROM drug_aliases
                WHERE source_drug_id IS NOT NULL
                UNION
                SELECT primary_source_drug_id AS source_drug_id, canonical_drug_id
                FROM canonical_drugs
                WHERE primary_source_drug_id IS NOT NULL
                """
            )
            canonical_map = {row["source_drug_id"]: row["canonical_drug_id"] for row in cur.fetchall()}
    return target_links, candidates, evidence_rows, canonical_map


def build_rows(database_url: str) -> list[dict[str, str]]:
    target_links, candidates, evidence_rows, canonical_map = fetch_rows(database_url)
    rows: dict[str, dict[str, str]] = {}

    for source in candidates:
        for link in target_links:
            raw_json = link["raw_json"] or {}
            allowed_diseases = split_diseases(raw_json.get("diseases"))
            if source["disease_id"] not in allowed_diseases:
                continue
            if not target_matches(source["target"], link["target_text"]):
                continue
            context_id = stable_id(
                "cpslink",
                "candidate_target",
                source["candidate_id"],
                link["protein_id"],
                link["structure_id"],
                link["target_text"],
            )
            rows[context_id] = {
                "context_id": context_id,
                "disease_id": source["disease_id"],
                "candidate_id": source["candidate_id"],
                "canonical_drug_id": canonical_map.get(source["drug_id"], ""),
                "evidence_id": "",
                "protein_id": link["protein_id"],
                "structure_id": link["structure_id"],
                "target_source": "candidate_target",
                "relation_note": json.dumps(
                    {
                        "matched_target_text": link["target_text"],
                        "drug_id": source["drug_id"],
                        "drug_name": source["drug_name"],
                        "source_target": source["target"],
                        "target_pathway": source["target_pathway"],
                        "mapping_status": link["mapping_status"],
                        "confidence": str(link["confidence"]) if link["confidence"] is not None else "",
                        "source_file": source["source_file"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }

    for source in evidence_rows:
        for link in target_links:
            raw_json = link["raw_json"] or {}
            allowed_diseases = split_diseases(raw_json.get("diseases"))
            if source["disease_id"] not in allowed_diseases:
                continue
            if not target_matches(source["target"], link["target_text"]):
                continue
            context_id = stable_id(
                "cpslink",
                "image_evidence",
                source["evidence_id"],
                link["protein_id"],
                link["structure_id"],
                link["target_text"],
            )
            rows[context_id] = {
                "context_id": context_id,
                "disease_id": source["disease_id"],
                "candidate_id": "",
                "canonical_drug_id": canonical_map.get(source["drug_id"], ""),
                "evidence_id": source["evidence_id"],
                "protein_id": link["protein_id"],
                "structure_id": link["structure_id"],
                "target_source": "image_evidence",
                "relation_note": json.dumps(
                    {
                        "matched_target_text": link["target_text"],
                        "drug_id": source["drug_id"],
                        "drug_name": source["drug_name"],
                        "source_target": source["target"],
                        "target_pathway": source["target_pathway"],
                        "mapping_status": link["mapping_status"],
                        "confidence": str(link["confidence"]) if link["confidence"] is not None else "",
                        "source_file": source["source_file"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }

    return sorted(rows.values(), key=lambda row: (row["disease_id"], row["target_source"], row["context_id"]))


def validate_rows(rows: list[dict[str, str]], database_url: str) -> list[str]:
    import psycopg

    errors: list[str] = []
    checks = {
        "context_id duplicate": [key for key, count in Counter(row["context_id"] for row in rows).items() if count > 1],
        "context semantic duplicate": [
            key
            for key, count in Counter(
                (
                    row["disease_id"],
                    row["candidate_id"],
                    row["evidence_id"],
                    row["protein_id"],
                    row["structure_id"],
                    row["target_source"],
                )
                for row in rows
            ).items()
            if count > 1
        ],
    }
    for label, dupes in checks.items():
        if dupes:
            errors.append(f"{label}: {dupes}")

    invalid_target_source = [
        row["context_id"] for row in rows if row["target_source"] not in {"candidate_target", "image_evidence", "kg_target", "manual"}
    ]
    if invalid_target_source:
        errors.append(f"invalid target_source: {invalid_target_source}")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            db_sets: dict[str, set[str]] = {}
            for label, query in {
                "disease_id": "SELECT disease_id FROM diseases",
                "candidate_id": "SELECT candidate_id FROM drug_candidates",
                "canonical_drug_id": "SELECT canonical_drug_id FROM canonical_drugs",
                "evidence_id": "SELECT evidence_id FROM image_modal_drug_evidence",
                "protein_id": "SELECT protein_id FROM protein_targets",
                "structure_id": "SELECT structure_id FROM alphafold_structures",
            }.items():
                cur.execute(query)
                db_sets[label] = {row[0] for row in cur.fetchall()}

    fk_checks = {
        "disease_id missing": [row["disease_id"] for row in rows if row["disease_id"] not in db_sets["disease_id"]],
        "candidate_id missing": [
            row["candidate_id"] for row in rows if row["candidate_id"] and row["candidate_id"] not in db_sets["candidate_id"]
        ],
        "canonical_drug_id missing": [
            row["canonical_drug_id"]
            for row in rows
            if row["canonical_drug_id"] and row["canonical_drug_id"] not in db_sets["canonical_drug_id"]
        ],
        "evidence_id missing": [row["evidence_id"] for row in rows if row["evidence_id"] and row["evidence_id"] not in db_sets["evidence_id"]],
        "protein_id missing": [row["protein_id"] for row in rows if row["protein_id"] not in db_sets["protein_id"]],
        "structure_id missing": [row["structure_id"] for row in rows if row["structure_id"] not in db_sets["structure_id"]],
    }
    for label, missing in fk_checks.items():
        if missing:
            errors.append(f"{label}: {sorted(set(missing))}")

    return errors


def write_report(rows: list[dict[str, str]], errors: list[str], applied: bool) -> None:
    source_counts = Counter(row["target_source"] for row in rows)
    disease_counts = Counter(row["disease_id"] for row in rows)
    lines = [
        "# Candidate Protein Structure Link 생성/적재 검증 v1",
        "",
        "## 목적",
        "",
        "`drug_candidates`와 `image_modal_drug_evidence`의 target 표현을 `target_protein_links`와 보수적으로 매칭해 `candidate_protein_structure_links` seed를 생성한다.",
        "",
        "## 생성 파일",
        "",
        "```text",
        "10_alphafold/candidate_protein_structure_links_seed_v1.csv",
        "```",
        "",
        "## Row Count",
        "",
        "| 대상 | rows |",
        "| --- | ---: |",
        f"| candidate_protein_structure_links seed | {len(rows)} |",
        "",
        "## Source Count",
        "",
        "| target_source | rows |",
        "| --- | ---: |",
        *[f"| {key} | {source_counts[key]} |" for key in sorted(source_counts)],
        "",
        "## Canonical Drug Mapping",
        "",
        "| 항목 | rows |",
        "| --- | ---: |",
        f"| canonical_drug_id present | {sum(1 for row in rows if row['canonical_drug_id'])} |",
        f"| canonical_drug_id empty | {sum(1 for row in rows if not row['canonical_drug_id'])} |",
        "",
        "## Disease Count",
        "",
        "| disease_id | rows |",
        "| --- | ---: |",
        *[f"| {key} | {disease_counts[key]} |" for key in sorted(disease_counts)],
        "",
        "## 실행 모드",
        "",
        "```text",
        f"applied_to_db: {str(applied).lower()}",
        "```",
        "",
        "## 검증 결과",
        "",
    ]
    if errors:
        lines.extend(["```text", *errors, "```", "", "판정: 실패"])
    else:
        lines.extend(
            [
                "```text",
                "context_id duplicate: 0",
                "context semantic duplicate: 0",
                "target_source invalid: 0",
                "disease_id FK missing: 0",
                "candidate_id FK missing: 0",
                "canonical_drug_id FK missing: 0",
                "evidence_id FK missing: 0",
                "protein_id FK missing: 0",
                "structure_id FK missing: 0",
                "```",
                "",
                "판정: 통과",
            ]
        )
    lines.extend(
        [
            "",
            "## 매칭 정책",
            "",
            "```text",
            "target_protein_links.target_text가 candidate/evidence target 문자열 안에 token 단위로 등장하는 경우만 연결했다.",
            "target_protein_links.raw_json.diseases에 현재 disease_id가 포함된 경우만 연결했다.",
            "복합 target의 모든 구성요소를 임의로 확장하지 않고, reviewed seed에 있는 target 표현만 사용했다.",
            "canonical_drug_id가 비어도 relation_note에 drug_id/drug_name을 보존한다.",
            "```",
        ]
    )
    (DOCS / "candidate_structure_links_validation_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_to_db(rows: list[dict[str, str]], database_url: str) -> None:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO candidate_protein_structure_links (
                      context_id, disease_id, candidate_id, canonical_drug_id, evidence_id,
                      protein_id, structure_id, target_source, relation_note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (context_id) DO UPDATE SET
                      disease_id = EXCLUDED.disease_id,
                      candidate_id = EXCLUDED.candidate_id,
                      canonical_drug_id = EXCLUDED.canonical_drug_id,
                      evidence_id = EXCLUDED.evidence_id,
                      protein_id = EXCLUDED.protein_id,
                      structure_id = EXCLUDED.structure_id,
                      target_source = EXCLUDED.target_source,
                      relation_note = EXCLUDED.relation_note
                    """,
                    (
                        row["context_id"],
                        row["disease_id"],
                        row["candidate_id"] or None,
                        row["canonical_drug_id"] or None,
                        row["evidence_id"] or None,
                        row["protein_id"],
                        row["structure_id"] or None,
                        row["target_source"],
                        row["relation_note"] or None,
                    ),
                )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build candidate/evidence to protein structure context links.")
    parser.add_argument("--apply", action="store_true", help="Actually insert/update PostgreSQL rows.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")

    rows = build_rows(args.database_url)
    errors = validate_rows(rows, args.database_url)
    write_csv(
        OUT_CSV,
        [
            "context_id",
            "disease_id",
            "candidate_id",
            "canonical_drug_id",
            "evidence_id",
            "protein_id",
            "structure_id",
            "target_source",
            "relation_note",
        ],
        rows,
    )
    if errors:
        write_report(rows, errors, applied=False)
        raise SystemExit("\n".join(errors))
    if args.apply:
        apply_to_db(rows, args.database_url)
    write_report(rows, errors, applied=args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} ok: candidate_protein_structure_links={len(rows)}")


if __name__ == "__main__":
    main()
