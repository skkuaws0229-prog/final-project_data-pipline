# STAD 파이프라인 — 프로젝트 컨텍스트 (CONTEXT)

단일 진실 소스. 에이전트·연구자 공통 참조.

## 개요

- **질병:** 위암 (Stomach adenocarcinoma, **TCGA-STAD**)
- **목표:** drug repurposing 파이프라인 (프로토콜 v2.4) — **코드는 Colon/Lung과 동일 구조**, **데이터만 STAD**
- **기반 프로토콜:** `drug_repurposing_pipeline_protocol.md` v2.4 (Downloads 사본, Scaffold Split §8-3 공식 도입, Colon 기준 이식 예정)
- **참조 코드:** [20260420_new_pre_project_biso_Colon](../20260420_new_pre_project_biso_Colon), [20260416_new_pre_project_biso_Lung](../20260416_new_pre_project_biso_Lung)

## 현재 운영 상태 (2026-04-21 갱신)

- **Step 2 전처리 + depmap 재필터링:** `run_step2_stad.sh` + `filter_stad_depmap_to_labels.py` 기준 주요 산출물 생성 완료 (`labels`, `drug_features`, `data/depmap/depmap_crispr_long_stad`, LINCS 파생 테이블 포함)
- **Step 3 FE:** AWS Batch 실행 완료 (2026-04-21), `features_rows=5118`, sample join `83.3%` 확인. `nextflow run` 시 `-work-dir` 옵션 필수
- **Step 6 실행 경로:** STAD config 기반 wrapper (`scripts/run_step6_stad.sh`) 구성 완료
- **LINCS (GSE92742):** `rebuild_stad_lincs_cell_ids_gse92742.py` 재검증 결과 usable cell은 `AGS`만 확인
- **해석/보고 제약:** STAD 분석에서 LINCS evidence는 AGS-only coverage limitation을 명시해야 함

### LINCS AGS-only 확정 해석 (2026-04-21)

LINCS evidence in STAD is AGS-only under GSE92742 (362 trt_cp signatures).  
This limitation has been triple-verified (2026-04-21):  
(a) GSE92742 primary_site/subtype strict: AGS only  
(b) GSE70138 phase II plate: AGS present but 0 trt_cp; merge/replace yields no gain  
(c) Deep alias/normalize/substring check: no missed stomach cells  
Downstream interpretation relies more heavily on DepMap/GDSC/PRISM axes  
for drug repurposing evidence, with LINCS used as supporting signal for AGS only.

근거 문서:
- `reports/lincs/stad_lincs_cell_id_qc.json` (1차 검증)
- `reports/lincs/stad_lincs_gse70138_verification.json` (2차 검증)
- `reports/lincs/stad_lincs_alias_deep_check.json` (3차 검증)

## 경로

| 구분 | 경로 |
|------|------|
| 로컬 STAD 베이스 | `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1/20260421_new_pre_project_biso_STAD` |
| Raw S3 (팀 적재) | `s3://say2-4team/Stad_raw/` |
| Stad_raw 시드 (공통) | 2026-04-21: `Colon_raw`에서 질병 비특이 디렉터리만 `aws s3 sync` — `GDSC/`, `depmap/`, `drugbank/`, `chembl/`, `admet/`, `LInc1000/`, `gtex/`, `msigdb/`, `opentargets/`, `string/` (제외: `cBioPortal/`, `geo/`, 루트 가공 parquet 4종) |
| Stad_raw STAD 코호트 | 2026-04-21: `scripts/download_stad_cohort_data.sh` — GEO `GSE62254`/`GSE15459` series matrix (NCBI FTP); TCGA-STAD PanCan 2018 스터지 tar는 `https://github.com/labxscut/HCG/releases/download/HCG/stad_tcga_pan_can_atlas_2018.tar.gz` (cBioPortal 동일 스터디 미러, README 근거) → 로컬 `curated_data/` 후 `SYNC_S3=1`으로 `Stad_raw/geo/`, `Stad_raw/cbioportal/` 업로드 |
| Stad_raw GEO suppl + CPTAC 안내 | 2026-04-21: `scripts/sync_stad_geo_suppl_and_cptac_pointer.sh` — NCBI FTP에서 `GSE62254_RAW.tar`, `GSE15459_RAW.tar` 및 `filelist.txt`/`GSE15459_outcome.xls`를 **스트리밍으로** `s3://say2-4team/Stad_raw/geo/.../suppl/`에 적재; CPTAC는 **이미징·단백·오믹스** 포털별 안내를 `configs/README_CPTAC_STAD_ACCESS.md`로 관리 후 동일 스크립트가 `Stad_raw/cptac_stad/`에 업로드 (대용량 본데이터는 팀이 매니페스트 기준으로 선별 적재) |
| ClinicalTrials (위암) | `scripts/download_clinicaltrials_stad.py` 또는 `scripts/download_stad_clinicaltrials.sh` — API v2 `query.cond` 기본 `stomach neoplasms` → `curated_data/additional_sources/clinicaltrials/clinicaltrials_gastric_cancer_*.json`; `SYNC_S3=1`이면 `Stad_raw/additional_sources/clinicaltrials/`로 `aws s3 sync` |
| **COSMIC STAD 가공본** | `scripts/build_cosmic_stad.py` — `additional_sources/cosmic/*.tar` → `curated_data/additional_sources/cosmic_stad/<날짜>/` (Lung `cosmic_lung` 동형 parquet+tsv.gz); `SYNC_S3=1` → `Stad_raw/additional_sources/cosmic_stad/` |
| **GEO GSE84437** | `scripts/download_stad_geo_gse84437.sh` — matrix `GSE84437_series_matrix.txt.gz` + `soft/GSE84437_family.soft.gz` (메타); RAW tar는 `WITH_RAW_TAR=1`; `SYNC_S3=1` → `Stad_raw/geo/GSE84437/` |
| **PDC CPTAC-STAD 파일 매니페스트** | `scripts/fetch_pdc_cptac_stad_manifest.py` — `studyCatalog`+`study`로 CPTAC 위암 연구 선별 후 `filesPerStudy` → `curated_data/cptac_stad/pdc_manifests/<날짜>/`; `SYNC_S3=1` → `Stad_raw/cptac_stad/pdc_manifests/` |
| **일괄 (우선순위 1→3)** | `scripts/fetch_stad_priority_external.sh` — cosmic_stad → GSE84437 → PDC 매니페스트 (`SKIP_COSMIC=1` 등 옵션) |
| 작업 S3 (FE·학습 입력) | `s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/` |

## LINCS (팀 표준 고정 파일)

- **설정:** [lincs_source.json](lincs_source.json) — 현재 기본 `GSE92742` (다중 위장계열 세포주 커버)
- **세포주 목록:** [stad_lincs_cell_ids.json](stad_lincs_cell_ids.json) — GSE92742 `cell_info`/`sig_info` 기준으로 재생성 시 `python3 scripts/rebuild_stad_lincs_cell_ids_gse92742.py --project-root .` (후보 고정 입력: [stad_lincs_cell_ids_candidates_seed.json](stad_lincs_cell_ids_candidates_seed.json))
- **로컬 확보:** `Stad_raw/LInc1000/`에 GSE92742가 아직 없을 수 있음 → 형제 Colon 클론에 이미 있으면 `scripts/link_lincs_gse92742_from_colon.sh`로 `curated_data/lincs/GSE92742` **심볼릭 링크**(원본 미수정). 팀이 S3에 `LInc1000/GSE92742/`를 올리면 `parallel_download_stad.sh`로 동기화.

## Stad_raw 권장 하위 구조 (Colon 동형)

`gdsc/`, `depmap/`, `lincs/GSE92742/` (또는 팀이 바꾼 GSE), `drugbank/`, `chembl/`, `admet/`, `cbioportal/stad_tcga_pan_can_atlas_2018/` (예시 스터디명 — 실제 폴더는 cBio export와 일치), `cbioportal/cptac_stad_*` (CPTAC-STAD), `geo/GSE62254/`, `geo/GSE15459/`, `geo/GSE84437/`, `additional_sources/cosmic_stad/`, `cptac_stad/pdc_manifests/`, 선택 `validation/`, `string/`, `opentargets/`, `msigdb/`

## cBioPortal (메인 코호트)

- **TCGA-STAD:** Pan-Cancer Atlas 스터디 등 — 데이터 카드에 맞는 디렉터리명을 Step 1 수집 시 확정 후 본 문서에 갱신

## Step 6 외부 검증 (설계)

| 소스 | 역할 | 방법 (프로토콜 §10 정렬) |
|------|------|---------------------------|
| **GSE62254** | 독립 환자 코호트 (ACRG) | 발현 기반 proxy, 생존 (가능 시), P@K |
| **GSE15459** | 독립 검증 / 민감도 | 동상 |
| **GSE84437** | 추가 환자 코호트 (matrix + SOFT 메타) | case/sample-level abundance (`series_matrix`); RAW는 선택 |
| **COSMIC (`cosmic_stad/`)** | STAD 스코프 COSMIC | Lung `cosmic_lung`과 동일 산출물 패턴 |
| **CPTAC-STAD** | 환자 단백/포스포 | PDC 매니페스트(`pdc_manifests/`)로 파일 선별 후 실데이터 수신 |
| **PRISM** | 세포주 약물 감수성 | 위장 lineage 서브셋 |
| **COSMIC** | 드라이버·타겟 정합 | STAD/CIN 등 코호트 정의에 맞춤 |
| **ClinicalTrials** | 임상 근거 | Gastric / STAD 검색어 |

## Subtype / 메타데이터 (초안)

- 평가 stratify 후보: Lauren (가용 시), MSI (가용 시)
- 메타만: EBV, 지리적 분류 등 — 코호트별 가용성 확인 후 `CONTEXT` 갱신

## choi_protocol 학습·앙상블·Neo4j (Step 3.5–8)

- **Git 워크스페이스 루트:** `/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest/20260415_preproject_choi_protocol_v1_bisotest-1` — Colon/Lung/STAD 폴더가 공존하는 동일 클론
- **GitHub:** `skkuaws0215/20260415_preproject_choi_protocol_v1_bisotest` — choi_protocol 학습·앙상블 코드는 저장소 내 기존 경로(팀 가이드 `PROTOCOL_CHOI_통합실행가이드` 참조)
- **연결 방식:** 본 프로젝트 `data/` 산출물(`labels.parquet`, `drug_features.parquet`, `depmap/depmap_crispr_long_stad.parquet`, `lincs_stad_drug_level_with_crispr_prefix.parquet`, `drug_target_mapping.parquet`) 경로를 학습 설정에 **STAD S3** (`params.s3_base` 아래 `data/`)로 지정
- **Nextflow dry-run:** 로컬에서 `cd nextflow && nextflow config .` — Batch 전 `params` 해석 확인
- **Neo4j:** Disease 코드 `STAD`, Top-N 속성·검증 필드는 프로토콜 v2.4 Lung §12-2 패턴 복제

## 절대 규칙 요약

1. `curated_data/` 읽기 전용  
2. `Stad_raw/` 직접 수정 금지  
3. Proxy 데이터 사용 시 사용자 확인  
4. 오류 시 중단·보고  
5. **❌ Step 2 QC 경고를 타암종과 "비슷한 패턴"으로 넘기지 말 것.** 지표 이름/수치를 숫자로 직접 비교해 확인할 것. (2026-04-21 시간 소요 이슈; 상세는 `STAD_reproduction_protocol.md` §7.1)  
6. **❌ Nextflow awsbatch executor는 `-work-dir <s3://경로>` 옵션 필수.** 항상 커맨드라인에 명시할 것.  

## 코딩 선호

- Python 3.10, conda `drug4`
- 모든 파일 I/O는 `logs/`에 타임스탬프 로그
