#!/usr/bin/env python3
import csv
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "03_normalized" / "candidate_pool.csv"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://drug_service:drug_service_local@localhost:5433/drug_service")


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS candidate_pool (
  candidate_id TEXT PRIMARY KEY,
  disease_id TEXT NOT NULL REFERENCES diseases(disease_id),
  drug_id TEXT,
  canonical_drug_id TEXT,
  drug_name TEXT NOT NULL,
  rank INTEGER,
  tier TEXT,
  score TEXT,
  target TEXT,
  target_pathway TEXT,
  evidence_summary TEXT,
  canonical_smiles TEXT,
  source_file TEXT NOT NULL,
  source_row_number INTEGER NOT NULL,
  raw_json JSONB NOT NULL,
  is_final_candidate BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_candidate_pool_disease_rank
  ON candidate_pool(disease_id, rank);

CREATE INDEX IF NOT EXISTS idx_candidate_pool_canonical
  ON candidate_pool(canonical_drug_id);
"""


INSERT_SQL = """
INSERT INTO candidate_pool (
  candidate_id,
  disease_id,
  drug_id,
  canonical_drug_id,
  drug_name,
  rank,
  tier,
  score,
  target,
  target_pathway,
  evidence_summary,
  canonical_smiles,
  source_file,
  source_row_number,
  raw_json,
  is_final_candidate
) VALUES (
  %(candidate_id)s,
  %(disease_id)s,
  %(drug_id)s,
  %(canonical_drug_id)s,
  %(drug_name)s,
  %(rank)s,
  %(tier)s,
  %(score)s,
  %(target)s,
  %(target_pathway)s,
  %(evidence_summary)s,
  %(canonical_smiles)s,
  %(source_file)s,
  %(source_row_number)s,
  %(raw_json)s,
  %(is_final_candidate)s
)
"""


def nullable(value: str) -> str | None:
    return value if value != "" else None


def nullable_int(value: str) -> int | None:
    if value == "":
        return None
    return int(value)


def main() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_SQL)
            cur.execute("TRUNCATE TABLE candidate_pool")
            with CSV_PATH.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                count = 0
                for row in reader:
                    payload = {
                        **row,
                        "drug_id": nullable(row["drug_id"]),
                        "canonical_drug_id": nullable(row["canonical_drug_id"]),
                        "rank": nullable_int(row["rank"]),
                        "tier": nullable(row["tier"]),
                        "score": nullable(row["score"]),
                        "target": nullable(row["target"]),
                        "target_pathway": nullable(row["target_pathway"]),
                        "evidence_summary": nullable(row["evidence_summary"]),
                        "canonical_smiles": nullable(row["canonical_smiles"]),
                        "source_row_number": int(row["source_row_number"]),
                        "is_final_candidate": row["is_final_candidate"].lower() == "true",
                    }
                    cur.execute(INSERT_SQL, payload)
                    count += 1
            cur.execute(
                """
                UPDATE candidate_pool pool
                SET is_final_candidate = true
                FROM drug_candidates final
                LEFT JOIN drug_aliases alias ON alias.source_drug_id = final.drug_id
                WHERE pool.disease_id = final.disease_id
                  AND (
                    NULLIF(pool.canonical_drug_id, '') = COALESCE(alias.canonical_drug_id, final.drug_id)
                    OR lower(pool.drug_name) = lower((SELECT drug_name FROM drugs WHERE drug_id = final.drug_id))
                  )
                """
            )
            cur.execute(
                """
                INSERT INTO candidate_pool (
                  candidate_id,
                  disease_id,
                  drug_id,
                  canonical_drug_id,
                  drug_name,
                  rank,
                  tier,
                  score,
                  target,
                  target_pathway,
                  evidence_summary,
                  canonical_smiles,
                  source_file,
                  source_row_number,
                  raw_json,
                  is_final_candidate
                )
                SELECT
                  'poolfinal_' || final.candidate_id,
                  final.disease_id,
                  final.drug_id,
                  COALESCE(alias.canonical_drug_id, final.drug_id),
                  drug.drug_name,
                  final.rank,
                  final.tier,
                  final.score,
                  final.target,
                  final.target_pathway,
                  final.evidence_summary,
                  drug.canonical_smiles,
                  final.source_file,
                  final.source_row_number,
                  final.raw_json,
                  true
                FROM drug_candidates final
                JOIN drugs drug ON drug.drug_id = final.drug_id
                LEFT JOIN drug_aliases alias ON alias.source_drug_id = final.drug_id
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM candidate_pool pool
                  WHERE pool.disease_id = final.disease_id
                    AND (
                      NULLIF(pool.canonical_drug_id, '') = COALESCE(alias.canonical_drug_id, final.drug_id)
                      OR lower(pool.drug_name) = lower(drug.drug_name)
                    )
                )
                """
            )
            cur.execute("SELECT COUNT(*) FROM candidate_pool")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM candidate_pool WHERE is_final_candidate")
            final_count = cur.fetchone()[0]
        conn.commit()
    print(f"candidate_pool_loaded={count}")
    print(f"candidate_pool_total={total}")
    print(f"candidate_pool_final_marked={final_count}")


if __name__ == "__main__":
    main()
