# IPF Drug Repurposing Pipeline Protocol
Date: 2026-05-04
Version: v1.0 (2A Boosting 3-Ensemble, External Validation Clean)

## Overview
- 질환: Idiopathic Pulmonary Fibrosis (IPF)
- 목적: AI 기반 약물 재창출 - 최종 15개 후보 약물 도출
- 모델: LightGBM + XGBoost + CatBoost (groupcv Spearman 가중 앙상블)
- y: ln(IC50) (낮을수록 potent)
- 타겟: 13개 IPF 관련 타겟 (JAK1, TGFBR1, PDGFRA, PDGFRB, FGFR2, KDR 등)

## 데이터
- 학습 코호트: GSE92592 (RNA-seq), GSE47460 (Microarray), GSE32537 (Microarray)
- 외부검증 코호트: GSE110147 (27명), GSE150910 (103명)
- 약물 데이터: ChEMBL 34, 13개 타겟 IC50, 32,134 약물

## Step별 요약

### Step 1: GEO 전처리 + 정규화
- 학습 3코호트만으로 공통 유전자 union -> high-variance top5000
- StandardScaler fit: 학습만, EV는 transform only
- 한계: raw가 아닌 기존 normalized parquet 사용, ComBat 미적용

### Step 2: 질병 시그니처
- DEG: 학습 코호트 IPF vs Control Welch t-test, FDR<0.05
- Signature: up 66 + down 66 = 132 genes
- Pathway: 고정 IPF pathway gene set 기반 z-score (8d)

### Step 3: 약물 피처 (기존 재사용)
- IC50: 45,048 rows, 32,134 drugs, 13 targets
- Drug feature: 2A (22d), 2B (1046d)
- 환자 데이터 무관 -> leakage 없음

### Step 4: 피처 엔지니어링
- x_patient: signature 132d + pathway 8d + PCA 200d = 340d
- PCA/scaler: 학습 코호트만으로 fit, EV는 transform only
- fit params 저장

### Step 5: 모델 학습
- LightGBM / XGBoost / CatBoost
- 평가: cv5, groupcv, scaffoldcv
- 앙상블 가중치: groupcv Spearman 비례

### Step 6: 외부검증
- 방법: Step1부터 학습/EV 완전 분리 재실행 (Clean EV)
- 2A EV Spearman: 0.9365 (GSE110147, GSE150910 동일)
- 2B EV Spearman: 0.9455
- EV Top30 overlap (GSE110147 vs GSE150910): Jaccard 1.000
- Train Top30 vs EV Top30: Jaccard 0.36
- 한계: PCA/정규화 입력이 기존 normalized parquet 기반

### Step 6 Top30 재구성
- Model Top20: JAK1 전임상 화합물 (Tier 4)
- 2단계 보강 10개:
  - Tier 1: Nintedanib (IPF 승인)
  - Tier 2: Ponatinib, AT-9283, Ruxolitinib, Tofacitinib, Pazopanib, Sunitinib, Sorafenib
  - Tier 4: TGFBR1 lead, PDGFRA lead
- Nintedanib model rank: 8350 (train), 8920 (EV)

### Step 7: ADMET
- 22 assay RF 기반 QSAR 예측 (실험값 아님)
- IPF 기준: 만성 경구투여 -> 항암제보다 엄격
- Hard Fail: hERG, Ames, Ro5 위반 >=2, PAINS
- Clinical_Context_Hard_Fail: Nintedanib, Ponatinib, Sunitinib (승인약이므로 유지)
- 최종 15개 도출

## 최종 15개 약물

| Rank | Drug | ChEMBL ID | Target | Tier | ADMET | max_phase |
|---:|---|---|---|---|---|---|
| 1 | Nintedanib | CHEMBL502835 | PDGFRB | Tier1 | Clinical_Context | 4 (IPF 승인) |
| 2 | AT-9283 | CHEMBL495727 | FGFR2 | Tier2 | Pass_With_Flags | 2 |
| 3 | Ruxolitinib | CHEMBL1789941 | JAK1 | Tier2 | Pass_With_Flags | 4 (MF/PV) |
| 4 | Tofacitinib | CHEMBL221959 | JAK1 | Tier2 | Pass_With_Flags | 4 (RA) |
| 5 | Pazopanib | CHEMBL477772 | KDR | Tier2 | Pass_With_Flags | 4 (RCC) |
| 6 | Sorafenib | CHEMBL1336 | KDR | Tier2 | Pass_With_Flags | 4 (HCC) |
| 7 | Ponatinib | CHEMBL1171837 | PDGFRB | Tier2 | Clinical_Context | 4 (CML) |
| 8 | Sunitinib | CHEMBL535 | PDGFRB | Tier2 | Clinical_Context | 4 (RCC) |
| 9-15 | JAK1 preclinical leads | various | JAK1 | Tier4 | Pass_With_Flags | null |

## IPF Reference 약물 (파이프라인에 없음)

| Drug | 이유 |
|---|---|
| Pirfenidone | 해당 타겟이 13개에 미포함 |
| Nerandomilast | PDE4B, 타겟 미포함 |
| Admilparant | LPA1, IC50 데이터 없음 |
| Galunisertib | TGFBR1 IC50 데이터 없음 |
| Vactosertib | TGFBR1 IC50 데이터 없음 |
| Baricitinib | IC50 데이터 없음 |

## 향후 계획
1. 이미지 모달: OSIC Kaggle (176명) -> CT-CLIP -> 환자 clustering -> 약물 stratification
2. CT-RATE 스케일업 가능
3. y 개선: multi-objective score (clinical maturity + pathway relevance + target activity)
4. PAH 파이프라인 확장

## 한계
1. Step1 입력이 raw가 아닌 기존 normalized parquet
2. ComBat 배치 보정 미적용
3. 모델 Top20이 JAK1 전임상 화합물로 편중
4. ADMET은 QSAR 예측값 (실험 검증 아님)
5. GEO 환자와 HRCT 이미지 환자가 동일인이 아님
