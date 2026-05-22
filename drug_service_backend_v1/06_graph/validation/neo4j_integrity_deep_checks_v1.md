# Neo4j Deep Integrity Checks v1

## 목적

이 문서는 적재된 Neo4j graph를 Cypher로 검증한 결과입니다. 검증 항목은 중복 relationship, orphan node, 필수 속성 blank, disease scope mismatch, alias 표시 중복 후보, TargetConcept 정리 후보입니다.

이 리포트는 graph 무결성 확인과 React v2 인수인계를 위한 자료입니다. 현재 단계에서 source data 삭제를 권장하지 않습니다.

## 요약

```text
Duplicate CANDIDATE_FOR candidate_id relationships: 0
Duplicate ImageEvidence -> Drug SUPPORTS_DRUG pairs: 0
Orphan nodes: 0
Required blank fields: 0
Disease-scope mismatches: 0
Alias display duplicate groups: 6
TargetConcept review candidates: 존재, v2 classification 필요
```

## 1. 중복 Relationship 검증

Cypher 의도:

```cypher
MATCH (:Drug)-[r:CANDIDATE_FOR]->(:Disease)
WITH r.candidate_id AS id, count(r) AS c
WHERE c > 1
RETURN id, c;
```

검증 결과:

```text
중복 candidate_id relationship 없음
중복 ImageEvidence -> Drug SUPPORTS_DRUG pair 없음
```

## 2. Orphan Node 검증

Cypher 의도:

```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n), count(n);
```

검증 결과:

```text
관계 없이 떠 있는 orphan node 없음
```

## 3. 필수 속성 Blank 검증

확인한 필수 표시/연결 속성:

```text
Disease.display_name
Drug.primary_drug_name
ImageEvidence.drug_name
TargetConcept.concept_text
```

검증 결과:

```text
필수 속성 blank 없음
```

## 4. Disease Scope Mismatch 검증

확인 항목:

```text
Disease -> ImageCluster disease_id 일관성
ImageCluster -> ImageEvidence disease_id 일관성
```

검증 결과:

```text
disease_id scope mismatch 없음
```

## 5. Alias 중복 표시 후보

중복 alias 표시 후보:

```text
Unnamed JAK1 preclinical compound: 7 alias rows
Bleomycin: 2 alias rows
Dactinomycin: 2 alias rows
LESTAURTINIB: 2 alias rows
Ruxolitinib: 2 alias rows
STAUROSPORINE: 2 alias rows
```

해석:

```text
Graph 무결성 오류가 아닙니다.
여러 source row 또는 대소문자/display variant가 같은 canonical drug로 매핑된 결과입니다.
Neo4j에는 provenance 보존을 위해 alias row를 유지합니다.
API/frontend에서 사용자에게 표시할 때는 normalized_alias 기준으로 distinct-collapse 처리하는 것이 좋습니다.
```

## 6. TargetConcept 정리 후보

v1에서는 TargetConcept를 의도적으로 raw text로 보존합니다. Cypher 검증에서 v2 분류/정규화가 필요한 concept들이 확인되었습니다.

```text
generic_bucket: Other, Other, kinases
compound_list: MEK1, MEK2; PARP1, PARP2; CDK4, CDK6 등
pathway_or_compound: PI3K/MTOR signaling; JAK/STAT inflammatory axis; B-cell / BTK axis
mechanism_axis: RA inflammatory kinase axis
long_free_text: source row에서 생성된 긴 multi-token target/pathway 문자열
compound_phrase: Protein stability and degradation; ECM remodeling and angiogenesis
```

Relation count 기준 상위 review 후보:

```text
PI3K/MTOR signaling: 50
Protein stability and degradation: 21
Other: 17
JAK/STAT inflammatory axis: 14
B-cell / BTK axis: 10
MEK1, MEK2: 8
Endothelin + NO/PDE5 pathway: 7
Other, kinases: 7
```

해석:

```text
삭제하지 않습니다.
v2에서 Gene, Pathway, Mechanism, DrugClass, FreeText로 분류합니다.
긴 복합 target 문자열은 이후 normalized concept token으로 parsing하는 것이 좋습니다.
```

## 최종 판단

현재 단계에서 삭제할 graph data는 없습니다. Graph는 참조 무결성 기준으로 유효합니다. 남은 이슈는 display normalization과 v2 semantic classification 작업입니다.
