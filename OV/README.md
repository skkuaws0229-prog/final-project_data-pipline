# OV 난소암 결과 패키지

이 폴더는 OV(난소암) 기본 파이프라인과 이미지 모달 자동화 검증 결과를 GitHub에 올릴 수 있는 경량 형태로 정리한 것이다.

원본 WSI `.svs`, tile embedding `.h5`, merged embedding `.npy`, parquet shard, 모델 바이너리처럼 용량이 큰 파일은 포함하지 않는다. 대용량 원본과 중간 산출물은 S3 기준 위치에서 확인한다.

## 폴더 구성

| 폴더 | 내용 |
| --- | --- |
| `0.Image_modal_OV/` | OV 이미지 모달 후단 결과, IM3 k 탐색, cluster-drug link, IM5 summary |
| `1.Drug_results/` | 기본 파이프라인 최종 약물, ADMET gate, Top-N selection |
| `2.Validation/` | OV 자동화 검증 리포트, config dump, prior review, integrity check |
| `3.Model_metadata/` | 모델 metric, ensemble summary |
| `4.Agent_reports/` | agent preflight/postflight 및 repair log |

## S3 기준 위치

- 이미지 모달 root: `s3://say2-4team/ov_image_modal_20260511_v1/`
- 기본 raw root: `s3://say2-4team/OV_raw/`
- 자동화 결과 root: `s3://say2-4team/pipeline_results/ov/`

## 보관 정책

- GitHub에는 CSV, JSON, Markdown, 작은 PNG만 포함한다.
- 원본 `.svs`는 비용 절감을 위해 S3에서도 정리 가능하며, 필요 시 GDC/TCGA에서 재다운로드한다.
- 임베딩과 대용량 중간 산출물은 GitHub에 포함하지 않는다.

## 검증 상태

OV 자동화 검증은 `2.Validation/ov_automation_validation_report_20260513.md` 기준으로 확인한다.

- seed 고정
- IM3 k=2~8 탐색
- IM4c confidence score 추가
- OV prior review
- AWS 자동화 프로토콜 반영

IM4a clinical은 데이터 확보 항목으로 별도 처리한다.
