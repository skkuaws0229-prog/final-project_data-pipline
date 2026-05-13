from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
DOCS = ROOT / "docs"

PROTEIN_CSV = ALPHAFOLD / "protein_targets_seed_reviewed_v1.csv"
LINK_CSV = ALPHAFOLD / "target_protein_links_seed_reviewed_v1.csv"
HOLD_CSV = ALPHAFOLD / "uniprot_mapping_hold_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def duplicates(values: list[object]) -> list[object]:
    return [key for key, count in Counter(values).items() if count > 1]


def validate_seed() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[str]]:
    proteins = read_csv(PROTEIN_CSV)
    links = read_csv(LINK_CSV)
    holds = read_csv(HOLD_CSV)
    errors: list[str] = []

    protein_ids = [row["protein_id"] for row in proteins]
    uniprot_ids = [row["uniprot_id"] for row in proteins if row["uniprot_id"]]
    gene_symbols = [row["gene_symbol"].upper() for row in proteins if row["gene_symbol"]]
    link_ids = [row["link_id"] for row in links]
    link_keys = [(row["target_text"].lower(), row["protein_id"]) for row in links]
    protein_id_set = set(protein_ids)

    checks = {
        "protein_id duplicate": duplicates(protein_ids),
        "uniprot_id duplicate": duplicates(uniprot_ids),
        "gene_symbol duplicate": duplicates(gene_symbols),
        "link_id duplicate": duplicates(link_ids),
        "target_text+protein_id duplicate": duplicates(link_keys),
    }
    for label, dupes in checks.items():
        if dupes:
            errors.append(f"{label}: {dupes}")

    missing_fk = [row["protein_id"] for row in links if row["protein_id"] not in protein_id_set]
    if missing_fk:
        errors.append(f"target_protein_links protein_id missing from protein_targets: {missing_fk}")

    bad_mapping_status = [
        row["mapping_status"] for row in links if row["mapping_status"] not in {"exact", "alias", "manual", "unresolved", "rejected"}
    ]
    if bad_mapping_status:
        errors.append(f"invalid mapping_status: {bad_mapping_status}")

    bad_confidence = []
    for row in links:
        try:
            value = float(row["confidence"]) if row["confidence"] else None
        except ValueError:
            bad_confidence.append(row["link_id"])
            continue
        if value is not None and not 0 <= value <= 1:
            bad_confidence.append(row["link_id"])
    if bad_confidence:
        errors.append(f"invalid confidence: {bad_confidence}")

    for row in links:
        try:
            json.loads(row["raw_json"])
        except json.JSONDecodeError:
            errors.append(f"invalid raw_json: {row['link_id']}")

    if len(holds) != 1 or holds[0]["suggested_gene_symbol"].upper() != "MET":
        errors.append("hold list expected to contain only MET")

    return proteins, links, holds, errors


def write_report(
    proteins: list[dict[str, str]],
    links: list[dict[str, str]],
    holds: list[dict[str, str]],
    errors: list[str],
    applied: bool,
) -> None:
    lines = [
        "# Reviewed UniProt Seed DB 적재 검증 v1",
        "",
        "## 목적",
        "",
        "`protein_targets_seed_reviewed_v1.csv`와 `target_protein_links_seed_reviewed_v1.csv`를 PostgreSQL seed로 적재하기 전 검증한다.",
        "기본 실행은 dry-run이며, 실제 DB 변경은 `--apply` 실행 시에만 수행한다.",
        "",
        "## 입력 파일",
        "",
        "```text",
        "10_alphafold/protein_targets_seed_reviewed_v1.csv",
        "10_alphafold/target_protein_links_seed_reviewed_v1.csv",
        "10_alphafold/uniprot_mapping_hold_v1.csv",
        "```",
        "",
        "## Row Count",
        "",
        "| 대상 | rows |",
        "| --- | ---: |",
        f"| protein_targets seed | {len(proteins)} |",
        f"| target_protein_links seed | {len(links)} |",
        f"| hold list | {len(holds)} |",
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
                "protein_id duplicate: 0",
                "uniprot_id duplicate: 0",
                "gene_symbol duplicate: 0",
                "link_id duplicate: 0",
                "target_text + protein_id duplicate: 0",
                "target_protein_links -> protein_targets FK missing: 0",
                "mapping_status enum invalid: 0",
                "confidence invalid: 0",
                "raw_json invalid: 0",
                "hold list: MET only",
                "```",
                "",
                "판정: 통과",
            ]
        )
    lines.extend(
        [
            "",
            "## 주의",
            "",
            "```text",
            "이 loader는 protein_targets와 target_protein_links만 다룬다.",
            "alphafold_structures와 candidate_protein_structure_links는 구조 metadata 확보 후 별도 단계에서 적재한다.",
            "AlphaFold DB API 호출과 구조 다운로드는 이 단계에서 실행하지 않는다.",
            "```",
        ]
    )
    (DOCS / "reviewed_seed_db_load_validation_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_to_db(proteins: list[dict[str, str]], links: list[dict[str, str]], database_url: str) -> None:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for row in proteins:
                cur.execute(
                    """
                    INSERT INTO protein_targets (
                        protein_id, gene_symbol, uniprot_id, protein_name, organism, source
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (protein_id) DO UPDATE SET
                        gene_symbol = EXCLUDED.gene_symbol,
                        uniprot_id = EXCLUDED.uniprot_id,
                        protein_name = EXCLUDED.protein_name,
                        organism = EXCLUDED.organism,
                        source = EXCLUDED.source
                    """,
                    (
                        row["protein_id"],
                        row["gene_symbol"] or None,
                        row["uniprot_id"] or None,
                        row["protein_name"] or None,
                        row["organism"],
                        row["source"],
                    ),
                )
            for row in links:
                cur.execute(
                    """
                    INSERT INTO target_protein_links (
                        link_id, target_text, normalized_target_text, protein_id,
                        mapping_status, confidence, source, raw_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (link_id) DO UPDATE SET
                        target_text = EXCLUDED.target_text,
                        normalized_target_text = EXCLUDED.normalized_target_text,
                        protein_id = EXCLUDED.protein_id,
                        mapping_status = EXCLUDED.mapping_status,
                        confidence = EXCLUDED.confidence,
                        source = EXCLUDED.source,
                        raw_json = EXCLUDED.raw_json
                    """,
                    (
                        row["link_id"],
                        row["target_text"],
                        row["normalized_target_text"],
                        row["protein_id"] or None,
                        row["mapping_status"],
                        float(row["confidence"]) if row["confidence"] else None,
                        row["source"],
                        row["raw_json"],
                    ),
                )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load reviewed UniProt seed CSVs into PostgreSQL.")
    parser.add_argument("--apply", action="store_true", help="Actually insert/update PostgreSQL rows.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    proteins, links, holds, errors = validate_seed()
    if errors:
        write_report(proteins, links, holds, errors, applied=False)
        raise SystemExit("\n".join(errors))

    if args.apply:
        if not args.database_url:
            raise SystemExit("DATABASE_URL is required when --apply is used")
        apply_to_db(proteins, links, args.database_url)

    write_report(proteins, links, holds, errors, applied=args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} ok: proteins={len(proteins)} links={len(links)} holds={len(holds)}")


if __name__ == "__main__":
    main()
