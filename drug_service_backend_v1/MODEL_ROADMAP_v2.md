# 모델 로드맵 v2

## 결정

TxGNN은 v1/v2 구현 범위에서 제외합니다.

이유:

```text
1. 현재 후보 약물과 TxGNN/DrugBank node의 매칭 coverage가 제한적입니다.
2. PAH/RA 같은 질병에서 TxGNN score가 붙는 약물이 일부에 그치면 프론트와 사용자 해석이 더 복잡해집니다.
3. Python 3.8 + DGL 0.5.2 실행환경과 EC2 비용 부담이 큽니다.
4. 우리 프로젝트의 핵심 가치는 내부 후보 rank, ADMET, image-modal evidence, Neo4j graph, OpenSearch evidence, RAG/LLM 설명에 있습니다.
```

TxGNN은 삭제가 아니라 future optional 후보로만 보관합니다.

## 다음 진행 3건

```text
1. Neo4j path scoring v1
2. DistMult/TransE KG embedding baseline
3. Bedrock RAG/LLM explanation + chatbot
```

## 1. Neo4j path scoring v1

학습 없이 Neo4j graph path와 기존 property를 기반으로 점수를 계산합니다.

구현 endpoint:

```text
GET /graph/path-score?disease_id=RA&limit=100
```

v1에서는 score를 Neo4j 관계로 저장하지 않고 API에서 계산해 반환합니다. 모든 score row는 `evidence_sources`와 `risk_sources`를 포함합니다.

향후 저장형 관계 후보:

```text
(:Drug)-[:PATH_SCORED_FOR]->(:Disease)
```

## 2. DistMult/TransE KG embedding baseline

우리 Neo4j graph를 export해서 가벼운 KG embedding baseline을 학습합니다.

구현 endpoint:

```text
GET /health/kg-embedding
GET /graph/kg-embedding?disease_id=RA&model=ensemble&limit=50
```

v1에서는 Neo4j 관계로 저장하지 않고 CSV 산출물을 API가 읽어 반환합니다.

향후 저장형 관계 후보:

```text
(:Drug)-[:KG_EMBEDDING_PREDICTED_FOR]->(:Disease)
```

## 3. Bedrock RAG/LLM explanation

LLM이 새 약물을 추천하는 구조가 아니라, 기존 근거를 설명하는 구조로 둡니다.

근거 source:

```text
PostgreSQL rank / ADMET
Neo4j path score
KG embedding score
OpenSearch text evidence
image-modal evidence
```

예정 endpoint:

```text
GET /rag/explain?disease_id=RA&canonical_drug_id=...
POST /chat
```
