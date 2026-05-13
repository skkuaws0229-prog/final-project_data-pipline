# 전체 Docker Compose 검증 v1

생성 시각: 2026-05-13T01:47:54.200040+00:00

## 결과

PASS

## Health

```json
{"status":"ok","database":"ok"}
```

## Diseases API

```json
[{"disease_id":"BRCA","display_name":"Breast cancer","candidate_count":15},{"disease_id":"Colon","display_name":"Colorectal cancer","candidate_count":15},{"disease_id":"HNSC","display_name":"Head and neck squamous cell carcinoma","candidate_count":30},{"disease_id":"IPF","display_name":"Idiopathic pulmonary fibrosis","candidate_count":15},{"disease_id":"Liver","display_name":"Liver cancer","candidate_count":15},{"disease_id":"LUNG","display_name":"Lung cancer","candidate_count":15},{"disease_id":"PAH","display_name":"Pulmonary arterial hypertension","candidate_count":30},{"disease_id":"PDAC","display_name":"Pancreatic ductal adenocarcinoma","candidate_count":30},{"disease_id":"Psoriasis","display_name":"Psoriasis","candidate_count":30},{"disease_id":"RA","display_name":"Rheumatoid arthritis","candidate_count":30},{"disease_id":"STAD","display_name":"Stomach adenocarcinoma","candidate_count":30}]
```

## docker compose ps

```text
NAME                    IMAGE                    COMMAND                  SERVICE    CREATED          STATUS                    PORTS
drug-service-api        drug_service_build-api   "uvicorn app.main:ap…"   api        45 seconds ago   Up 38 seconds             0.0.0.0:8010->8000/tcp, [::]:8010->8000/tcp
drug-service-postgres   postgres:16              "docker-entrypoint.s…"   postgres   45 seconds ago   Up 44 seconds (healthy)   0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp
```

## db-loader logs

```text
COPY 11   diseases
COPY 171  drugs
COPY 255  drug_candidates
COPY 255  admet_results
COPY 33   image_modal_sources
COPY 31   image_modal_clusters
COPY 1694 image_modal_cluster_members
COPY 371  image_modal_drug_evidence
COPY 14   image_modal_reports
COPY 160  canonical_drugs
COPY 171  drug_aliases
COPY 31   disease_aliases
COPY 371  image_modal_evidence_drug_matches
```
