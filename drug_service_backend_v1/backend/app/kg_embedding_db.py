import csv
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=1)
def load_kg_scores() -> list[dict[str, str]]:
    path = Path(settings.kg_embedding_scores_path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def get_kg_scores(disease_id: str, model: str, limit: int) -> list[dict]:
    score_field = {
        "distmult": "distmult_score",
        "transe": "transe_score",
        "ensemble": "ensemble_score",
    }[model]
    rows = [row for row in load_kg_scores() if row["disease_id"] == disease_id]
    rows.sort(key=lambda row: (-float(row[score_field]), row["drug_name"]))
    results = []
    for row in rows[:limit]:
        results.append(
            {
                "disease_id": row["disease_id"],
                "canonical_drug_id": row["canonical_drug_id"],
                "drug_name": row["drug_name"],
                "kg_score": float(row[score_field]),
                "distmult_score": float(row["distmult_score"]),
                "transe_score": float(row["transe_score"]),
                "ensemble_score": float(row["ensemble_score"]),
                "is_known_candidate": row["is_known_candidate"] == "1",
                "candidate_rank": int(row["candidate_rank"]) if row["candidate_rank"] else None,
                "candidate_tier": row["candidate_tier"] or None,
            }
        )
    return results

