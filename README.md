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
| `OV/` | 난소암 | OV 기본 파이프라인, 이미지 모달, 자동화 검증 결과 |
| `PDAC/` | 췌장암, PAAD | PDAC/PAAD 이미지 모달, 리포트, 스크립트, ADMET 요약 |
| `HNSC/` | 두경부암 | HNSC 이미지 모달, 리포트, 스크립트, 외부 검증 요약 |
| `IPF/` | 특발성 폐섬유증 | CT 이미지 모달 결과, 약물 결과, 외부 검증, 모델 메타데이터 |
| `PAH/` | 폐동맥고혈압 | CT 이미지 모달 결과, 약물 결과, 외부 검증, 모델 메타데이터 |
| `Psoriasis/` | 건선 | BiomedCLIP 이미지 모달 결과, HISTAI UNI2 가능성 검토 manifest |
| `RA/` | 류마티스 관절염 | X-ray 이미지 모달 결과, 약물 결과, 외부 검증 요약 |
| `pipeline/` | 자동 워크플로우 파이프라인 | 오케스트레이터, 11개 config, step 모듈, 공통 유틸 |

## 파이프라인 실행 문서

`pipeline/`에는 실행 방식별 README가 분리되어 있습니다.

- `pipeline/README_local_agent.md`: 로컬 에이전트 4개 기반 실행 프로토콜. 기본 파이프라인, 이미지 모달, 임베딩, 약물 추천, 검증을 에이전트가 확인하며 이어서 진행합니다.
- `pipeline/sagemaker/README_sagemaker.md`: AWS 이관 실행 문서. Lambda, Step Functions, SageMaker, Secrets Manager, S3 preflight 기반으로 질환명 하나를 받아 자동 실행합니다.
- `pipeline/sagemaker/automation_protocol.md`: 로컬/AWS 공통 운영 원칙. 권한 사전검사, 데이터 재사용, 1-slide smoke, 4-way 병렬, seed 고정, 중복 job 방지 기준을 정리합니다.
- `docs/rag_bedrock_retrieval_contract_v1.md`: Bedrock/LLM 호출 전에 프론트가 사용할 retrieval context 백엔드 계약입니다. 실제 Bedrock 호출은 포함하지 않습니다.
- `docs/rag_bedrock_retrieval_connection_validation_v1.md`: retrieval 계약 작성 후 현재 backend 연결 상태 재검증 결과입니다.
- `docs/frontend_v1_connection_qa_pass_20260514.md`: 프론트 v1 연결 QA 통과 기록입니다.
- `docs/explanation_context_api_validation_v1.md`: Bedrock 연결 전 설명용 근거 패키지 API 검증 결과입니다.
- `docs/assistant_api_validation_v1.md`: 프론트 챗봇 team API assistant endpoint 검증 결과입니다. Bedrock 호출은 포함하지 않습니다.
- `docs/backend_db_integrity_frontend_handoff_v1.md`: 백엔드/DB 전체 무결성과 프론트 전달 준비 검증 결과입니다.
- `docs/frontend_api_handoff_workflow_v1.md`: 프론트에 전달할 API 목록과 전체 워크플로우입니다.

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
- Python 가상환경 (`.venv`)
- Node.js 의존성 폴더 (`node_modules`)
- Docker volume, PostgreSQL/Neo4j/OpenSearch 실제 데이터 디렉터리
- `__pycache__`, `*.pyc`, frontend build output 같은 로컬 cache/build 산출물

대용량 원본과 중간 산출물은 위 S3 경로를 기준으로 확인하면 됩니다.

위 항목들은 누락이 아니라 의도적으로 제외한 항목입니다. GitHub에는 재현 가능한 코드, 설정, schema, 정규화 CSV, 검증 리포트만 올립니다. 실행 환경은 `requirements.txt`, `package.json`, Docker Compose 파일을 기준으로 각자 로컬 또는 EC2에서 다시 생성합니다.

## 재현 가능 범위

이 저장소만으로 가능한 재현:

- 11개 질환별 폴더 구조와 최종 산출물 확인
- 보고서에 들어간 주요 수치 검증
- ADMET, 4-Tier, cluster-drug linkage 결과 확인
- 이미지 모달 후단 분석의 CSV/JSON/Markdown 결과 확인
- `pipeline/` 오케스트레이터와 11개 YAML config 구조 확인
- 일부 후단 분석 로직 재사용 및 dry-run 실행

S3 접근이 함께 있어야 가능한 재현:

- 원본 WSI/DICOM/임상 이미지 기반 전처리
- UNI2, BiomedCLIP, CT-CLIP 임베딩 재생성
- `.npy`, `.parquet`, model checkpoint 기반 완전 재학습
- Step 1부터 Step 5까지 end-to-end 재현
- SageMaker 또는 로컬 XPU/GPU 기반 대용량 임베딩 작업

따라서 이 GitHub 저장소는 **경량 재현 패키지 + 결과 검증 패키지**입니다. S3 데이터 접근 권한이 함께 있으면 **end-to-end 재현 패키지**로 사용할 수 있습니다.

재현 흐름:

1. GitHub 저장소를 clone합니다.
2. `S3_DATA_INDEX.md`에서 질환별 S3 prefix를 확인합니다.
3. 필요한 대용량 원본, 임베딩, parquet, 모델 산출물을 S3에서 내려받습니다.
4. `pipeline/configs/`의 질환별 YAML을 기준으로 후단 분석 또는 전체 파이프라인을 실행합니다.

예시:

```powershell
git clone https://github.com/skkuaws0215/final-project_data-pipline.git
cd final-project_data-pipline

python pipeline/run_disease_pipeline.py --config pipeline/configs/04_coad.yaml --dry-run
```

## 민감정보 점검

커밋 전 다음 유형의 문자열을 스캔했습니다.

- `sk-ant-*`, `sk-*` 형태 API key
- AWS access key (`AKIA*`, `ASIA*`)
- `aws_secret_access_key`
- private key 블록
- `HF_TOKEN`, `HUGGINGFACE_HUB_TOKEN`
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`

실제 secret 값은 발견되지 않았습니다. 코드 안에는 환경변수 이름 예시만 포함되어 있습니다.
