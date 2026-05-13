# 약물 재창출 AWS 자동화 프로토콜

이 문서는 질환 단위 AWS 자동화의 기본 운영 기준이다. 난소암(OV)에서 검증한 방식이며, 별도 예외를 명시하지 않는 한 이후 모든 질환에도 동일하게 적용한다.

## 핵심 원칙

사용자는 질환명 하나만 입력한다. 이후 시스템은 아래 순서로 자동 진행한다.

`질환명 입력 -> 에이전트 config 생성 -> 권한 사전검사 -> 데이터 사전검사 -> 누락 데이터 최소 확보 -> SageMaker job 실행 -> 결과 검증 -> S3 저장 -> 알림`

Lambda는 판단과 오케스트레이션만 담당한다. 긴 다운로드, 업로드, 이미지 처리, 모델 실행, 임베딩은 Lambda에서 하지 않고 SageMaker 또는 장시간 실행 가능한 job 서비스에서 수행한다.

## 권한 사전검사

비용이 발생하는 job을 실행하기 전에 관련 role과 S3 prefix에 대한 권한을 반드시 확인한다.

- S3 `ListBucket`, `HeadObject`, `GetObject`, `PutObject`, multipart upload 권한
- Secrets Manager `GetSecretValue` 권한
- CloudWatch Logs 생성/쓰기 권한
- ECR image pull 권한
- Step Functions가 SageMaker execution role을 넘길 수 있는 `iam:PassRole` 권한

권한이 없을 경우:

- 안전하게 추가 가능한 권한이면 최소 범위 inline policy를 생성하거나 업데이트한다.
- 권한을 보강한 뒤 사전검사를 다시 수행한다.
- explicit deny 또는 계정 단위 정책으로 막힌 경우 비용 발생 job을 실행하지 않는다.
- 어떤 action/resource가 막혔는지 보고한다.

## 기본 파이프라인 데이터 사전검사

기준 S3 위치:

- 질환별 raw root: `s3://say2-4team/{DISEASE}_raw/`
- template/provision 기준 root: `s3://say2-4team/HNSC_raw/`
- 기본 파이프라인 결과 root: `s3://say2-4team/pipeline_results/{disease_slug}/basic_pipeline/`

`{DISEASE}_raw/` 아래에서 확인해야 하는 공용/기본 객체:

- `GDSC/GDSC2-dataset.csv`
- `GDSC/screened_compounds_rel_8.5.csv`
- `depmap/Model.csv`
- `depmap/Gene.csv`
- `depmap/CRISPRGeneEffect.csv`
- `drug/drug_features_catalog.parquet`
- `drug/drug_target_mapping.parquet`
- `lincs/lincs_drug_signature_normalized.parquet`
- `admet/admet_group.zip`

동작 원칙:

- 이미 S3에 있고 무결성 검사를 통과한 데이터는 재사용한다.
- 공용/기본 객체 중 누락된 것만 template root에서 복사하거나 provision한다.
- 질환별로 추가로 필요한 데이터만 최소 다운로드한다. 보통 core disease dataset 1개와 외부검증/cohort 데이터 1~2개 수준이다.
- object count, byte size, 0 byte 파일 여부를 확인한다.
- 기본 파이프라인 실행 전에 manifest를 남긴다.
- 권한 사전검사와 데이터 사전검사를 모두 통과한 뒤에만 SageMaker basic pipeline job을 실행한다.

## 이미지 모달 사전검사

WSI와 임베딩 job은 시간과 비용을 통제하기 위해 기본 상한을 둔다.

- WSI 기본 목표 개수: 100개
- WSI 최대 개수: 200개
- 먼저 1개 slide smoke 다운로드를 실행한다.
- smoke 결과가 S3에 실제 `.svs` 객체로 올라온 것을 확인한 뒤 main WSI 다운로드를 진행한다.
- main WSI 다운로드는 기본 4개 병렬 download worker로 진행한다.
- 목표 raw `.svs` 개수에 도달하기 전에는 tile/embedding 단계로 넘어가지 않는다.
- 임베딩은 기본 4-way 병렬 part로 진행한다.
  - 100개: 25/25/25/25
  - 200개: 50/50/50/50
- 4-way split을 지킬 수 없으면 비용 발생 job을 실행하지 않고 이유를 보고한다.

## 재시작과 manifest

모든 단계는 재시작 가능해야 한다.

- 유효한 산출물이 이미 있는 완료 step은 재실행하지 않는다.
- partial output을 감지하고 누락된 부분만 채운다.
- 각 step은 가능하면 `manifest.json`을 남긴다.
- manifest에는 input path, output path, object count, total bytes, job name, instance type, 시작/종료 시각, random seed, config hash, code version을 기록한다.

## 실패 처리 원칙

- upstream step이 실패했거나 산출물이 불완전하면 downstream step을 실행하지 않는다.
- 같은 질환/step에 대해 중복 active SageMaker job을 띄우지 않는다.
- API key를 Step Functions execution history에 남기지 않는다.
- 없는 질환 데이터를 임의로 만들거나 추정하지 않는다. source가 없으면 blocked 상태로 보고한다.
- 실패 시 FailureReason, 막힌 권한/action/resource, CloudWatch log stream을 가능한 한 함께 보고한다.
