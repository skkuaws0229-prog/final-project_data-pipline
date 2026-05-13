#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timezone
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "09_kg_embedding"
IMPORT = ROOT / "06_graph" / "import"
SEED = 20260513


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str | int | float]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(value, 30.0), -30.0)))


def train_model(model_name: str, triples_idx: list[tuple[int, int, int]], entity_count: int, relation_count: int, dim: int = 48, epochs: int = 350) -> tuple[torch.Tensor, torch.Tensor]:
    random.seed(SEED)
    torch.manual_seed(SEED)
    entity = torch.nn.Embedding(entity_count, dim)
    relation = torch.nn.Embedding(relation_count, dim)
    torch.nn.init.xavier_uniform_(entity.weight)
    torch.nn.init.xavier_uniform_(relation.weight)
    optimizer = torch.optim.Adam([entity.weight, relation.weight], lr=0.02)
    triples = torch.tensor(triples_idx, dtype=torch.long)

    for _ in range(epochs):
        perm = torch.randperm(len(triples))
        for start in range(0, len(triples), 256):
            batch = triples[perm[start : start + 256]]
            neg = batch.clone()
            corrupt_head = torch.rand(len(batch)) < 0.5
            neg[corrupt_head, 0] = torch.randint(0, entity_count, (int(corrupt_head.sum()),))
            neg[~corrupt_head, 2] = torch.randint(0, entity_count, (int((~corrupt_head).sum()),))

            pos_score = score_batch(model_name, entity, relation, batch)
            neg_score = score_batch(model_name, entity, relation, neg)
            loss = -torch.log(torch.sigmoid(pos_score) + 1e-9).mean() - torch.log(torch.sigmoid(-neg_score) + 1e-9).mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            if model_name == "transe":
                entity.weight.data = torch.nn.functional.normalize(entity.weight.data, p=2, dim=1)

    return entity.weight.detach(), relation.weight.detach()


def score_batch(model_name: str, entity: torch.nn.Embedding, relation: torch.nn.Embedding, batch: torch.Tensor) -> torch.Tensor:
    h = entity(batch[:, 0])
    r = relation(batch[:, 1])
    t = entity(batch[:, 2])
    if model_name == "distmult":
        return (h * r * t).sum(dim=1)
    if model_name == "transe":
        return -torch.linalg.vector_norm(h + r - t, ord=1, dim=1)
    raise ValueError(model_name)


def score_pair(model_name: str, entity_weight: torch.Tensor, relation_weight: torch.Tensor, h: int, r: int, t: int) -> float:
    h_vec = entity_weight[h]
    r_vec = relation_weight[r]
    t_vec = entity_weight[t]
    if model_name == "distmult":
        return float((h_vec * r_vec * t_vec).sum().item())
    return float((-torch.linalg.vector_norm(h_vec + r_vec - t_vec, ord=1)).item())


def main() -> None:
    triples = read_csv(OUT / "kg_triples_v1.csv")
    entities = [row["entity_id"] for row in read_csv(OUT / "kg_entities_v1.csv")]
    relations = [row["relation"] for row in read_csv(OUT / "kg_relations_v1.csv")]
    entity_to_idx = {entity: idx for idx, entity in enumerate(entities)}
    relation_to_idx = {relation: idx for idx, relation in enumerate(relations)}
    triples_idx = [(entity_to_idx[row["head"]], relation_to_idx[row["relation"]], entity_to_idx[row["tail"]]) for row in triples]

    dist_entity, dist_relation = train_model("distmult", triples_idx, len(entities), len(relations))
    transe_entity, transe_relation = train_model("transe", triples_idx, len(entities), len(relations))

    drugs = read_csv(IMPORT / "graph_drugs.csv")
    diseases = read_csv(IMPORT / "graph_diseases.csv")
    candidate_edges = read_csv(IMPORT / "graph_candidate_for_edges.csv")
    candidate_lookup = {(row["canonical_drug_id"], row["disease_id"]): row for row in candidate_edges}
    relation_idx = relation_to_idx["CANDIDATE_FOR"]

    raw_scores = []
    for disease in diseases:
        disease_id = disease["disease_id"]
        disease_entity = entity_to_idx[f"disease:{disease_id}"]
        for drug in drugs:
            canonical_drug_id = drug["canonical_drug_id"]
            drug_entity_id = f"drug:{canonical_drug_id}"
            if drug_entity_id not in entity_to_idx:
                continue
            drug_entity = entity_to_idx[drug_entity_id]
            dist_raw = score_pair("distmult", dist_entity, dist_relation, drug_entity, relation_idx, disease_entity)
            transe_raw = score_pair("transe", transe_entity, transe_relation, drug_entity, relation_idx, disease_entity)
            raw_scores.append(
                {
                    "disease_id": disease_id,
                    "canonical_drug_id": canonical_drug_id,
                    "drug_name": drug["primary_drug_name"],
                    "distmult_raw": dist_raw,
                    "transe_raw": transe_raw,
                    "is_known_candidate": "1" if (canonical_drug_id, disease_id) in candidate_lookup else "0",
                    "candidate_rank": candidate_lookup.get((canonical_drug_id, disease_id), {}).get("rank", ""),
                    "candidate_tier": candidate_lookup.get((canonical_drug_id, disease_id), {}).get("tier", ""),
                }
            )

    def normalize(key: str) -> dict[tuple[str, str], float]:
        values_by_disease: dict[str, list[float]] = {}
        for row in raw_scores:
            values_by_disease.setdefault(row["disease_id"], []).append(float(row[key]))
        normalized = {}
        for disease_id, values in values_by_disease.items():
            low, high = min(values), max(values)
            span = high - low if high > low else 1.0
            for row in raw_scores:
                if row["disease_id"] == disease_id:
                    normalized[(row["disease_id"], row["canonical_drug_id"])] = (float(row[key]) - low) / span
        return normalized

    dist_norm = normalize("distmult_raw")
    transe_norm = normalize("transe_raw")
    output_rows = []
    for row in raw_scores:
        key = (row["disease_id"], row["canonical_drug_id"])
        dist_score = dist_norm[key]
        transe_score = transe_norm[key]
        ensemble = (dist_score + transe_score) / 2.0
        output_rows.append(
            {
                "disease_id": row["disease_id"],
                "canonical_drug_id": row["canonical_drug_id"],
                "drug_name": row["drug_name"],
                "distmult_score": round(dist_score, 6),
                "transe_score": round(transe_score, 6),
                "ensemble_score": round(ensemble, 6),
                "is_known_candidate": row["is_known_candidate"],
                "candidate_rank": row["candidate_rank"],
                "candidate_tier": row["candidate_tier"],
            }
        )

    output_rows.sort(key=lambda row: (row["disease_id"], -float(row["ensemble_score"]), row["drug_name"]))
    write_csv(
        OUT / "kg_embedding_scores_v1.csv",
        output_rows,
        ["disease_id", "canonical_drug_id", "drug_name", "distmult_score", "transe_score", "ensemble_score", "is_known_candidate", "candidate_rank", "candidate_tier"],
    )

    known_count = sum(1 for row in output_rows if row["is_known_candidate"] == "1")
    report = [
        "# KG Embedding 검증 리포트 v1",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## 학습 설정",
        "",
        f"- Seed: {SEED}",
        f"- Triples: {len(triples)}",
        f"- Entities: {len(entities)}",
        f"- Relations: {len(relations)}",
        "- Models: DistMult, TransE",
        "",
        "## 산출물",
        "",
        f"- kg_embedding_scores_v1.csv rows: {len(output_rows)}",
        f"- known candidate score rows: {known_count}",
        "",
        "## 해석",
        "",
        "KG embedding score는 graph 구조를 학습한 보조 점수입니다. 최종 추천 근거로 단독 사용하지 않고 path_score, ADMET, image-modal evidence, OpenSearch/RAG 근거와 함께 사용해야 합니다.",
        "",
    ]
    (OUT / "kg_embedding_validation_v1.md").write_text("\n".join(report), encoding="utf-8")
    print(OUT / "kg_embedding_scores_v1.csv")


if __name__ == "__main__":
    main()

