#!/usr/bin/env python3
import argparse
import hashlib
import os
from pathlib import Path

import psycopg


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a downloaded AlphaFold structure file in PostgreSQL.")
    parser.add_argument("--structure-id", required=True)
    parser.add_argument("--local-file", required=True)
    parser.add_argument("--s3-uri", required=True)
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    local_file = Path(args.local_file)
    if not local_file.exists():
        raise SystemExit(f"local file not found: {local_file}")

    file_size = local_file.stat().st_size
    checksum = sha256_file(local_file)

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
            if args.apply:
                cur.execute(
                    """
                    UPDATE alphafold_structures
                    SET
                      structure_source_uri = COALESCE(structure_source_uri, %(source_uri)s),
                      structure_uri = %(s3_uri)s,
                      file_size_bytes = %(file_size)s,
                      checksum_sha256 = %(checksum)s,
                      status = 'available',
                      updated_at = now()
                    WHERE structure_id = %(structure_id)s
                    """,
                    {
                        "structure_id": args.structure_id,
                        "s3_uri": args.s3_uri,
                        "source_uri": args.source_uri,
                        "file_size": file_size,
                        "checksum": checksum,
                    },
                )
                if cur.rowcount != 1:
                    raise SystemExit(f"structure_id not updated: {args.structure_id}")
            conn.commit()

    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} ok: {args.structure_id} size={file_size} sha256={checksum}")


if __name__ == "__main__":
    main()
