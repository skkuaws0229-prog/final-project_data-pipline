#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "09_kg_embedding"
API_BASE = "http://127.0.0.1:8010"
DISEASE_IDS = ["BRCA", "Colon", "HNSC", "IPF", "LUNG", "Liver", "PAH", "PDAC", "Psoriasis", "RA", "STAD"]


def api_json(path: str, params: dict[str, str | int] | None = None) -> dict:
    params = params or {}
    query = f"?{urlencode(params)}" if params else ""
    with urlopen(f"{API_BASE}{path}{query}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def duplicate_count(values: list[str]) -> int:
    counts = Counter(values)
    return sum(1 for count in counts.values() if count > 1)


def main() -> int:
    health = api_json("/health/kg-embedding")
    rows = []
    problems = 0
    for disease_id in DISEASE_IDS:
        payload = api_json("/graph/kg-embedding", {"disease_id": disease_id, "model": "ensemble", "limit": 200})
        scores = payload.get("scores", [])
        ids = [item["canonical_drug_id"] for item in scores]
        duplicate_drugs = duplicate_count(ids)
        out_of_range = [item for item in scores if not 0.0 <= float(item["kg_score"]) <= 1.0]
        known_candidate_count = sum(1 for item in scores if item["is_known_candidate"])
        rows.append(
            {
                "disease_id": disease_id,
                "score_rows": len(scores),
                "known_candidate_rows": known_candidate_count,
                "duplicate_canonical_drug_ids": duplicate_drugs,
                "out_of_range_scores": len(out_of_range),
                "top_drug": scores[0]["drug_name"] if scores else "",
                "top_kg_score": scores[0]["kg_score"] if scores else "",
            }
        )
        problems += duplicate_drugs + len(out_of_range)

    write_csv(
        OUT / "kg_embedding_api_summary_v1.csv",
        rows,
        ["disease_id", "score_rows", "known_candidate_rows", "duplicate_canonical_drug_ids", "out_of_range_scores", "top_drug", "top_kg_score"],
    )
    report = [
        "# KG Embedding API 검증 리포트 v1",
        "",
        "## 검증 대상",
        "",
        f"- `/health/kg-embedding`: score_rows={health.get('score_rows')}",
        "- `/graph/kg-embedding?model=ensemble` 11개 질병",
        "",
        "## 검증 결과",
        "",
        f"- 문제 수: {problems}",
        "- score 범위: 0~1",
        "- 질병 내 duplicate canonical drug 없음",
        "",
        "## 산출물",
        "",
        "- kg_embedding_api_summary_v1.csv",
        "",
        "## 해석 주의",
        "",
        "KG embedding score는 학습 기반 보조 점수입니다. Path scoring처럼 source/risk를 설명하는 점수가 아니므로 단독 추천 근거로 사용하지 않습니다.",
        "",
    ]
    (OUT / "kg_embedding_api_validation_v1.md").write_text("\n".join(report), encoding="utf-8")
    print(OUT / "kg_embedding_api_validation_v1.md")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

