# Conditional To PASS Changelog 20260513

- updated_at: 2026-05-13 09:45:15 KST
- previous_verdict: CONDITIONAL PASS
- updated_verdict: PASS (IM4a clinical data pending handled separately)

## 수정 1: seed/random_state 고정

변경 파일:
- `/Users/skku_aws2_14/pipeline/run_disease_pipeline.py`
- `/Users/skku_aws2_14/pipeline/steps/step2_basic_pipeline.py`
- `/Users/skku_aws2_14/pipeline/utils/embedding_utils.py`
- `/Users/skku_aws2_14/pipeline/configs/auto_ov.yaml`

내용:
- top-level `random_seed: 42` 추가.
- 파이프라인 진입점에서 `set_global_random_seed(config)` 호출.
- `random`, `numpy`, `torch`, CUDA/CUDNN deterministic 설정 추가.
- Step2 모델 학습/CV seed를 config `random_seed`로 전달.
- IM2 embedding merge 정렬을 deterministic sort/groupby로 고정.

검증:
- seed/k 검증 파일: `ov_seed_and_k_search_verification_20260513.json`
- 기존 best_k=4, 전체 k=2..8 재탐색 후 best_k=2. 동일하지 않음. 원인은 seed 변화가 아니라 k=2가 새 탐색 범위에 포함되며 silhouette가 더 높았기 때문.

## 수정 2: IM3 k=2~8 전체 silhouette 탐색

변경 파일:
- `/Users/skku_aws2_14/pipeline/steps/im3_clustering.py`

신규 산출물:
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/image_modal/step_im3/im3_k_search_results.csv`
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/image_modal/step_im3/im3_k_search_summary.md`
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/image_modal/step_im3/im3_best_k_comparison_20260513.csv`

결과:
- best_k: 4 -> 2
- best_silhouette: k=2 = 0.191136
- cluster sizes: [38, 12]
- best_k 변경으로 IM4c와 IM5를 새 k=2 기준으로 재실행함.

## 수정 3: IM4c confidence_score 추가

변경 파일:
- `/Users/skku_aws2_14/pipeline/steps/im4c_cluster_drug.py`

신규 산출물:
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/image_modal/step_im4/im4c_cluster_drug_links_scored.csv`
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/image_modal/step_im4/im4c_confidence_summary.md`
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/validation/ov_im_cluster_drug_links_full.csv`

결과:
- 새 cluster 수: 2
- scored links: 30
- confidence grades: {'C': 30}
- cluster-specific DEG/marker 파일이 없어 `analysis.driver_genes` fallback을 사용함. 따라서 모든 link가 C 등급이며, scientific confidence는 낮게 해석해야 함.

## 수정 4: OV 약물 prior 재검토

변경 파일:
- `/Users/skku_aws2_14/pipeline/configs/auto_ov.yaml`

신규 산출물:
- `/Users/skku_aws2_14/pipeline/OV_pipeline/outputs/validation/ov_prior_review_20260513.md`

결과:
- driver_genes: `TP53, BRCA1, BRCA2, NF1, RB1, CDK12`
- tier1_drugs: `Carboplatin, Paclitaxel, Olaparib, Niraparib, Bevacizumab, Cisplatin, Doxorubicin`
- tier4_exclude: empty
- subtypes: `HGSOC, LGSOC, Endometrioid, Clear cell, Mucinous`
- tcga_project: `TCGA-OV` 유지
- foundation_model: `UNI2` 유지

## 남은 항목

- IM4a clinical은 사용자가 지정한 대로 데이터 확보 문제라 별도 처리.
