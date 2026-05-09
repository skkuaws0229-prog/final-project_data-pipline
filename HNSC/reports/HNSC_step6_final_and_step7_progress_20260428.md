# HNSC Step6 Final + Step7 Progress (2026-04-28)

## 1) Step6 외부검증 최종 상태

- 실행 래퍼: `scripts/run_step6_hnsc.sh`
- 독립 어댑터: `scripts/step6_ext_comprehensive_hnsc_independent.py`
- 입력: `results/20260427_hnsc_step4_v1/stad_top30_drugs_ensemble_hnsc_directive_validation_tiers.csv`

최종 집계:
- Top30 중 1개 이상 외부근거 매칭: **28/30**
- 미매칭: **2개** (`Pyridostatin`, `Schweinfurthin A`)
- 소스별 지원(최종):
  - PRISM(any): 21
  - ClinicalTrials: 17
  - Patient context(TCGA/CPTAC): 14
  - OpenTargets: 14
  - COSMIC: 3
  - GEO(drug-level): 0 (`DATASET_ONLY`)

보완 수행:
- COSMIC bundle 다운로드: `Stad_raw/additional_sources/cosmic_stad/20260421`
- OpenTargets parquet 로컬 반영: `base_data/.../data/source_staging/opentargets/`
- PRISM/ClinicalTrials raw fallback 적용 후 재매칭
  - `Dactinomycin` 매칭 복구

---

## 2) Step7 진행 결과 (1차)

- 산출 파일: `results/20260427_hnsc_step4_v1/step7_top15_hnsc_provisional.csv`
- 실행 래퍼: `scripts/run_step7_hnsc.sh` (`scripts/step7_finalize_hnsc.py`)
- 운영 원칙:
  - 외부근거 매칭 + VT를 함께 고려
  - VT4 및 미매칭 물질은 `REVIEW`로 분리

Step7 확장판 산출:
- `results/20260427_hnsc_step4_v1/step7_top30_hnsc_extended.csv` (Top30 전체)
- `results/20260427_hnsc_step4_v1/step7_top15_hnsc_extended.csv` (Top15)

현재 Top15에서 `REVIEW`:
- `Camptothecin` (VT4)
- `Pyridostatin` (미매칭, VT4)
- `Schweinfurthin A` (미매칭, VT4)

---

## 3) 다음 실행 포인트

1. Step7 확정판에서 `REVIEW` 3개 유지/대체 결정
2. 확정 Top15 기준 Step8/9(KG/설명)로 이관

