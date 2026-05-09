# S3 데이터 인덱스

대용량 원본과 중간 산출물의 기준 위치:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/`

## 질환별 S3 경로

| GitHub 폴더 | S3 Prefix |
| --- | --- |
| `BRCA/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/BRCA/` |
| `LUNG/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/LUNG/` |
| `Liver/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/` |
| `Colon/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Colon/` |
| `STAD/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/STAD/` |
| `PDAC/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PDAC/` |
| `HNSC/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/HNSC/` |
| `IPF/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/IPF/` |
| `PAH/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/PAH/` |
| `Psoriasis/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Psoriasis/` |
| `RA/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/RA/` |
| `pipeline/` | `s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/pipeline/` |

## GitHub 패키징 기준

이 저장소는 재현과 보고서 작성에 필요한 가벼운 결과물만 미러링합니다.

GitHub에 포함:

- 코드, config, 실행 스크립트
- 요약 CSV/JSON/Markdown
- 가벼운 분석 이미지
- cluster-drug, ADMET, 4-Tier 결과

S3에만 보관:

- 원본 WSI/DICOM/임상 이미지
- 대용량 임베딩 및 parquet shard
- 모델 checkpoint와 큰 prediction matrix
- raw source snapshot과 대용량 중간 산출물
