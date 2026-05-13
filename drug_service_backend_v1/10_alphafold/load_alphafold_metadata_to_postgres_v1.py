from __future__ import annotations

import argparse
import csv
import os
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALPHAFOLD = ROOT / "10_alphafold"
DOCS = ROOT / "docs"

STRUCTURE_CSV = ALPHAFOLD / "alphafold_structures_seed_candidates_v1.csv"
PROTEIN_CSV = ALPHAFOLD / "protein_targets_seed_reviewed_v1.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def duplicates(values: list[object]) -> list[object]:
    return [key for key, count in Counter(values).items() if count > 1]


def validate_seed() -> tuple[list[dict[str, str]], list[str]]:
    rows = read_csv(STRUCTURE_CSV)
    protein_rows = read_csv(PROTEIN_CSV)
    protein_ids = {row["protein_id"] for row in protein_rows}
    errors: list[str] = []

    checks = {
        "structure_id duplicate": duplicates([row["structure_id"] for row in rows]),
        "protein_id duplicate": duplicates([row["protein_id"] for row in rows if row["status"] == "to_fetch"]),
        "provider_accession duplicate": duplicates([row["provider_accession"] for row in rows if row["provider_accession"]]),
    }
    for label, dupes in checks.items():
        if dupes:
            errors.append(f"{label}: {dupes}")

    missing_fk = [row["protein_id"] for row in rows if row["protein_id"] not in protein_ids]
    if missing_fk:
        errors.append(f"protein_id missing from reviewed protein seed: {missing_fk}")

    invalid_provider = [row["structure_id"] for row in rows if row["provider"] not in {"alphafold_db", "pdb", "local", "predicted"}]
    if invalid_provider:
        errors.append(f"invalid provider: {invalid_provider}")

    invalid_file_format = [row["structure_id"] for row in rows if row["file_format"] not in {"pdb", "mmcif", "cif"}]
    if invalid_file_format:
        errors.append(f"invalid file_format: {invalid_file_format}")

    invalid_status = [row["structure_id"] for row in rows if row["status"] not in {"available", "to_fetch", "missing", "failed"}]
    if invalid_status:
        errors.append(f"invalid status: {invalid_status}")

    missing_structure_uri = [row["structure_id"] for row in rows if row["status"] == "to_fetch" and not row["structure_uri"]]
    if missing_structure_uri:
        errors.append(f"to_fetch missing structure_uri: {missing_structure_uri}")

    noncanonical = [row["entry_id"] for row in rows if row["entry_id"] != f"AF-{row['uniprot_id']}-F1"]
    if noncanonical:
        errors.append(f"noncanonical entry selected: {noncanonical}")

    bad_plddt = []
    for row in rows:
        if not row["mean_plddt"]:
            continue
        try:
            value = float(row["mean_plddt"])
        except ValueError:
            bad_plddt.append(row["structure_id"])
            continue
        if not 0 <= value <= 100:
            bad_plddt.append(row["structure_id"])
    if bad_plddt:
        errors.append(f"invalid mean_plddt: {bad_plddt}")

    return rows, errors


def write_report(rows: list[dict[str, str]], errors: list[str], applied: bool, db_counts: dict[str, int] | None = None) -> None:
    status_counts = Counter(row["status"] for row in rows)
    lines = [
        "# AlphaFold Metadata DB 적재 검증 v1",
        "",
        "## 목적",
        "",
        "`alphafold_structures_seed_candidates_v1.csv`를 PostgreSQL `alphafold_structures` metadata row로 적재할 수 있는지 검증한다.",
        "구조 파일 다운로드와 S3 업로드는 실행하지 않는다.",
        "",
        "## 입력 파일",
        "",
        "```text",
        "10_alphafold/alphafold_structures_seed_candidates_v1.csv",
        "```",
        "",
        "## Row Count",
        "",
        "| 대상 | rows |",
        "| --- | ---: |",
        f"| alphafold structure metadata seed | {len(rows)} |",
        "",
        "## Status Count",
        "",
        "| status | rows |",
        "| --- | ---: |",
        *[f"| {key} | {status_counts[key]} |" for key in sorted(status_counts)],
        "",
        "## 실행 모드",
        "",
        "```text",
        f"applied_to_db: {str(applied).lower()}",
        "```",
    ]
    if db_counts is not None:
        lines.extend(
            [
                "",
                "## DB Count",
                "",
                "| table | rows |",
                "| --- | ---: |",
                f"| protein_targets | {db_counts.get('protein_targets', 0)} |",
                f"| alphafold_structures | {db_counts.get('alphafold_structures', 0)} |",
            ]
        )

    lines.extend(["", "## 검증 결과", ""])
    if errors:
        lines.extend(["```text", *errors, "```", "", "판정: 실패"])
    else:
        lines.extend(
            [
                "```text",
                "structure_id duplicate: 0",
                "to_fetch protein_id duplicate: 0",
                "provider_accession duplicate: 0",
                "protein_id FK candidate missing: 0",
                "provider invalid: 0",
                "file_format invalid: 0",
                "status invalid: 0",
                "to_fetch structure_uri missing: 0",
                "noncanonical entry selected: 0",
                "mean_plddt invalid: 0",
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
            "status=to_fetch는 구조 파일을 아직 로컬/S3로 받지 않았다는 뜻이다.",
            "structure_uri는 현재 AlphaFold DB 외부 cifUrl이다.",
            "실제 파일을 S3에 저장하는 단계에서 structure_uri를 S3 URI로 바꿀 수 있다.",
            "```",
        ]
    )
    (DOCS / "alphafold_metadata_db_load_validation_v1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_to_db(rows: list[dict[str, str]], database_url: str) -> dict[str, int]:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO alphafold_structures (
                        structure_id, protein_id, provider, provider_accession, version,
                        file_format, structure_uri, source_url, pae_uri, mean_plddt,
                        confidence_summary, license, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (structure_id) DO UPDATE SET
                        protein_id = EXCLUDED.protein_id,
                        provider = EXCLUDED.provider,
                        provider_accession = EXCLUDED.provider_accession,
                        version = EXCLUDED.version,
                        file_format = EXCLUDED.file_format,
                        structure_uri = EXCLUDED.structure_uri,
                        source_url = EXCLUDED.source_url,
                        pae_uri = EXCLUDED.pae_uri,
                        mean_plddt = EXCLUDED.mean_plddt,
                        confidence_summary = EXCLUDED.confidence_summary,
                        license = EXCLUDED.license,
                        status = EXCLUDED.status,
                        updated_at = now()
                    """,
                    (
                        row["structure_id"],
                        row["protein_id"],
                        row["provider"],
                        row["provider_accession"] or None,
                        row["version"] or None,
                        row["file_format"],
                        row["structure_uri"],
                        row["source_url"] or None,
                        row["pae_uri"] or None,
                        float(row["mean_plddt"]) if row["mean_plddt"] else None,
                        row["confidence_summary"] or None,
                        row["license"] or None,
                        row["status"],
                    ),
                )
            cur.execute("SELECT count(*) FROM protein_targets")
            protein_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM alphafold_structures")
            structure_count = cur.fetchone()[0]
        conn.commit()
    return {"protein_targets": protein_count, "alphafold_structures": structure_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load AlphaFold DB metadata candidates into PostgreSQL.")
    parser.add_argument("--apply", action="store_true", help="Actually insert/update PostgreSQL rows.")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    rows, errors = validate_seed()
    if errors:
        write_report(rows, errors, applied=False)
        raise SystemExit("\n".join(errors))

    db_counts = None
    if args.apply:
        if not args.database_url:
            raise SystemExit("DATABASE_URL is required when --apply is used")
        db_counts = apply_to_db(rows, args.database_url)

    write_report(rows, errors, applied=args.apply, db_counts=db_counts)
    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} ok: alphafold_structures={len(rows)}")


if __name__ == "__main__":
    main()
