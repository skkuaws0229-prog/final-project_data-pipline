# Path Scoring 설계 v1

## 배경

TxGNN은 v1/v2 구현 범위에서 제외했습니다. 현재 데이터에서는 TxGNN node 매칭 coverage가 제한적이고, 실행 환경과 EC2 비용 부담이 큽니다.

따라서 먼저 내부 데이터만으로 설명 가능한 기준 점수를 만듭니다.

## 입력 근거

```text
Drug candidate rank / tier / score
ADMET verdict / status / hard_fail / soft_flags
Neo4j Drug-Disease 관계
Image-modal evidence Drug 연결
TargetConcept overlap
```

## 출력 원칙

점수만 반환하지 않고, 반드시 source를 같이 반환합니다.

```text
evidence_sources: 긍정/지원 근거
risk_sources: ADMET risk/penalty 근거
```

이 구조를 유지해야 이후 OpenSearch/Bedrock RAG에서 “왜 이 약물이 추천됐는가”와 “주의할 점은 무엇인가”를 함께 설명할 수 있습니다.

## v1 한계

- target/pathway text는 아직 완전한 ontology normalization이 아닙니다.
- target overlap은 같은 `TargetConcept.target_id` 기준입니다.
- 학습 기반 예측 점수는 아닙니다.
- DistMult/TransE baseline은 다음 단계에서 별도 점수로 추가합니다.

