#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "05_validation"
API_BASE = "http://127.0.0.1:8010"
DISEASE_IDS = ["BRCA", "Colon", "HNSC", "IPF", "LUNG", "Liver", "PAH", "PDAC", "Psoriasis", "RA", "STAD"]
PSQL = ["docker", "exec", "-i", "drug-service-postgres", "psql", "-U", "drug_service", "-d", "drug_service"]


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return proc.stdout


def psql_csv(query: str) -> list[dict[str, str]]:
    output = run(PSQL + ["-A", "-F", ",", "-c", query])
    lines = [line for line in output.splitlines() if line and not line.startswith("(")]
    return list(csv.DictReader(lines)) if lines else []


def api_json(path: str, params: dict[str, str | int]) -> dict | list:
    with urlopen(f"{API_BASE}{path}?{urlencode(params)}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def write_csv(path: Path, rows: list[dict[str, str | int]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def duplicate_count(ids: list[str]) -> int:
    counts = Counter(ids)
    return sum(1 for count in counts.values() if count > 1)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    source_duplicate_rows = psql_csv(
        """
        SELECT
          c.disease_id,
          COALESCE(da.canonical_drug_id, c.drug_id) AS canonical_drug_id,
          MIN(d.drug_name) AS example_drug_name,
          COUNT(*)::text AS candidate_rows,
          STRING_AGG(c.candidate_id, '|' ORDER BY c.rank NULLS LAST, c.candidate_id) AS candidate_ids,
          STRING_AGG(COALESCE(c.rank::text, ''), '|' ORDER BY c.rank NULLS LAST, c.candidate_id) AS ranks
        FROM drug_candidates c
        JOIN drugs d ON d.drug_id = c.drug_id
        LEFT JOIN drug_aliases da ON da.source_drug_id = d.drug_id
        GROUP BY c.disease_id, COALESCE(da.canonical_drug_id, c.drug_id)
        HAVING COUNT(*) > 1
        ORDER BY c.disease_id, candidate_rows DESC, example_drug_name;
        """
    )
    write_csv(
        OUT_DIR / "drug_uniqueness_source_duplicates_v1.csv",
        source_duplicate_rows,
        ["disease_id", "canonical_drug_id", "example_drug_name", "candidate_rows", "candidate_ids", "ranks"],
    )

    cross_disease_rows = psql_csv(
        """
        SELECT
          COALESCE(da.canonical_drug_id, c.drug_id) AS canonical_drug_id,
          MIN(d.drug_name) AS primary_drug_name,
          COUNT(DISTINCT c.disease_id)::text AS disease_count,
          STRING_AGG(DISTINCT c.disease_id, '|' ORDER BY c.disease_id) AS diseases
        FROM drug_candidates c
        JOIN drugs d ON d.drug_id = c.drug_id
        LEFT JOIN drug_aliases da ON da.source_drug_id = d.drug_id
        GROUP BY COALESCE(da.canonical_drug_id, c.drug_id)
        HAVING COUNT(DISTINCT c.disease_id) > 1
        ORDER BY COUNT(DISTINCT c.disease_id) DESC, primary_drug_name;
        """
    )
    write_csv(
        OUT_DIR / "cross_disease_drug_relations_v1.csv",
        cross_disease_rows,
        ["canonical_drug_id", "primary_drug_name", "disease_count", "diseases"],
    )

    api_rows = []
    for disease_id in DISEASE_IDS:
        drugs = api_json("/drugs", {"disease_id": disease_id, "limit": 500})
        drug_ids = [item.get("canonical_drug_id") or item.get("drug_id") for item in drugs]
        graph = api_json("/graph/relations", {"disease_id": disease_id, "limit": 200})
        candidate_edges = [edge for edge in graph.get("edges", []) if edge.get("type") == "CANDIDATE_FOR"]
        candidate_drug_ids = [edge.get("source") for edge in candidate_edges]
        path_score = api_json("/graph/path-score", {"disease_id": disease_id, "limit": 200})
        scored_ids = [item.get("canonical_drug_id") for item in path_score.get("scores", [])]
        api_rows.append(
            {
                "disease_id": disease_id,
                "drugs_api_rows": len(drugs),
                "drugs_api_duplicate_drugs": duplicate_count(drug_ids),
                "graph_candidate_edges": len(candidate_edges),
                "graph_candidate_duplicate_drugs": duplicate_count(candidate_drug_ids),
                "path_score_rows": len(scored_ids),
                "path_score_duplicate_drugs": duplicate_count(scored_ids),
            }
        )

    write_csv(
        OUT_DIR / "drug_uniqueness_api_summary_v1.csv",
        api_rows,
        [
            "disease_id",
            "drugs_api_rows",
            "drugs_api_duplicate_drugs",
            "graph_candidate_edges",
            "graph_candidate_duplicate_drugs",
            "path_score_rows",
            "path_score_duplicate_drugs",
        ],
    )

    api_problem_count = sum(
        int(row["drugs_api_duplicate_drugs"]) + int(row["graph_candidate_duplicate_drugs"]) + int(row["path_score_duplicate_drugs"])
        for row in api_rows
    )
    source_duplicate_disease_count = len({row["disease_id"] for row in source_duplicate_rows})
    report = [
        "# Drug Uniqueness 검증 리포트 v1",
        "",
        f"Generated at: {now}",
        "",
        "## 기준",
        "",
        "- 같은 질병 안의 후보/결과/API 목록에서는 같은 `canonical_drug_id`가 중복 노출되면 안 됩니다.",
        "- 같은 약물이 서로 다른 질병에 등장하는 것은 오류가 아니라 cross-disease 관계성 분석 대상입니다.",
        "- image-modal evidence는 같은 약물이 여러 cluster 근거로 여러 번 등장할 수 있으므로 원본 근거 row는 보존합니다.",
        "",
        "## 검증 결과",
        "",
        f"- API presentation duplicate count: {api_problem_count}",
        f"- Source candidate duplicate disease count: {source_duplicate_disease_count}",
        f"- Cross-disease related drugs: {len(cross_disease_rows)}",
        "",
        "## 산출물",
        "",
        "- drug_uniqueness_api_summary_v1.csv",
        "- drug_uniqueness_source_duplicates_v1.csv",
        "- cross_disease_drug_relations_v1.csv",
        "",
        "## 해석",
        "",
        "API presentation duplicate count는 반드시 0이어야 합니다. Source candidate duplicate는 canonicalization 또는 원천 후보 생성 단계에서 같은 질병 안에 같은 canonical drug가 여러 row로 들어온 경우이며, 이후 정규화 단계에서 우선순위 1개로 접거나 canonicalization key를 보강해야 합니다.",
        "",
    ]
    (OUT_DIR / "drug_uniqueness_validation_v1.md").write_text("\n".join(report), encoding="utf-8")
    print(OUT_DIR / "drug_uniqueness_validation_v1.md")
    return 1 if api_problem_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
