# 최종 프로젝트 데이터 파이프라인

이 저장소는 11개 질환의 약물 재창출 파이프라인과 이미지 모달 분석 결과를 GitHub에 올릴 수 있는 가벼운 형태로 정리한 패키지입니다.

원본 WSI, DICOM 이미지, UNI2/BiomedCLIP/CT-CLIP 임베딩, parquet shard, 학습된 모델 바이너리처럼 용량이 큰 파일은 GitHub에 포함하지 않고 S3에 보관합니다.

S3 원본 위치:

`s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/`

## 폴더 구성

| 폴더 | 질환 / 워크플로우 | 주요 내용 |
| --- | --- | --- |
| `BRCA/` | 유방암 | 이미지 모달 clinical, clustering, survival, drug interpretation 요약 |
| `LUNG/` | 폐암, LUAD | LUAD 이미지 모달 결과, 리포트, 스크립트, 주요 supporting input |
| `Liver/` | 간암, LIHC | LIHC 이미지 모달 결과 및 생성 분석 산출물 |
| `Colon/` | 대장암, COAD | COAD 이미지 모달 후단 분석 결과 |
| `STAD/` | 위암 | STAD 이미지 모달 후단 분석 결과 |
| `PDAC/` | 췌장암, PAAD | PDAC/PAAD 이미지 모달, 리포트, 스크립트, ADMET 요약 |
| `HNSC/` | 두경부암 | HNSC 이미지 모달, 리포트, 스크립트, 외부 검증 요약 |
| `IPF/` | 특발성 폐섬유증 | CT 이미지 모달 결과, 약물 결과, 외부 검증, 모델 메타데이터 |
| `PAH/` | 폐동맥고혈압 | CT 이미지 모달 결과, 약물 결과, 외부 검증, 모델 메타데이터 |
| `Psoriasis/` | 건선 | BiomedCLIP 이미지 모달 결과, HISTAI UNI2 가능성 검토 manifest |
| `RA/` | 류마티스 관절염 | X-ray 이미지 모달 결과, 약물 결과, 외부 검증 요약 |
| `pipeline/` | 자동 워크플로우 파이프라인 | 오케스트레이터, 11개 config, step 모듈, 공통 유틸 |

## 포함된 자료

- 재현 가능한 워크플로우 코드와 YAML config
- Step별 CSV, JSON, Markdown 요약
- 가벼운 PCA, Kaplan-Meier, 리포트 이미지
- Top drug, ADMET, 4-Tier, cluster-drug linkage 결과
- S3 manifest 및 데이터 확보/가능성 검토 요약
- 통합 보고서 수치 보강 파일

## 포함하지 않은 자료

- 원본 WSI, DICOM, 임상 이미지 파일
- 대용량 임베딩 배열 (`.npy`, `.npz`) 및 parquet shard
- 학습된 모델 바이너리/checkpoint
- 대용량 raw API dump 및 중간 prediction matrix
- 비밀번호, API key, HuggingFace token, AWS access key 같은 민감정보

대용량 원본과 중간 산출물은 위 S3 경로를 기준으로 확인하면 됩니다.

## 민감정보 점검

커밋 전 다음 유형의 문자열을 스캔했습니다.

- `sk-ant-*`, `sk-*` 형태 API key
- AWS access key (`AKIA*`, `ASIA*`)
- `aws_secret_access_key`
- private key 블록
- `HF_TOKEN`, `HUGGINGFACE_HUB_TOKEN`
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

실제 secret 값은 발견되지 않았습니다. 코드 안에는 환경변수 이름 예시만 포함되어 있습니다.
