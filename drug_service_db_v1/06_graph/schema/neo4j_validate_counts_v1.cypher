MATCH (n:Disease) RETURN 'Disease nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:Drug) RETURN 'Drug nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:DrugAlias) RETURN 'DrugAlias nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:DiseaseAlias) RETURN 'DiseaseAlias nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:TargetConcept) RETURN 'TargetConcept nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:ImageCluster) RETURN 'ImageCluster nodes' AS artifact, count(n) AS count
UNION ALL
MATCH (n:ImageEvidence) RETURN 'ImageEvidence nodes' AS artifact, count(n) AS count
UNION ALL
MATCH ()-[r:CANDIDATE_FOR]->() RETURN 'CANDIDATE_FOR edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:HAS_TARGET]->() RETURN 'HAS_TARGET edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:ALIAS_OF]->() RETURN 'ALIAS_OF edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:HAS_IMAGE_CLUSTER]->() RETURN 'HAS_IMAGE_CLUSTER edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:HAS_IMAGE_EVIDENCE]->() RETURN 'HAS_IMAGE_EVIDENCE edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:SUPPORTS_DRUG]->() RETURN 'SUPPORTS_DRUG edges' AS artifact, count(r) AS count
UNION ALL
MATCH ()-[r:MENTIONS_TARGET]->() RETURN 'MENTIONS_TARGET edges' AS artifact, count(r) AS count;
