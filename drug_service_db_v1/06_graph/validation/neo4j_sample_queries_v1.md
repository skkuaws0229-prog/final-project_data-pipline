# Neo4j Sample Queries v1

## 질병 범위 약물 evidence 확인

```cypher
MATCH (drug:Drug)-[r:CANDIDATE_FOR]->(disease:Disease {disease_id:'RA'})
WHERE toLower(drug.primary_drug_name) CONTAINS 'ruxolitinib'
OPTIONAL MATCH (e:ImageEvidence {disease_id:'RA'})-[:SUPPORTS_DRUG]->(drug)
RETURN drug.primary_drug_name AS drug,
       disease.display_name AS disease,
       r.rank AS rank,
       r.tier AS tier,
       count(e) AS ra_evidence_count
LIMIT 5;
```

관찰 결과:

```text
Ruxolitinib, Rheumatoid arthritis, rank 1, pass_admet_gate, RA evidence count 2
```

## Alias lookup

```cypher
MATCH (alias:DrugAlias)-[:ALIAS_OF]->(drug:Drug)
WHERE alias.normalized_alias CONTAINS 'ruxolitinib'
RETURN alias.alias_name, alias.alias_type, drug.primary_drug_name
LIMIT 10;
```

관찰 메모:

```text
Ruxolitinib은 여러 source row가 같은 canonical drug에 매핑되어 alias가 2번 나타납니다.
API/frontend에서 사용자에게 표시할 때는 normalized_alias 기준으로 distinct-collapse 처리하는 것이 좋습니다.
```

## TargetConcept 빈도 확인

```cypher
MATCH (t:TargetConcept)<-[r]-(source)
WHERE type(r) IN ['HAS_TARGET','MENTIONS_TARGET']
RETURN t.concept_type AS concept_type,
       t.concept_text AS concept_text,
       count(r) AS relation_count
ORDER BY relation_count DESC, concept_text
LIMIT 30;
```

정리 후 상위 concept:

```text
DNA replication: 101
Mitosis: 59
PI3K/MTOR signaling: 50
TOP1: 40
JAK1: 25
```

`nan` placeholder target은 graph에서 제거했습니다.
