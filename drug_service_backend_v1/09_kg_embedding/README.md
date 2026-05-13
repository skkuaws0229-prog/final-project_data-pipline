# KG Embedding Baseline v1

이 폴더는 DistMult/TransE baseline 산출물입니다.

## 목적

Neo4j graph를 학습 데이터로 변환하고, 가벼운 KG embedding baseline으로 Drug-Disease 점수를 생성합니다.

TxGNN은 v1/v2 범위에서 제외했으므로, 이 단계는 내부 graph 기반 학습 점수를 추가하는 baseline입니다.

## 실행 순서

```bash
python3 09_kg_embedding/build_kg_triples_v1.py
python3 09_kg_embedding/train_kg_embedding_v1.py
```

## 산출물

```text
kg_triples_v1.csv
kg_entities_v1.csv
kg_relations_v1.csv
kg_embedding_scores_v1.csv
kg_embedding_validation_v1.md
```

## API

```text
GET /graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
```

## 해석 주의

- KG embedding score는 설명 가능한 근거 점수가 아닙니다.
- Path scoring과 달리 학습 기반 보조 점수로 사용합니다.
- 프론트/RAG에서는 반드시 path score, evidence source, risk source와 함께 표시해야 합니다.

