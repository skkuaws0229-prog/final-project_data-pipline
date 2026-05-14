#!/usr/bin/env python3
import argparse
import csv
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen

import psycopg
from psycopg.rows import dict_row


ROOT = Path(__file__).resolve().parents[1]
STRUCTURE_ROOT = ROOT / "11_structures" / "alphafold"
MANIFEST = ROOT / "10_alphafold" / "alphafold_file_manifest_v1.csv"
S3_BASE = "s3://say2-4team/20260408_new_pre_project_biso/drug_service_build/11_structures/alphafold"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_pending_structures(database_url: str, include_available: bool, limit: int | None) -> list[dict]:
    status_filter = "" if include_available else "WHERE afs.status <> 'available'"
    limit_sql = "LIMIT %(limit)s" if limit else ""
    params = {"limit": limit}
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                  afs.structure_id,
                  afs.structure_uri,
                  afs.structure_source_uri,
                  afs.file_format,
                  afs.status,
                  pt.gene_symbol,
                  pt.uniprot_id
                FROM alphafold_structures afs
                JOIN protein_targets pt ON pt.protein_id = afs.protein_id
                {status_filter}
                ORDER BY pt.gene_symbol, pt.uniprot_id
                {limit_sql}
                """,
                params,
            )
            return [dict(row) for row in cur.fetchall()]


def download_file(url: str, destination: Path, overwrite: bool) -> None:
    if destination.exists() and not overwrite:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "drug-service-alphafold-fetch-v1"})
    with urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())


def update_db(database_url: str, manifest_rows: list[dict], apply: bool) -> None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE alphafold_structures
                  ADD COLUMN IF NOT EXISTS structure_source_uri TEXT,
                  ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT,
                  ADD COLUMN IF NOT EXISTS checksum_sha256 TEXT
                """
            )
            if apply:
                for row in manifest_rows:
                    cur.execute(
                        """
                        UPDATE alphafold_structures
                        SET
                          structure_source_uri = COALESCE(structure_source_uri, %(source_uri)s),
                          structure_uri = %(s3_uri)s,
                          file_size_bytes = %(file_size_bytes)s,
                          checksum_sha256 = %(checksum_sha256)s,
                          status = 'available',
                          updated_at = now()
                        WHERE structure_id = %(structure_id)s
                        """,
                        row,
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError(f"structure_id not updated: {row['structure_id']}")
        conn.commit()


def write_manifest(rows: list[dict]) -> None:
    fieldnames = [
        "structure_id",
        "gene_symbol",
        "uniprot_id",
        "source_uri",
        "local_path",
        "s3_uri",
        "file_size_bytes",
        "checksum_sha256",
    ]
    with MANIFEST.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download AlphaFold structure files and register S3 metadata.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-available", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    structures = fetch_pending_structures(database_url, args.include_available, args.limit)
    manifest_rows = []
    failures = []
    for structure in structures:
        source_uri = structure.get("structure_source_uri") or structure["structure_uri"]
        if not str(source_uri).startswith("http"):
            continue
        uniprot_id = str(structure["uniprot_id"]).upper()
        filename = Path(source_uri).name
        local_path = STRUCTURE_ROOT / uniprot_id / filename
        try:
            download_file(source_uri, local_path, args.overwrite)
            manifest_rows.append(
                {
                    "structure_id": structure["structure_id"],
                    "gene_symbol": structure["gene_symbol"],
                    "uniprot_id": uniprot_id,
                    "source_uri": source_uri,
                    "local_path": str(local_path.relative_to(ROOT)),
                    "s3_uri": f"{S3_BASE}/{uniprot_id}/{filename}",
                    "file_size_bytes": local_path.stat().st_size,
                    "checksum_sha256": sha256_file(local_path),
                }
            )
        except Exception as exc:
            failures.append({"structure_id": structure["structure_id"], "error": str(exc)})

    write_manifest(manifest_rows)
    update_db(database_url, manifest_rows, args.apply)

    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} ok: requested={len(structures)} downloaded={len(manifest_rows)} failures={len(failures)} manifest={MANIFEST}")
    for failure in failures:
        print(f"failure: {failure['structure_id']} {failure['error']}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
