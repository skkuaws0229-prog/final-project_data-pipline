# 약물 재창출 AWS 자동화

이 디렉터리는 로컬 3안 workflow를 AWS 2안 구조로 이관하기 위한 스캐폴딩이다.

`질환명 입력 -> Lambda config -> SageMaker 기본 파이프라인 -> SageMaker IM GPU -> SageMaker IM CPU -> Lambda 검증 -> SNS 알림`

Claude/Agentic AI config 생성 로직은 기존처럼 `run_disease_pipeline.py` 안에 둔다. 이 AWS 계층은 실행 위치, 권한, 저장소, 검증, 알림만 감싼다.

## 파일 구성

- `Dockerfile.basic`: `run_disease_pipeline.py`와 IM3~5 CPU 후처리를 실행하는 CPU 이미지
- `Dockerfile.im-gpu`: 기존 IM1~2 이미지를 재사용하지 못할 때 사용할 GPU 이미지 템플릿
- `basic_pipeline_job.py`: 기본 파이프라인 전체를 SageMaker Processing Job으로 제출하는 helper
- `image_modal_cpu_job.py`: IM3~5를 SageMaker Processing Job으로 제출하는 helper
- `run_image_modal_cpu.py`: IM3, IM4c, IM5를 순차 실행하는 Processing entrypoint
- `step_functions_definition.json`: Step Functions 정의 템플릿
- `lambda_config.py`: Secrets Manager와 환경변수에서 SageMaker/image/S3 config를 반환하는 Lambda handler
- `lambda_validate.py`: S3 산출물을 확인하고 PASS/FAIL을 반환하는 Lambda handler
- `deploy.sh`: ECR push, Lambda 배포, Step Functions/SNS 설정 스크립트
- `automation_protocol.md`: 질환별 자동화 운영 프로토콜

## 필요한 AWS 리소스/권한

- SageMaker execution role
  - S3 read/write
  - CloudWatch Logs 생성/쓰기
  - ECR pull
  - 컨테이너가 secret을 직접 읽기 위한 Secrets Manager read
- Lambda role
  - Secrets Manager read
  - STS get caller identity
  - S3 head/list
  - CloudWatch Logs
- Step Functions role
  - Lambda invoke
  - SageMaker create/describe/stop
  - SNS publish
  - SageMaker role에 대한 `iam:PassRole`
- ECR repository
  - `drug-repurposing-basic`
  - 필요 시 `drug-repurposing-im-gpu`
- Secret
  - `drug-repurposing/anthropic`
  - JSON 예: `{"ANTHROPIC_API_KEY":"..."}`

중요: Anthropic API key는 Step Functions execution history에 남기지 않는다. Lambda config는 secret id만 반환하고, SageMaker 컨테이너가 Secrets Manager에서 직접 API key를 읽는다.

## 배포

```bash
cd /Users/skku_aws2_14/pipeline
export AWS_REGION=ap-northeast-2
export SAGEMAKER_ROLE_ARN=arn:aws:iam::666803869796:role/SKKU-SageMaker-Processing-Execution-Role
export STEP_FUNCTIONS_ROLE_ARN=arn:aws:iam::666803869796:role/drug-repurposing-step-functions-role
export LAMBDA_ROLE_ARN=arn:aws:iam::666803869796:role/drug-repurposing-lambda-role
export S3_OUTPUT_PATH=s3://say2-4team/pipeline_results

# 선택: 완료 알림 이메일 구독
export SNS_EMAIL=you@example.com

bash sagemaker/deploy.sh
```

`deploy.sh`는 IAM role 자체를 새로 만들지 않는다. 배포 전 최소 권한 role을 만들거나 기존 role ARN을 지정해야 한다.

## OV E2E 시작

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-northeast-2:666803869796:stateMachine:drug-repurposing \
  --input '{"disease_name":"난소암","disease_slug":"ov"}'
```

## 산출물 위치

- 기본 파이프라인 결과: `s3://.../pipeline_results/{disease_slug}/basic_pipeline/`
- IM3~5 결과: `s3://.../pipeline_results/{disease_slug}/image_modal/`
- AWS job name에는 한글 질환명을 직접 쓰지 않고 `disease_slug`를 사용한다. SageMaker job name은 한글을 허용하지 않는다.

## 운영 메모

- IM1~2 GPU 단계는 `im_gpu_image_uri`를 사용하는 SageMaker job으로 연결한다.
- 운영 배포 전 기존 production WSI/UNI2 이미지와 entrypoint를 확정해야 한다.
- 비용이 발생하는 SageMaker job을 실행하기 전에는 권한 사전검사, 데이터 사전검사, 중복 active job 검사를 반드시 통과해야 한다.
- 권한 부족이 안전하게 보강 가능한 경우 최소 권한 inline policy를 추가한 뒤 preflight를 다시 수행한다.
- explicit deny 또는 계정 단위 정책으로 막히면 비용 발생 job을 실행하지 않는다.

## 이미지 모달 규모 프로토콜

WSI/UNI2 정책은 시간과 비용을 통제하기 위해 기본 상한을 둔다.

- WSI 기본 목표 개수: 100개
- WSI 최대 개수: 200개
- 실행 순서: 1-slide smoke 다운로드 -> S3 `.svs` 업로드 확인 -> main WSI 다운로드
- WSI 다운로드 병렬도: SageMaker job 내부 4개 download worker
- 임베딩 병렬도: 기본 4-way SageMaker part
  - 100개: 25/25/25/25
  - 200개: 50/50/50/50
- 목표 raw `.svs` 개수에 도달하기 전에는 tile/embedding을 실행하지 않는다.
- 4-way split을 지킬 수 없으면 비용 발생 job을 실행하지 않고 이유를 보고한다.

이 값은 `drug-repurposing-config` Lambda가 `image_modal_policy`로 반환하며, 배포 시 환경변수로 바꿀 수 있다.

```bash
export WSI_DEFAULT_LIMIT=100
export WSI_MAX_LIMIT=200
export WSI_SMOKE_COUNT=1
export WSI_PARALLEL_DOWNLOADS=4
export EMBEDDING_PARALLEL_PARTS=4
bash sagemaker/deploy.sh
```

## 기본 파이프라인 데이터 프로토콜

기본 파이프라인은 S3에 이미 있는 데이터를 먼저 재사용하고, 누락된 질환별 입력만 확보한다. 무결성 검사를 통과한 공용 데이터를 다시 다운로드하거나 다시 provision하지 않는다.

기준 S3 위치:

- 질환별 raw root: `s3://say2-4team/{DISEASE}_raw/`
  - 예: `s3://say2-4team/OV_raw/`, `s3://say2-4team/HNSC_raw/`, `s3://say2-4team/STAD_raw/`, `s3://say2-4team/PAAD_raw/`
- raw template/provision source: `s3://say2-4team/HNSC_raw/`
- 기본 파이프라인 결과: `s3://say2-4team/pipeline_results/{disease_slug}/basic_pipeline/`
- 이미지 모달 root: `s3://say2-4team/{disease_slug}_image_modal_YYYYMMDD_v1/`

`{DISEASE}_raw/` 아래에서 확인할 공용/기본 객체:

- `GDSC/GDSC2-dataset.csv`
- `GDSC/screened_compounds_rel_8.5.csv`
- `depmap/Model.csv`
- `depmap/Gene.csv`
- `depmap/CRISPRGeneEffect.csv`
- `drug/drug_features_catalog.parquet`
- `drug/drug_target_mapping.parquet`
- `lincs/lincs_drug_signature_normalized.parquet`
- `admet/admet_group.zip`

에이전트 동작 기준:

1. 질환명에서 disease code와 target raw root를 확정한다.
2. 데이터 복사나 SageMaker launch 전에 권한 사전검사를 수행한다.
3. `{DISEASE}_raw/` 아래 required object의 존재 여부, size, 0-byte 여부를 확인한다.
4. 유효한 기존 객체는 모두 재사용한다.
5. 누락된 공용 객체만 `HNSC_raw` 또는 설정된 template root에서 복사/provision한다.
6. 질환별로 누락된 최소 입력만 다운로드한다. 보통 core disease dataset 1개와 외부검증/cohort 데이터 1~2개 수준이다.
7. source, destination, object count, total bytes, config hash, timestamp를 포함한 manifest를 남긴다.
8. 권한과 데이터 검사가 모두 통과한 뒤에만 SageMaker basic pipeline job을 실행한다.

## 실패 처리

- IAM 권한이 없고 안전하게 추가 가능하면 최소 권한 inline policy를 추가/업데이트한 뒤 preflight를 다시 실행한다.
- explicit deny 또는 account-level policy가 막고 있으면 비용 발생 job을 실행하지 않고 blocked action/resource를 보고한다.
- 필수 데이터가 없고 설정된 source도 없으면 데이터를 임의 생성하지 않는다. blocked로 보고하고 source가 필요하다고 남긴다.
- partial data가 있으면 처음부터 다시 받지 않고 누락 객체만 이어서 받는다.

이 프로토콜은 OV에만 특화된 것이 아니다. 질환별 config는 바뀌지만, 데이터 재사용, 권한 사전검사, 최소 다운로드, manifest, launch gate는 이후 질환에도 동일하게 적용한다.
