# 약물 재창출(Drug Repurposing) 파이프라인 프로토콜
## 적응증 확장 재현 가이드

> 작성일: 2026-04-17
> 최종 수정일: 2026-04-20
> 버전: v2.3
> 목적: BRCA v3.1 파이프라인을 타 질병에 동일하게 적용하여 약물 재창출 랭킹을 생성하는 재현 프로토콜
> 원칙: 프로토콜(코드) = 원본 그대로 사용 / 데이터 = 해당 질병의 실제 데이터만 사용

---

## 1. 적용 현황

| 단계 | 질병 | 유형 | 상태 | 완료일 | 비고 |
|:----:|------|:----:|:----:|:------:|------|
| 1 | 유방암 (BRCA) | 암종 | ✅ 완료 | - | 기준 파이프라인 |
| 2 | 폐암 (Lung) | 암종 | ✅ 현재 재현본 완료 | 2026-04-29 | All-Lung 기준 current rerun 완료. Step5~7 재실행, Top30 finalized, Step6/7 산출물 갱신 완료. NSCLC-only는 향후 선택 재실험 |
| 3 | 대장암 (Colorectal) | 암종 | 예정 | - | |
| 4 | IPF (특발성 폐섬유증) | 비암종 | 예정 | - | |
| 5 | RA (류마티스 관절염) | 비암종 | 예정 | - | |

### 1-1. Lung 파이프라인 Step별 완료 현황

| Step | 내용 | 상태 | 비고 |
|:----:|------|:----:|------|
| 1-2 | 데이터 수집/전처리 | ✅ | 125,427 pairs (SCLC 포함) |
| 3 | LINCS + Nextflow FE | ✅ | SCLC 2개 세포주 포함 |
| 3.5 | Feature Selection | ✅ | 20,512 → 5,764 (71.9% 감축) |
| 4 | 15개 모델 학습 (Phase 2A/2B/2C) | ✅ | 최고: CatBoost 2C (0.5030) |
| 5 | 앙상블 (24개 실험) | ✅ | 양수 Gain 4/24 |
| 6 | 외부검증 | ✅ | current Top30 기준 재실행 완료. PRISM 19, ClinicalTrials 10, COSMIC 12, CPTAC 13 |
| 7 | ADMET → Top 15 | ✅ | current Top30 기준 28/30 PASS, 2 FAIL, Final Top15 갱신 완료 |
| 8 | Neo4j 적재 | ✅ | 30,563 노드, BRCA-Lung 공통 6개 |
| 9 | LLM 연동 (Ollama) | 📋 예정 | 무료, 로컬 실행. 향후 Bedrock 전환 |

---

## 2. 절대 규칙

```
1. curated_data/ → 읽기 전용. 수정/삭제 절대 금지.
2. curated_date/glue/ → 접근 자체 금지 (다른 팀원 영역).
3. 프로토콜(코드) = 팀4/팀장 원본 그대로 사용.
4. 데이터 = 해당 질병의 실제 데이터만 사용.
5. 팀4 가공 데이터(tmp_data/)를 실제 데이터로 혼동하지 않는다.
6. Proxy 데이터 사용 시 반드시 사용자 확인 요청.
7. 오류 발생 시 즉시 멈추고 보고. 자의적 해결 금지.
8. 불확실하면 모른다고 한다.
```

---

## 3. 전체 파이프라인 구조

```
Step 1. Raw 데이터 수집
Step 2. 데이터 전처리 (Raw → Parquet)
Step 3. Feature Engineering (Nextflow + AWS Batch)
    Step 3-1. prepare_fe_inputs
    Step 3-2. build_features
    Step 3-3. build_pair_features
    Step 3-4. upload_results
Step 3.5. Feature Selection → features_slim.parquet
Step 4. 모델 학습 (13개 모델 × 3입력셋 × 3평가방식)
Step 5. 앙상블 (Phase 3)
Step 6. Multi-objective Ranking + 외부 검증
Step 7. ADMET Gate
```

---

## 4. 질병별 데이터 비교표

### 4-1. Raw 데이터 현황

| 데이터 | BRCA | Lung | 비고 |
|--------|:----:|:----:|------|
| GDSC2 | ✅ | ✅ | 약물 감수성 (IC50) |
| DepMap CRISPR | ✅ | ✅ | 세포주 유전자 의존성 |
| LINCS L1000 | ✅ | ✅ | 약물 시그니처 |
| DrugBank | ✅ | ✅ | 약물 메타데이터 |
| ChEMBL | ✅ | ✅ | SMILES 매칭 |
| CPTAC | ❌ | ✅ | 외부 검증용 (Lung 추가) |
| ADMET | ✅ | ✅ | Step 7용 |

### 4-2. 전처리 결과 비교

| 항목 | BRCA | Lung | 비고 |
|------|:----:|:----:|------|
| 전체 cell line | 52 | 969 | GDSC2 기준 |
| 매칭 cell line | 52 (100%) | 578 (59.8%) | DepMap CRISPR과 매칭 |
| 미매칭 원인 | - | DepMap 데이터 부재 | 391개 미수행 |
| 약물 수 | 295 | 295 | 동일 |
| SMILES 커버리지 | 243/295 (82.4%) | 243/295 (82.4%) | 동일 |
| IC50 measurements | ~7,730 | 148,239 | Lung이 약 20배 |
| IC50 결측 | 0 | 0 | |
| 클래스 불균형 | 70.8:29.2 | 70.9:29.1 | 거의 동일 |

### 4-3. Cell Line 매칭 방법 (Lung 특이사항)

```python
# Name 정규화 규칙 (Lung에서 채택)
def normalize_name(name):
    return str(name).lower().replace('-', '').replace('/', '').replace(' ', '').replace('_', '')
```

| 방법 | 매칭률 | 채택 |
|------|:------:|:----:|
| 원본 (cell_line_name) | 50.5% | ❌ |
| Name 정규화 | 59.8% | ✅ |
| Sanger Model ID | 악화 | ❌ |

---

## 5. LINCS 처리 (질병별 세포주 교체)

### 5-1. 세포주 선택 기준

| | BRCA | Lung |
|--|------|------|
| 세포주 | MCF7 (단일) | 11개 폐암 세포주 |
| 선택 기준 | 유방암 대표 | primary_site = lung |
| 제외 | - | A549.311(서브클론), HCC515(normal) |

### 5-2. Lung 세포주 목록

| Cell ID | Subtype | Type | 분류 |
|---------|---------|:----:|:----:|
| A549 | NSCLC carcinoma | tumor | NSCLC |
| CORL23 | NSCLC large cell | tumor | NSCLC |
| DV90 | NSCLC adenocarcinoma | tumor | NSCLC |
| H1299 | Carcinoma | tumor | NSCLC |
| HCC15 | NSCLC squamous | tumor | NSCLC |
| NCIH1694 | **SCLC carcinoma** | tumor | **SCLC** |
| NCIH1836 | **SCLC carcinoma** | tumor | **SCLC** |
| NCIH2073 | NSCLC adenocarcinoma | tumor | NSCLC |
| NCIH596 | NSCLC adenosquamous | tumor | NSCLC |
| SKLU1 | NSCLC adenocarcinoma | tumor | NSCLC |
| T3M10 | NSCLC large cell | tumor | NSCLC |

> **⚠️ 주의:** LINCS 11개 세포주 중 SCLC 2개(NCIH1694, NCIH1836) 포함.
> LINCS는 전체 feature 중 5개(0.09%)만 차지하므로 모델 영향 미미.

### 5-2-1. GDSC2 Lung 세포주 NSCLC/SCLC 분포 (전체 학습 데이터)

> **⚠️ 중요:** GDSC2 기반 학습 데이터에 SCLC 세포주가 포함되어 있음.
> NSCLC와 SCLC는 기전이 다르므로 (NSCLC: EGFR/ALK/KRAS 드라이버, SCLC: RB1/TP53 드라이버),
> 결과 해석 시 이 점을 고려해야 함.

| 분류 | 세포주 수 | 비율 | Drug-Cell Pair |
|------|:---------:|:----:|:--------------:|
| NSCLC | 98 | 78.4% | ~대부분 |
| SCLC | 26 | 20.8% | 5,529 (3.92%) |
| Carcinoid | 1 | 0.8% | ~280 |
| **합계** | **125** | **100%** | **~148,239** |

**NSCLC 세부 분류:**

| 서브타입 | 세포주 수 |
|----------|:---------:|
| Lung Adenocarcinoma (LUAD) | 53 |
| Lung Squamous Cell Carcinoma (LUSC) | 21 |
| Large Cell Carcinoma | 10 |
| Non-Small Cell Lung Cancer NOS | 7 |
| Giant Cell / Adenosquamous / Mucoepidermoid | 7 |

**SCLC 세포주 26개:**
COR-L279, COR-L311, COR-L47, DMS 273, DMS 53, HCC-33, Lu-134-A, Lu-135, Lu-139, Lu-165, NCI-H1048, NCI-H1092, NCI-H1694, NCI-H1836, NCI-H209, NCI-H211, NCI-H2171, NCI-H2286, NCI-H446, NCI-H510, NCI-H526, NCI-H82, NCI-H841, SCLC-22H, SHP-77, SW 1271

**현재 결과 유효성:**
- Top 15 약물 중 FDA 승인 4개가 정확히 검출됨 → 결과 자체는 유효
- SCLC pair가 3.92%로 소수이나, 세포주 수 기준 20.8%는 무시 불가
- 현재 결과는 "All Lung Cancer" 버전으로 간주

### 5-2-2. 향후 NSCLC-only 재실험 방안

> 시간 확보 시 NSCLC-only 버전으로 재실험하여 비교 권장.

**재실험 절차:**

```
Step 1. 데이터 필터링
  - GDSC2에서 SCLC 26개 + Carcinoid 1개 세포주 제거
  - DepMap CRISPR에서 동일 세포주 제거
  - 필터링 후 예상: ~98 cell lines, ~120,000 pairs

Step 2. LINCS 재추출
  - 11개 → 9개 세포주 (NCIH1694, NCIH1836 제거)
  - lincs_lung_nsclc_drug_level.parquet 생성

Step 3. Nextflow FE 재실행
  - sample_features.parquet 재생성 (SCLC 제외)
  - labels.parquet 재생성 (SCLC pair 제외)
  - 나머지 파일은 동일

Step 4. Feature Selection → 모델 학습 → 앙상블 → 외부검증 → ADMET
  - 동일 프로토콜 적용

Step 5. All Lung vs NSCLC-only 비교
  - GroupCV Spearman 비교
  - Top 15 약물 overlap 분석
  - SCLC-specific 약물이 빠지는지 확인
```

**비교 포인트:**

| 비교 항목 | All Lung (현재) | NSCLC-only (예정) |
|----------|:--------------:|:-----------------:|
| 세포주 수 | 125 | ~98 |
| Pairs | ~148K | ~120K |
| LINCS 세포주 | 11 | 9 |
| GroupCV | 0.5030 | ? |
| Top 15 overlap | - | ? |

**재실험 시 FE 파일 재생성 가이드:**

| 파일 | 다시 만들어야? | 이유 |
|------|:------------:|------|
| sample_features.parquet | ✅ | SCLC 26개 세포주 행 제거 |
| labels.parquet | ✅ | SCLC pair ~5,529개 행 제거 |
| lincs_lung_drug_level.parquet | ✅ | SCLC 2개 세포주 제거 후 재집계 |
| drug_features.parquet | ❌ | 약물 정보라 세포주 무관 |
| drug_target_mapping.parquet | ❌ | 약물-타겟 매핑이라 무관 |

> 위 3개 파일 수정 후 Nextflow FE 재실행 필요.
> features.parquet, pair_features.parquet는 Nextflow가 자동 빌드.

**컬럼 수(feature) 변화 예상:**

| Feature 그룹 | 현재 (All Lung) | NSCLC-only 예상 | 변화 |
|-------------|:--------------:|:--------------:|------|
| Gene (CRISPR) | 18,435 | 18,435 | 동일 (유전자 목록 불변) |
| Morgan FP | 2,048 | 2,048 | 동일 (약물 구조 불변) |
| LINCS | 5 | 5 | 동일 (집계 방식 동일) |
| 기타 | 29 | 29 | 동일 |
| **FE 후 합계** | **~20,512** | **~20,512** | **거의 동일** |
| **Feature Selection 후** | **5,764** | **5,764 ± 200** | **약간 차이 가능** |

> 컬럼 수는 거의 동일. Feature Selection 단계에서 Low variance/High correlation 기준이
> 데이터 분포에 따라 소폭 달라질 수 있으나 큰 차이 없음 (±200 이내 예상).

**행 수(샘플) 변화:**

| 항목 | 현재 (All Lung) | NSCLC-only 예상 |
|------|:--------------:|:--------------:|
| 세포주 | 125 | ~98 (-27) |
| Drug-Cell Pairs | ~148,239 | ~120,000 |
| features_slim 후 | 125,427 | ~100,000 |

> 행 수만 줄어들고, 컬럼 구조는 동일하므로 학습 코드 수정 불필요.
> 데이터 경로만 변경하면 동일 파이프라인 적용 가능.

### 5-3. LINCS 추출 프로세스

```
1. cell_info.txt.gz → 폐암 세포주 식별 (primary_site 필터)
2. sig_info.txt.gz → trt_cp(compound treatment)만 필터링
3. gctx에서 시그니처 추출 (청크 단위, 5000개씩)
4. parquet 저장 (lincs_lung.parquet)
5. 약물 매칭 (3-stage: exact → aggressive norm → synonym)
6. 약물 단위 집계 (mean) → lincs_lung_drug_level.parquet
```

### 5-4. LINCS 시그니처 비교

| 항목 | BRCA (MCF7) | Lung (11 cells) |
|------|:-----------:|:---------------:|
| 전체 시그니처 | 63,367 | 50,468 |
| trt_cp 시그니처 | 29,312 | 25,265 |
| 유전자 수 | 12,328 | 12,328 |
| 파일 크기 | 7.6 GB | 1.8 GB |

### 5-5. 약물 매칭률 비교

| 매칭 방법 | BRCA | Lung |
|-----------|:----:|:----:|
| Simple match | 101 (34.2%) | 58 (19.7%) |
| Aggressive normalization | - | 92 (31.2%) |
| 최종 | 101 (34.2%) | 92 (31.2%) |

**Aggressive normalization 규칙:**
```python
# 하이픈, 특수문자, 공백 제거 후 비교
# 예: "SN-38" → "sn38" == "SN38"
# 예: "ABT-737" → "abt737" == "ABT737"
```

**미매칭 약물 처리:** build_pair_features에서 0.0 fill (제외하지 않음)

### 5-6. 대용량 처리 주의사항

| 항목 | 권장사항 |
|------|---------|
| gctx 압축 해제 | gunzip -k (원본 보존) |
| 메모리 부족 시 | 청크 단위 추출 (5,000개씩) |
| gc.collect() | 각 청크 후 실행 |
| 디스크 정리 | parquet 생성 확인 후 gctx/gz 삭제 |

---

## 6. Feature Engineering (Nextflow + AWS Batch)

### 6-1. FE 입력 파일

| 파일 | 용도 | BRCA | Lung |
|------|------|:----:|:----:|
| sample_features.parquet | DepMap CRISPR | 52 × 18,443 | 1,150 × 18,444 |
| labels.parquet | GDSC IC50 | ~7,730 × 4 | 148,239 × 4 |
| drug_features.parquet | Drug catalog + SMILES | 295 × 5 | 295 × 5 |
| lincs_*_drug_level.parquet | LINCS 약물 시그니처 | 101 × 12,329 | 92 × 12,329 |
| drug_target_mapping.parquet | 약물-타겟 매핑 | 485 × 2 | 485 × 2 (재사용) |

### 6-2. Nextflow config 수정사항 (질병별)

```groovy
// 질병별 변경 필요 항목
params {
    s3_base       = "s3://say2-4team/.../[질병명]"          // ← 변경
    run_id        = "YYYYMMDD_[질병]_fe_v1"                 // ← 변경
    lincs_drug_sig_uri = "${params.data_dir}/lincs_[질병]_drug_level.parquet"  // ← 변경
}

// 컬럼명 주의: drug_features.parquet의 SMILES 컬럼명
// canonical_smiles (build_features 요구) vs smiles (전처리 출력)
// → canonical_smiles로 통일 필요
```

### 6-3. AWS Batch 리소스 (재사용)

| 리소스 | 값 | 비고 |
|--------|-----|------|
| ECR | fe-v2-nextflow:v2-pip-awscli | 기존 이미지 재사용 |
| Compute Env | team4-fe-ce-cpu | ENABLED/VALID 확인 |
| Job Queue | team4-fe-queue-cpu | ENABLED/VALID 확인 |
| IAM | ecsTaskExecutionRole | 기존 재사용 |

### 6-4. 메모리 설정 (실험적 결과)

| Process | 초기 설정 | 최종 설정 | 비고 |
|---------|:---------:|:---------:|------|
| prepare_fe_inputs | 16 GB | 16 GB | |
| build_features | 16 GB | 128 GB | OOM 발생으로 증설 |
| build_pair_features | 32 GB | 128 GB | OOM 발생으로 증설 |
| upload_results | 4 GB | 4 GB | |

### 6-5. FE 결과 비교

| 항목 | BRCA | Lung | Colon |
|------|:----:|:----:|:-----:|
| drug-cell pairs | 6,366 | 125,427 | 9,692 |
| features.parquet 컬럼 | 18,316 | 18,439 | 17,925 |
| pair_features.parquet 컬럼 | 2,073 | 2,075 | 2,075 |
| LINCS feature 5개 | ✅ | ✅ | ✅ |
| 결측치 | 0 | 0 | 0 |
| 클래스 불균형 | 7:3 | 7:3 | 7:3 (2.33:1) |

### 6-6. FE QC 체크리스트

```
[ ] features.parquet shape 확인 (컬럼 ~18,000+)
[ ] labels.parquet binary_label 분포 확인
[ ] pair_features.parquet LINCS 5개 컬럼 존재 확인
[ ] 전 파일 행 수 일치 확인
[ ] 결측치 0 확인
[ ] 클래스 불균형 5:1 이하 확인
```

---

## 7. Feature Selection → features_slim.parquet

### 7-1. Selection 순서 (TCGA 기준, BRCA와 동일)

```
1단계: Low Variance 제거
   - TCGA 기준 variance 계산
   - 임계값 미만 제거

2단계: High Correlation 정리
   - Pearson > 0.95 쌍에서 하나 제거
   - 기준: 전체 평균 상관이 높은 쪽 제거

3단계 (선택): Importance 기반 하위 컷
   - 모델 학습 후 과적합 심하면 적용
   - biology signal 보존 주의
```

### 7-2. Selection 대상별 처리

| 구분 | 대상 | Selection 적용 |
|------|------|:--------------:|
| Gene (CRISPR) | ~18,435개 | ✅ Low var + High corr |
| Morgan FP | ~2,048개 | ✅ Low var + High corr |
| LINCS/Target/Pathway/Drug desc | ~25개 | ❌ 전부 유지 |

### 7-3. 질병별 Feature Selection 결과
| 항목 | BRCA | Lung | Colon |
|------|:----:|:----:|:-----:|
| 원본 features | ~20,383 | 20,514 | 19,998 |
| Gene 원본 → 선택 | ~18,310 → 4,415 | 18,435 → 4,703 | 17,919 → 4,564 |
| Morgan 원본 → 선택 | 2,048 → 1,094 | 2,048 → 1,032 | 2,048 → 1,067 |
| 기타 유지 | 25 | 29 | 29 |
| **최종 합계** | **5,534** | **5,766** | **5,662** |

**주요 관찰**:
- Lung/Colon은 동일 로직(low_variance 0.01 + high_correlation 0.95) 적용
- Colon gene high_correlation에서 73개 제거 (Lung은 0개) — 샘플 수 차이(35 vs 578)로 인한 자연스러운 현상
- FS 스크립트: `scripts/feature_selection.py` (독립 실행 가능, Lung 로직 100% 재현)

### 7-4. 산출물

```
features_slim.parquet          → 모델 학습 입력 (수정본)
features.parquet               → 원본 보존 (수정 금지)
pair_features.parquet          → 원본 보존 (수정 금지)
feature_selection_log.json     → 단계별 제거 수 기록
```

---

## 8. 모델 학습 (Phase 2)

### 8-1. 입력셋 3종

| 입력셋 | 구성 | 설명 |
|--------|------|------|
| Phase 2A | numeric-only | features_slim 수치 피처만 |
| Phase 2B | numeric + SMILES | 2A + SMILES (ML: TF-IDF+SVD 64d, DL: char token) |
| Phase 2C | numeric + context + SMILES | 2B + strong context 5개 컬럼 |

### 8-2. 모델 구성 (15개)

| 유형 | 모델 | 비고 |
|:----:|------|------|
| ML | LightGBM | |
| ML | LightGBM DART | |
| ML | XGBoost | |
| ML | CatBoost | |
| ML | RandomForest | |
| ML | ExtraTrees | |
| DL | FlatMLP | |
| DL | ResidualMLP | |
| DL | FTTransformer | |
| DL | CrossAttention | |
| DL | TabNet | |
| DL | WideDeep | |
| DL | TabTransformer | early stop 적용 |
| Graph | GraphSAGE | drug-split 필수 |
| Graph | GAT | drug-split 필수 |

> **주의:** GraphSAGE, GAT는 반드시 drug-based split 적용. Random split 사용 시 약물 정보 누출로 성능 과대평가.

### 8-3. 평가 방식 3종

| 방식 | 설명 | 목적 |
|------|------|------|
| Holdout | train:test = 8:2 | 빠른 확인 |
| 5-Fold CV | 일반 KFold | 안정적 평가 |
| GroupCV | canonical_drug_id 기준 3-fold | unseen drug 일반화 |

### 8-4. 평가 지표

```
예측 성능: Spearman, Pearson, R², RMSE, MAE, Kendall's Tau
과적합: Train-Val Gap, Fold std
```

### 8-5. BRCA 결과 참고

| 순위 | 모델 | 입력셋 | GroupCV Spearman |
|:----:|------|:------:|:----------------:|
| 1 | CatBoost | 2A | 0.8624 |
| 2 | LightGBM | 2A | 0.8575 |
| 3 | ResidualMLP | 2C | 0.5493 |

---

## 9. 앙상블 (Phase 3)

### 9-1. 앙상블 조합

| 조합 | 구성 | 비고 |
|------|------|------|
| FRC (프로토콜) | FlatMLP + ResidualMLP + CrossAttention | 프로토콜 기본 |
| DL Top3 | GroupCV 상위 DL 3개 | |
| ML Top3 | GroupCV 상위 ML 3개 | |
| ML+DL 혼합 | 전체 상위 3개 | BRCA 최고 성능 |

### 9-2. 앙상블 방식

| 방식 | 설명 |
|------|------|
| Simple Average | 단순 평균 |
| Weighted Average | GroupCV Spearman 비례 가중치 |

### 9-3. 총 실험 수

```
4조합 × 2방식 × 3입력셋 = 24개 앙상블 실험
```

### 9-4. 앙상블 평가 지표

```
Spearman, Ensemble Gain, Diversity, Error Overlap, Consensus Score
```

### 9-5. BRCA 앙상블 결과

| 순위 | 조합 | 입력셋 | 방식 | GroupCV Spearman | Gain |
|:----:|------|:------:|------|:----------------:|:----:|
| 1 | ML+DL 혼합 (RF+ResidualMLP+TabNet) | 2A | Weighted | **0.5521** | +0.0112 |
| 2 | ResidualMLP 단일 | 2C | - | 0.5493 | - |
| 3 | ML Top3 | 2A | Weighted | 0.5455 | +0.0045 |
| 4 | FRC | 2C | Simple | 0.5452 | 음수 |

### 9-6. Lung 앙상블 결과

| 순위 | 조합 | 입력셋 | 방식 | GroupCV Spearman | Gain |
|:----:|------|:------:|------|:----------------:|:----:|
| 1 | CatBoost 단일 | 2C | - | **0.5030** | - |
| 2 | ML+DL 혼합 (CatBoost+ResidualMLP+TabNet) | 2A | Weighted | 0.4797 | +0.0033 |
| 3 | ML+DL 혼합 | 2A | Simple | 0.4790 | +0.0025 |
| 4 | DL Top3 | 2C | Weighted | 0.4290 | +0.0013 |

**Lung 핵심 발견:**
- 양수 Gain: 4/24 (17%), 최대 +0.0033
- 음수 Gain: 20/24 (83%)
- CatBoost 단일이 대부분 앙상블보다 우수
- Error Overlap 높음 (0.6~0.8): 모델들이 비슷한 오류 발생

### 9-7. BRCA vs Lung 앙상블 비교

| 항목 | BRCA | Lung | 비교 |
|------|------|------|------|
| 최고 앙상블 | Mixed Weighted 2A (0.5521) | Mixed Weighted 2A (0.4797) | BRCA +0.072 |
| 최고 단일 | ResidualMLP 2C (0.5493) | CatBoost 2C (0.5030) | BRCA +0.046 |
| 앙상블 vs 단일 | 앙상블 승 (+0.003) | 단일 승 (+0.023) | 다른 패턴 |
| 최종 채택 | 앙상블 (0.5521) | 단일 (0.5030) | - |
| 양수 Gain 수 | 6/24 | 4/24 | BRCA 더 많음 |
| 모델 선호 | DL (ResidualMLP) | ML (CatBoost) | 질병별 다름 |
| 앙상블 최고 Phase | 2A | 2A | **동일** |
| 단일 최고 Phase | 2C | 2C | **동일** |
| 최고 앙상블 조합 | Mixed Weighted | Mixed Weighted | **동일** |
| 프로토콜 조합(FRC) Gain | 전부 음수 | 전부 음수 | **동일** |

### 9-8. 단일 모델 Top 5 비교 (GroupCV)

**Phase 2A:**

| 순위 | BRCA 모델 | BRCA Sp | Lung 모델 | Lung Sp |
|:----:|-----------|:-------:|-----------|:-------:|
| 1 | LightGBM | 0.5410 | CatBoost | 0.4765 |
| 2 | ResidualMLP | 0.5343 | ResidualMLP | 0.4531 |
| 3 | CatBoost | 0.5277 | TabTransformer | 0.4498 |
| 4 | TabTransformer | 0.5201 | LightGBM | 0.4490 |
| 5 | TabNet | 0.5189 | TabNet | 0.4369 |

**Phase 2C:**

| 순위 | BRCA 모델 | BRCA Sp | Lung 모델 | Lung Sp |
|:----:|-----------|:-------:|-----------|:-------:|
| 1 | ResidualMLP | 0.5493 | CatBoost | 0.5030 |
| 2 | TabTransformer | 0.5483 | ResidualMLP | 0.4277 |
| 3 | TabNet | 0.5449 | XGBoost | 0.4235 |
| 4 | CatBoost | 0.5277 | TabTransformer | 0.4186 |
| 5 | LightGBM | 0.5201 | LightGBM DART | 0.4142 |

### 9-9. 입력셋 효과 비교

**SMILES 추가 효과 (A→B, GroupCV):**

| | BRCA ML 평균 | BRCA DL 평균 | Lung ML 평균 | Lung DL 평균 |
|--|:---:|:---:|:---:|:---:|
| A→B 변화 | +0.006 | +0.012 | -0.005 | -0.017 |

**Context 추가 효과 (B→C, GroupCV):**

| | BRCA ML 평균 | BRCA DL 평균 | Lung ML 평균 | Lung DL 평균 |
|--|:---:|:---:|:---:|:---:|
| B→C 변화 | -0.003 | +0.008 | -0.035 | -0.015 |
| 예외 | - | - | CatBoost +0.021 | - |

---

## 10. 외부 검증 (Step 6)

### 10-1. 질병별 외부 검증 데이터

| | BRCA | Lung | 역할 |
|--|------|------|------|
| 주 검증 (환자 코호트) | METABRIC | CPTAC-LUAD/LUSC | 독립 환자 코호트, Survival 검증 |
| 변이 기반 검증 | - | COSMIC | 약물 타겟 ↔ 폐암 드라이버 유전자 일치 확인 |
| 약물 반응 검증 | - | PRISM | 대규모 세포주 약물 감수성 |
| 임상 근거 검증 | - | ClinicalTrials | 추천 약물의 폐암 임상시험 현황 |

### 10-2. BRCA vs Lung 검증 체계 비교

```
BRCA: 단일 검증
  └── METABRIC (Method A + B + C)

Lung: 다층 검증 (4개 소스)
  ├── CPTAC-LUAD/LUSC  → 독립 환자 코호트 (Survival, 발현, 단백질)
  ├── COSMIC           → 드라이버 유전자 기반 약물-질병 연관성
  ├── PRISM            → 세포주 약물 감수성 실측 (재창출 후보 커버리지)
  └── ClinicalTrials   → 임상시험 근거 (실제 임상 진행 여부)
```

### 10-3. COSMIC 활용 방법

```
1. 파이프라인 추천 약물의 타겟 유전자 추출
   (drug_target_mapping.parquet 참조)

2. COSMIC에서 해당 유전자의 폐암 변이 빈도 조회
   - LUAD/LUSC별 변이 빈도 (mutation frequency)
   - 드라이버 vs 패신저 분류

3. 검증 기준
   - 추천 약물 타겟이 COSMIC 폐암 드라이버 유전자와 일치 → 강한 근거
   - 변이 빈도 상위 20% 이내 → 임상적 유의성 높음
   - 일치하지 않음 → 약물 재창출 근거 약함 (단, 우회 경로 가능)

4. 소스 경로
   curated_data/validation/cosmic/
```

### 10-4. 각 검증 소스별 확인 항목

| 소스 | 확인 항목 | 판정 기준 |
|------|----------|----------|
| CPTAC | 타겟 유전자 발현 → 생존 연관성 | Survival p < 0.05 |
| COSMIC | 타겟 유전자 변이 빈도 | 폐암 드라이버 Top 20% |
| PRISM | 추천 약물 IC50 실측 | IC50 < median |
| ClinicalTrials | 폐암 임상시험 존재 여부 | Phase II 이상 |

### 10-5. 검증 방법 (BRCA 기준, Lung 확장 적용)

```
Method A: IC50 proxy 검증 (CPTAC 발현 기반)
Method B: Survival binary 검증 (CPTAC 생존 데이터)
Method C: P@K 검증
Method D: 드라이버 유전자 일치 검증 (COSMIC) ← Lung 신규
Method E: 세포주 약물 반응 검증 (PRISM) ← Lung 신규
```

### 10-6. Lung 외부 검증 결과

**검증 커버리지 (43개 약물 대상):**

| 소스 | 매칭 약물 | 커버리지 | 주요 지표 |
|------|:---------:|:--------:|----------|
| PRISM | 29/43 | 67.4% | Hit Rate@10 = 100% |
| ClinicalTrials | 21/43 | 48.8% | 1,561개 임상시험 |
| COSMIC | 22/43 | 51.2% | 2,104개 actionability records |
| CPTAC | 22/43 | 51.2% | 31/57 타겟 유전자 발현 확인 |

**신뢰도 분포:**

| 신뢰도 | 약물 수 | 의미 |
|:------:|:-------:|------|
| 100% | 7개 | 4개 소스 모두 검증 |
| 75% | 14개 | 3개 소스 검증 |
| 50% | 8개 | 2개 소스 검증 |
| 25% 이하 | 14개 | 1개 소스 이하 |

**100% 신뢰도 약물 (7개):**
- Topotecan (TOP1 inhibitor)
- Palbociclib (CDK4/6 inhibitor)
- Temsirolimus (mTOR inhibitor)
- Entinostat (HDAC inhibitor)
- Alisertib, Romidepsin, Cediranib

**Phase 2B vs 2C 비교:**

| 지표 | Phase 2B | Phase 2C |
|------|:--------:|:--------:|
| Top 30 Overlap | - | 17/30 (56.7%) |
| Precision@50 | 46.7% | 53.3% |
| Coverage Rate | 65.5% | 79.3% |
| 판정 | - | 2C가 임상적 타당성 높음 |

---

## 11. ADMET Gate (Step 7)

### 11-1. 필터링 3단계

```
Tier 1 Hard Fail → 즉시 탈락
- hERG > 0.7
- PAINS > 0
- Lipinski 위반 > 2

Tier 2 Soft Flag → 검토 후 판단
- hERG 0.5~0.7
- DILI, Ames, CYP3A4, PPB, Caco2

Tier 3 Context → 항암제 특성상 완화
- F(oral), t_half, Carcinogenicity
```

### 11-2. BRCA 최종 결과

```
Top 30 → Top 15 → ADMET 7개 PASS
Repurposing 1위: Ibrutinib (Safety 111.9)
```

### 11-3. Lung ADMET 결과

```
Top 43 (2B+2C 합집합) → 중복 제거 41개 → ADMET 40개 PASS (97.6%)
FAIL 1개: Epirubicin (Lipinski violations 3개)
```

### 11-4. Lung 최종 Top 15

| 순위 | 약물명 | 카테고리 | Score | 신뢰도 | 임상시험 수 |
|:----:|--------|----------|:-----:|:------:|:-----------:|
| 1 | Paclitaxel | FDA 승인 | 0.675 | 75% | 489 |
| 2 | Topotecan | FDA 승인 | 0.539 | 100% | 63 |
| 3 | Docetaxel | FDA 승인 | 0.498 | 75% | 423 |
| 4 | Vinorelbine | FDA 승인 | 0.376 | 75% | 65 |
| 5 | Palbociclib | 연구 단계 | 0.371 | 100% | 17 |
| 6 | Temsirolimus | 연구 단계 | 0.366 | 100% | 12 |
| 7 | Entinostat | 연구 단계 | 0.349 | 100% | 13 |
| 8 | Alisertib | 연구 단계 | 0.339 | 100% | 7 |
| 9 | Romidepsin | 연구 단계 | 0.336 | 100% | 3 |
| 10 | Cediranib | 연구 단계 | 0.326 | 100% | 3 |
| 11 | OTX015 | 연구 단계 | 0.298 | 75% | 2 |
| 12 | Rapamycin | 연구 단계 | 0.269 | 75% | 13 |
| 13 | LGK974 | 임상시험 | 0.310 | 75% | 1 |
| 14 | Dactinomycin | 재창출 후보 | 0.450 | 50% | 0 |
| 15 | SL0101 | 재창출 후보 | 0.342 | 25% | 0 |

### 11-5. Lung 카테고리별 분류

| 카테고리 | 약물 수 | 약물명 |
|----------|:-------:|--------|
| FDA 승인 폐암 치료제 | 4 | Paclitaxel, Topotecan, Docetaxel, Vinorelbine |
| 적응증 확장/연구 단계 | 8 | Palbociclib, Temsirolimus, Entinostat, Alisertib, Romidepsin, Cediranib, OTX015, Rapamycin |
| 임상시험 중 | 1 | LGK974 |
| 약물 재창출 후보 | 2 | Dactinomycin, SL0101 |

### 11-6. BRCA vs Lung ADMET 비교

| 항목 | BRCA | Lung |
|------|------|------|
| 대상 약물 | 30 | 41 (중복 제거 후) |
| ADMET PASS | 7 | 40 (97.6%) |
| FAIL | - | 1 (Epirubicin) |
| FDA 치료제 검출 | 5 | 4 |
| 연구 단계 | 6 | 8 |
| 재창출 후보 | 4 | 2 |
| 1위 재창출 후보 | Ibrutinib | Dactinomycin |

---

## 12. Neo4j Knowledge Graph 적재 (Step 8)

### 12-1. 기존 Neo4j 현황 (BRCA 구축 완료)

```
DB: Neo4j Aura Free (biso-kg)
노드: 30,461개 / 엣지: 137,368개

Drug        19,844   TESTED_IN       89,470
Target       8,880   INTERACTS_WITH  46,882
CellLine       969   IN_PATHWAY         729
Pathway        686   HAS_SIDE_EFFECT    109
SideEffect      46   TARGETS             41
Trial           35   IN_TRIAL            39
Disease          1   TREATS              13
Hospital        97
```

### 12-2. Lung 적재 내용

```
1. Disease 노드 추가
   - name: "Lung Cancer", code: "LUNG"

2. Top 15 약물 → Drug-TREATS-Disease("Lung Cancer") 엣지
   - 각 Drug에 속성 추가:
     lung_score, lung_confidence, lung_category

3. 외부 검증 결과 속성
   - prism_matched, clinical_trials_matched, cosmic_matched, cptac_matched
   - clinical_trials_count

4. BRCA-Lung 공통 약물 확인
   - 두 질병 모두에 TREATS 엣지가 있는 약물
```

### 12-3. 적재 경로

```
작업 디렉토리:
/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260409_scaleup_biso/

conda 환경: drug4-kg

입력 데이터:
/Users/skku_aws2_14/20260415_preproject_choi_protocol_v1_bisotest/
  20260415_preproject_choi_protocol_v1_bisotest/
    20260416_new_pre_project_biso_Lung/results/lung_final_top15.csv
```

### 12-4. 기존 로더 재사용

```
기존 BRCA 적재 스크립트:
neo4j/loaders/load_pipeline_results.py --disease LUNG

수정 필요:
- Disease 코드 LUNG 추가
- lung_final_top15.csv 경로 지정
- 검증 결과 속성 추가 (BRCA에는 없었던 PRISM/COSMIC/CPTAC 속성)
```

### 12-5. 향후 마이그레이션

```
현재: Neo4j Aura Free (200MB 제한)
조건: 전체 데이터 200MB 초과 시
이동: Neptune Serverless (openCypher 호환, 코드 거의 그대로)
```

---

## 12-A. LLM 연동 (Step 9)

> Neo4j 그래프 데이터를 LLM과 연결하여 자연어 질의 응답 구현.
> 현재는 로컬 LLM(Ollama)으로 구현. 다수 질병 파이프라인 완성 후 Bedrock 전환.

### 12-A-1. 아키텍처

```
사용자 질문
    ↓
FastAPI /api/chat (기존 엔드포인트)
    ↓
질문 분석 → Neo4j Cypher 쿼리 생성
    ↓
Neo4j 조회 (약물/질병/타겟/임상시험/부작용)
    ↓
조회 결과 + 원래 질문 → LLM (Ollama)
    ↓
근거 기반 답변 반환
```

### 12-A-2. LLM 단계별 전략

| 단계 | LLM | 시점 | 비용 | 비고 |
|:----:|-----|------|:----:|------|
| 현재 | Ollama (로컬) | 지금 | 무료 | Mac M4에서 실행 |
| 향후 | AWS Bedrock | 다수 질병 완성 후 | 유료 | 프롬프트만 이전 |

### 12-A-3. Ollama 설정

```
# 설치
brew install ollama

# 모델 다운로드 (추천: llama3.1 8B 또는 mistral 7B)
ollama pull llama3.1

# 실행
ollama serve
# 기본 포트: http://localhost:11434
```

### 12-A-4. 지원 질의 유형

| 질의 유형 | 예시 | Neo4j 쿼리 |
|----------|------|-----------|
| 약물 추천 | "폐암에 효과적인 약물 추천해줘" | Drug-TREATS-Disease("Lung Cancer") |
| 크로스 질병 | "유방암이랑 폐암 둘 다 쓰는 약물은?" | 공통 TREATS 엣지 조회 |
| 임상시험 | "Entinostat 임상시험 있어?" | Drug-IN_TRIAL 조회 |
| 약물 상세 | "Palbociclib 타겟이 뭐야?" | Drug-TARGETS-Target 조회 |
| 부작용 | "Paclitaxel 부작용 알려줘" | Drug-HAS_SIDE_EFFECT 조회 |
| 재창출 | "다른 암에서 재창출 가능한 약물은?" | category=REPURPOSING 필터 |
| 검증 근거 | "Topotecan 근거가 뭐야?" | 신뢰도 + 4개 검증 소스 조회 |

### 12-A-5. 프롬프트 템플릿

```
시스템 프롬프트:
당신은 약물 재창출 전문 어시스턴트입니다.
Neo4j Knowledge Graph에서 조회한 데이터를 기반으로 답변합니다.
근거 없는 추측은 하지 않습니다.
데이터에 없는 내용은 "해당 정보가 없습니다"라고 답합니다.

컨텍스트:
{neo4j_query_result}

사용자 질문:
{user_question}
```

### 12-A-6. 기존 FastAPI 연동

```
작업 디렉토리:
/Users/skku_aws2_14/20260408_pre_project_biso_myprotocol/20260409_scaleup_biso/

수정 파일:
- chat/api_server.py → /api/chat 엔드포인트에 Ollama 연결
- llm/ollama_client.py → Ollama API 호출 모듈 (신규)
- llm/neo4j_to_prompt.py → Neo4j 조회 결과 → 프롬프트 변환 (신규)

기존 엔드포인트 12개는 수정 불필요.
/api/chat만 LLM 백엔드 교체.
```

### 12-A-7. Bedrock 전환 조건

```
전환 시점:
- 3개 이상 질병 파이프라인 완성 후
- 로컬 Ollama 검증 완료 후
- 예산 확보 후

전환 작업:
- llm/ollama_client.py → llm/bedrock_client.py 교체
- 프롬프트 템플릿 동일하게 사용
- Neo4j → Neptune 마이그레이션과 동시 진행 가능
```

---

## 13. 32개 지표 체크리스트

### 12-1. 현재 완료 상황

**예측 성능 (8/8) ✅**

| 지표 | 상태 | Lung 최고값 (CatBoost 2C) |
|------|:----:|:------------------------:|
| Spearman | ✅ | 0.5030 |
| Pearson | ✅ | 확인 완료 |
| R² | ✅ | 확인 완료 |
| RMSE | ✅ | 확인 완료 |
| MAE | ✅ | 확인 완료 |
| Kendall's Tau | ✅ | 확인 완료 |
| MedianAE | ✅ | OOF에서 계산 |
| P95 Error | ✅ | OOF에서 계산 |

**과적합 (5/5) ✅**

| 지표 | 상태 | 비고 |
|------|:----:|------|
| Train Spearman | ✅ | 전 모델 기록 |
| Val Spearman | ✅ | 전 모델 기록 |
| Gap | ✅ | 모든 모델 > 0.15 (GroupCV 특성) |
| Train/Val Ratio | ✅ | 계산 완료 |
| Fold std | ✅ | 대부분 0.01~0.08 |

**앙상블 (4/4) ✅**

| 지표 | 상태 | 비고 |
|------|:----:|------|
| Ensemble Gain | ✅ | 양수 4/24 |
| Diversity | ✅ | 0.76~0.91 |
| Error Overlap | ✅ | 0.6~0.8 |
| Consensus Score | ✅ | 확인 완료 |

**일반화 (2/6) 🔄**

| 지표 | 상태 | 비고 |
|------|:----:|------|
| Holdout | ✅ | 전 모델 완료 |
| GroupCV (unseen drug) | ✅ | 전 모델 완료 |
| 5-Fold CV | ✅ | 전 모델 완료 |
| Scaffold split | ❌ | 미진행 |
| Multi-seed stability | ❌ | 미진행 |
| Cross-dataset | ❌ | 미진행 |

**약물 랭킹 (6/9) 🔄**

| 지표 | 상태 | 비고 |
|------|:----:|------|
| Hit Rate@K | ✅ | PRISM Hit Rate@10 = 100% |
| Precision@K | ✅ | Precision@50 = 53.3% |
| Recall@K | ✅ | PRISM Recall 확인 |
| Coverage Rate | ✅ | 79.3% |
| MRR | ✅ | 확인 완료 |
| NDCG@K | ✅ | 확인 완료 |
| MAP | ❌ | 미계산 |
| AUC-ROC | ❌ | 미계산 |
| Consensus Overlap | ❌ | 2B vs 2C 56.7% (부분 확인) |

### 12-2. 종합 진행률

```
완료: 28/32 (87.5%)
미완료: 4/32 (12.5%) — scaffold split, multi-seed, cross-dataset, MAP
```

---

## 12. 경로 정보 템플릿

### 로컬

```
/Users/[user]/[project_root]/
└── [date]_new_pre_project_biso_[Disease]/
    ├── curated_data/          ← Raw 데이터 (읽기 전용)
    │   ├── gdsc/
    │   ├── depmap/
    │   ├── lincs/
    │   ├── drugbank/
    │   ├── chembl/
    │   ├── cptac/             ← 외부 검증용
    │   ├── admet/             ← Step 7용
    │   ├── validation/        ← 외부 검증용
    │   └── processed/         ← 전처리 결과
    ├── data/                  ← FE 입력/S3 업로드 대상
    ├── scripts/
    ├── logs/
    └── reports/
```

### S3

```
s3://say2-4team/[base_path]/[date]_new_pre_project_biso_[Disease]/
├── data/                    ← FE 입력 파일
├── fe_output/               ← FE 결과
│   └── [run_id]/
│       ├── features/
│       ├── pair_features/
│       └── reports/
└── work/                    ← Nextflow 작업 디렉토리
```

### 참조 스크립트 (코드만 참조, 데이터 사용 금지)

```
/Users/[user]/[brca_protocol_path]/nextflow/scripts/
├── build_drug_catalog.py
├── prepare_fe_inputs.py
├── build_features_v8_20260406.py
└── build_pair_features_newfe_v2.py
```

---

## 13. 새 질병 추가 시 체크리스트

```
[ ] Raw 데이터 수집 (GDSC, DepMap, LINCS, DrugBank, ChEMBL)
[ ] 외부 검증 데이터 수집 (METABRIC 대체)
[ ] Cell line 매칭 방법 결정 (정규화 규칙)
[ ] LINCS 세포주 선택 (해당 질병 세포주 목록)
[ ] LINCS gctx → parquet 추출
[ ] 약물 매칭 (3-stage)
[ ] 약물 단위 집계 (mean)
[ ] Drug catalog 생성 (SMILES 매칭)
[ ] FE 입력 파일 준비 (4~5개)
[ ] S3 업로드
[ ] Nextflow config 수정 (경로, run_id, LINCS 파일명)
[ ] Nextflow AWS Batch 실행
[ ] FE QC
[ ] Feature Selection → features_slim.parquet
[ ] choi_protocol 경로/컬럼 매핑 수정
[ ] 모델 학습 (13개 × 3입력셋 × 3평가)
[ ] 앙상블 (24개 실험)
[ ] 외부 검증
[ ] ADMET Gate
[ ] 질병간 비교 분석 (앙상블 최적 조합 비교)
```

---

## 14. 기반 프로토콜 및 레퍼런스

### 14-1. 내부 프로토콜 계보

| 문서 | 날짜 | 내용 | 관계 |
|------|------|------|------|
| Team4_Experiment_Protocol_v2_3 | 2026-03 | 팀4 원본 실험 프로토콜 | 최초 기반 |
| protocol_guide_v1 (biso) | 2026-04-08 | 팀4 기반 재현 가이드, 15개 모델, FE+학습+ADMET | v1 |
| protocol_guide_v2 | 2026-04-10 | 7-Hurdle System 추가, MultiModalFusionNet | v2 |
| protocol_guide_v3 | 2026-04-14 | 15개 모델 재학습, Feature Selection(20,389→5,534), 6단계 확장 평가 | v3 |
| protocol_guide_v3.1 | 2026-04-14 | Multi-objective scoring, 치료제 분리, ADMET Tanimoto v1, CatBoost 단독 채택 | v3.1 |
| PROTOCOL_CHOI_통합실행가이드 | 2026-04-15 | 팀장 프로토콜 기반 학습 파이프라인, 3입력셋(2A/2B/2C), 13모델×3평가, 앙상블 Phase 3 | choi_protocol |
| lung_preprocessing_protocol | 2026-04-16 | 폐암 전처리 프로토콜, LINCS 11세포주, Cell line 정규화 | Lung 전처리 |
| **본 문서** | **2026-04-17** | **적응증 확장 재현 가이드, BRCA→Lung 비교, 재현 체크리스트** | **통합** |

### 14-2. 핵심 참조 관계

```
Team4_Experiment_Protocol_v2_3 (팀4 원본)
    ↓
protocol_guide_v1~v3.1 (BRCA 파이프라인 진화)
    ↓
PROTOCOL_CHOI_통합실행가이드 (팀장 프로토콜 + 커스터마이징)
    ↓
본 문서 (적응증 확장 재현 가이드)
```

### 14-3. GitHub 저장소

| 저장소 | 용도 |
|--------|------|
| skkuaws0215/20260408_pre_project_biso_myprotocol | BRCA 파이프라인 (v1~v3.1), 대시보드 |
| skkuaws0215/20260415_preproject_choi_protocol_v1_bisotest | choi_protocol 학습 파이프라인, Lung 확장 |

### 14-4. BRCA 앙상블 선정 과정 (v3 → v3.1)

```
15개 모델 학습
    ↓
앙상블 통과 12개 (Sp≥0.713 AND RMSE≤1.385)
    ↓
앙상블 B: 4개 (CatBoost + DART + FlatMLP + CrossAttn)
    ↓
앙상블 A: 3개 (CatBoost + DART + FlatMLP, CrossAttn 중복 제거)
    ↓
CatBoost 단독과 비교 → METABRIC Top 15 overlap 80%, Sp 0.994
    ↓
CatBoost 단독 채택 (v3.1)
```

### 14-5. choi_protocol 앙상블 결과 (Phase 3)

```
24개 앙상블 실험 (4조합 × 2방식 × 3입력셋)
    ↓
프로토콜 조합 Gain: 전부 음수
커스텀 조합 Gain: 6개 양수
    ↓
최고: ML+DL 혼합 (RF+ResidualMLP+TabNet) 2A Weighted → Sp 0.5521
단일 최고: ResidualMLP 2C → Sp 0.5493
    ↓
최종: 앙상블 + 단일 교차 검증 방식 채택
```

### 14-6. S3 데이터 경로

| 경로 | 용도 | 접근 |
|------|------|:----:|
| s3://say2-4team/curated_date/ | 전처리 완료 원본 데이터 | 읽기 전용 |
| s3://say2-4team/curated_date/glue/ | 다른 팀원 영역 | 접근 금지 |
| s3://say2-4team/Lung_raw/ | 폐암 Raw 데이터 (35.5GB) | 읽기 전용 |
| s3://say2-4team/20260408_new_pre_project_biso/.../BRCA/ | BRCA 업무폴더 | 읽기/쓰기 |
| s3://say2-4team/20260408_new_pre_project_biso/.../Lung/ | Lung 업무폴더 | 읽기/쓰기 |

---

## 15. 범용 모델 선택 전략

> BRCA + Lung 2개 질병 실험 결과에서 도출된 전략.
> 대장암, IPF, RA 등 추가 질병에서 검증 후 확정.

### 15-1. 확인된 공통 패턴

```
2개 질병(BRCA, Lung) 모두에서 동일한 패턴:

1. 앙상블 최고 Phase = 2A (numeric-only)
2. 단일 모델 최고 Phase = 2C (+Context+SMILES)
3. 앙상블 최고 조합 = Mixed Weighted (ML+DL 혼합)
4. 프로토콜 기본 조합(FRC) = 항상 실패 (Gain 음수)
5. SMILES/Context = DL 일부에만 효과, 앙상블에서는 diversity 감소
```

### 15-2. 질병별 다른 패턴

| 항목 | BRCA | Lung | 의미 |
|------|------|------|------|
| 최종 채택 | 앙상블 | 단일 | 데이터 특성에 따라 다름 |
| 선호 모델 유형 | DL (ResidualMLP) | ML (CatBoost) | 질병별 최적 모델 다름 |
| 앙상블 Gain | +0.003 (미세 양수) | -0.023 (음수) | 앙상블 효과 질병별 차이 |
| Context 효과 | DL에서 소폭 양수 | CatBoost에만 양수 | 활용 방식 다름 |

### 15-3. 범용 파이프라인 전략

```
새 질병 투입
    ↓
Phase 2A 학습 (필수) — numeric-only
Phase 2C 학습 (필수) — +Context+SMILES  
Phase 2B (선택) — 시간 여유 있으면
    ↓
메인: Mixed Weighted 앙상블 (2A)
  → CatBoost(Boosting) + ResidualMLP(Residual) + TabNet(Attention)
  → 서로 다른 특성의 모델로 diversity 확보
    ↓
서브: 단일 모델 최고 (2C)
  → CatBoost 또는 ResidualMLP (질병별 자동 선택)
    ↓
GroupCV 비교
  → 앙상블 Gain 양수 → 앙상블 채택 (BRCA 패턴)
  → 앙상블 Gain 음수 → 단일 채택 (Lung 패턴)
```

### 15-4. 검증 현황

| 질병 | 메인 (앙상블 2A) | 서브 (단일 2C) | 채택 | 검증 |
|------|:----------------:|:--------------:|:----:|:----:|
| BRCA | 0.5521 | 0.5493 | 앙상블 | ✅ |
| Lung | 0.4797 | 0.5030 | 단일 | ✅ |
| 대장암 | - | - | - | 예정 |
| IPF | - | - | - | 예정 |
| RA | - | - | - | 예정 |

### 15-5. 시간 최적화

```
기존: Phase 2A + 2B + 2C 전부 (3배 시간)
최적화: Phase 2A + 2C만 필수 (2배 시간)
  → 2B는 2A→2C 사이의 중간값이라 생략 가능
  → 2A/2C 결과로 SMILES/Context 효과 판단 충분

추가 최적화:
  → 15개 모델 중 Graph 2개 스킵 가능 (시간 대비 효과 낮음)
  → ExtraTrees GroupCV 스킵 가능 (Holdout으로 경향 확인)
  → 실질 필수: ML 5개 + DL 7개 = 12개 모델 × 2 Phase = 24 실험
```

---

## 16. 향후 확장: 멀티모달 브랜치 전략 (예정)

> 이 섹션은 향후 이미지/Graph 모달리티 추가 시 참고용으로 기재.
> 현재는 미구현. 타질병 baseline 완료 후 진행.

### 16-1. 브랜치 구조

```
Branch A (기존, 현재 완료):
  numeric features → ML/DL → 앙상블 A

Branch B (신규, 예정):
  이미지 데이터 → CNN/ViT → 앙상블 B

Branch C (신규, 예정):
  분자 그래프 (SMILES → GNN) → 앙상블 C

최종 통합:
  멀티모달 앙상블 (A + B + C) → 약물 랭킹
```

### 16-2. 질병별 이미지 데이터 가용성

| 질병 | 이미지 데이터 | 소스 | Branch B 적용 |
|------|:------------:|------|:------------:|
| BRCA | ❌ | - | 불가 |
| Lung | ✅ | CT, H&E 병리, CPTAC | 가능 |
| 대장암 | ✅ | 병리 슬라이드 | 가능 |
| IPF | ✅ | CT (폐 섬유화) | 가능 |
| RA | ✅ | X-ray, MRI | 가능 |

### 16-3. 브랜치 전략 장점

```
1. 기존 파이프라인 수정 없이 독립 개발/테스트
2. Branch A가 baseline → 이미지 추가 효과 정확히 측정
3. 이미지 모델 실패해도 기존 결과 영향 없음
4. 이미지 데이터 없는 질병(BRCA)은 Branch A만 사용
```

### 16-4. 진행 순서 (예정)

```
Step 1. 타질병 현재 프로토콜 baseline 완료 (Branch A)  ← 현재 진행 중
Step 2. 이미지 데이터 수집 및 전처리 (Branch B 준비)
Step 3. 이미지 모델 학습 (CNN, ViT 등)
Step 4. 멀티모달 앙상블 (A + B) 성능 비교
Step 5. 분자 그래프 GNN 추가 (Branch C) — 선택
```

---

## 17. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|:----:|----------|
| 2026-04-17 | v1.0 | 초안 작성 (BRCA 완료, Lung FE 완료 기준) |
| 2026-04-19 | v1.1 | Phase 2+3 완료. Lung 앙상블 결과, BRCA vs Lung 비교표, 범용 모델 선택 전략 추가 |
| 2026-04-19 | v1.2 | 향후 멀티모달 브랜치 전략 추가 (예정 사항 기재) |
| 2026-04-20 | v2.0 | Step 6 외부검증 결과(PRISM/COSMIC/CPTAC/ClinicalTrials), Step 7 ADMET 결과, 최종 Top 15 선정, 32개 지표 체크리스트 추가 |
| 2026-04-20 | v2.1 | Step 8 Neo4j Knowledge Graph 적재 섹션 추가 |
| 2026-04-20 | v2.2 | SCLC 세포주 포함 현황 기재, NSCLC-only 재실험 방안 추가 |
| 2026-04-20 | v2.3 | Step 9 LLM 연동 섹션 추가 (Ollama 로컬 → 향후 Bedrock 전환) |
