# PDAC 파이프라인 종합 결과 보고서 (2026-04-28)

기준 태그: `20260427_pdac_step4_v1_no_holdout`

## 1) 모델학습 및 대표 앙상블

| 항목 | 값 |
|---|---|
| Step4 실행 | 완료 |
| 대표 산출물 | `results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv` |
| Top30 행수 | 30 |

Top30 VT 분포:
- VT1: 4
- VT2: 9
- VT3: 16
- VT4: 1

## 2) 대표 앙상블 기반 Top30

파일: `results/20260427_pdac_step4_v1_no_holdout/top30_pdac_with_vt.csv`

## 3) Step6 외부검증 (방법 + 결과)

방법:
- 독립 어댑터 기반 외부검증
- 소스: PRISM / ClinicalTrials / OpenTargets / COSMIC / GEO / CPTAC

결과:
- Top30 처리: 30
- PRISM evidence: 24
- ClinicalTrials support: 19
- OpenTargets support: 13
- COSMIC support: 2
- GEO/CPTAC: `PENDING_DATA`

## 4) Step7 ADMET (방법 + Top15)

방법:
- 22 assay 완전 계산형 재평가
- Top30 전행 평가 후 Top15 선별

요약:
- assay_count: 22
- candidate_count: 30
- resolved_smiles_count: 30
- 분류: Candidate=8, Caution=22

Top15 파일:
- `results/20260427_pdac_step4_v1_no_holdout/step7_top15_pdac_admet_with_vt.csv`

Top15 VT 분포:
- VT1: 4
- VT2: 6
- VT3: 5
