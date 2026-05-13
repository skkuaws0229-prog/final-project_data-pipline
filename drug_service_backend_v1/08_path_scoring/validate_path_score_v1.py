from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


DISEASE_IDS = [
    "BRCA",
    "Colon",
    "HNSC",
    "IPF",
    "LUNG",
    "Liver",
    "PAH",
    "PDAC",
    "Psoriasis",
    "RA",
    "STAD",
]


def fetch_json(base_url: str, path: str, params: dict[str, str | int]) -> dict:
    url = f"{base_url.rstrip('/')}{path}?{urlencode(params)}"
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
    out_dir = Path(__file__).resolve().parent
    summary_path = out_dir / "path_score_summary_v1.csv"
    report_path = out_dir / "path_score_validation_v1.md"

    rows = []
    problems = []
    for disease_id in DISEASE_IDS:
        payload = fetch_json(base_url, "/graph/path-score", {"disease_id": disease_id, "limit": 200})
        scores = payload.get("scores", [])
        ids = [item.get("canonical_drug_id") for item in scores]
        duplicate_ids = len(ids) - len(set(ids))
        out_of_range = [
            item
            for item in scores
            if not (0.0 <= float(item.get("path_score", -1)) <= 1.0)
            or not (0.0 <= float(item.get("positive_score", -1)) <= 1.0)
            or not (0.0 <= float(item.get("risk_penalty", -1)) <= 1.0)
        ]
        missing_evidence = [item for item in scores if not item.get("evidence_sources")]
        top = scores[0] if scores else {}
        source_types = sorted(
            {
                source.get("source_type")
                for item in scores
                for source in item.get("evidence_sources", [])
                if source.get("source_type")
            }
        )
        risk_source_count = sum(len(item.get("risk_sources", [])) for item in scores)

        rows.append(
            {
                "disease_id": disease_id,
                "score_count": len(scores),
                "duplicate_canonical_drug_ids": duplicate_ids,
                "out_of_range_scores": len(out_of_range),
                "missing_evidence_sources": len(missing_evidence),
                "risk_source_count": risk_source_count,
                "top_drug": top.get("drug_name", ""),
                "top_path_score": top.get("path_score", ""),
                "evidence_source_types": "|".join(source_types),
            }
        )
        if duplicate_ids or out_of_range or missing_evidence:
            problems.append(disease_id)

    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    total_scores = sum(row["score_count"] for row in rows)
    report = [
        "# Path Scoring 검증 리포트 v1",
        "",
        "## 검증 대상",
        "",
        f"- API: `{base_url}/graph/path-score`",
        "- 질병: BRCA, Colon, HNSC, IPF, LUNG, Liver, PAH, PDAC, Psoriasis, RA, STAD",
        "- 제외 질병: OV, SKCM",
        "",
        "## 검증 항목",
        "",
        "- 11개 질병 endpoint 200 응답",
        "- `canonical_drug_id` 중복 여부",
        "- `path_score`, `positive_score`, `risk_penalty` 범위 0~1 여부",
        "- 각 score row의 `evidence_sources` 존재 여부",
        "- `risk_sources` 반환 구조 확인",
        "",
        "## 결과",
        "",
        f"- 전체 score row: {total_scores}",
        f"- 문제 발생 질병 수: {len(problems)}",
        f"- CSV 요약: `{summary_path.name}`",
        "",
        "## 비고",
        "",
        "`path_score`는 최종 임상 판단 점수가 아니라, 내부 후보 rank, ADMET, image-modal evidence, target overlap을 합친 설명 가능한 기준 점수입니다. RAG/LLM 설명에서는 반드시 `evidence_sources`와 `risk_sources`를 함께 사용해야 합니다.",
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"Wrote {summary_path}")
    print(f"Wrote {report_path}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

