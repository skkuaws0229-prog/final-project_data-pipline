# 로컬 에이전트 자동 실행 프로토콜

이 문서는 로컬 환경에서 Codex/Agent가 파이프라인을 오케스트레이션하는 실행 기준이다. AWS 완전 자동화로 이관하기 전, 사람이 질환명 하나를 주면 에이전트가 확인, 실행, 모니터링, 후속 단계 진행을 맡는 방식이다.

AWS Step Functions 기반 실행은 `pipeline/sagemaker/README_sagemaker.md`를 따른다.

## 실행 목표

사용자는 질환명과 실행 모드만 지정한다.

```bash
cd /Users/skku_aws2_14/pipeline
python3 run_disease_pipeline.py --disease "난소암" --mode full
```

로컬 에이전트는 아래 흐름을 끝까지 이어간다.

`질환명 입력 -> agentic config 생성 -> 권한/데이터 사전검사 -> 기본 파이프라인 -> 이미지 모달 -> 검증 -> 결과 정리`

## 에이전트 역할

로컬 실행에서는 에이전트가 오케스트레이터다.

- Agent 0: supervisor, preflight/postflight, 중복 job 방지
- Agent 1: config 생성, 질환명/TCGA project/S3 root/모델 설정 확정
- Agent 2: 결과 평가, PASS/CONDITIONAL PASS/FAIL 판단
- Agent 3: self-heal, 누락 파일/권한/shape 문제 repair

실행 중 사용자가 자리를 비워도, 이미 합의된 프로토콜 안에서는 사용자 승인을 기다리지 않고 다음 확인과 후속 실행을 진행한다. 단, 비용이 발생하는 새 SageMaker job은 preflight를 통과해야 한다.

## 기본 파이프라인

기본 파이프라인은 `run_disease_pipeline.py`가 실행한다.

주요 단계:

- Step 1: 데이터 수집/정규화
- Step 2: feature engineering, 모델 학습, 앙상블, Top drug ranking
- Step 3: ADMET gate, final selection

데이터 원칙:

- S3에 이미 있는 공용/기본 데이터는 재사용한다.
- `{DISEASE}_raw/` 아래 필수 객체의 존재 여부, size, 0-byte 여부를 확인한다.
- 누락된 공용 객체만 template root에서 복사/provision한다.
- 질환별 누락 데이터만 최소 확보한다. 보통 core disease dataset 1개와 외부검증/cohort 데이터 1~2개 수준이다.
- 권한 사전검사와 데이터 사전검사를 통과한 뒤에만 실행한다.

기준 S3 위치:

- 질환별 raw root: `s3://say2-4team/{DISEASE}_raw/`
- template/provision root: `s3://say2-4team/HNSC_raw/`
- 결과 root: `s3://say2-4team/pipeline_results/{disease_slug}/basic_pipeline/`

## 이미지 모달

이미지 모달은 로컬 에이전트가 SageMaker job을 launch/monitor하고, 완료된 산출물을 확인한 뒤 후속 로컬 step을 진행한다.

주요 단계:

- IM1: WSI raw 확보
- IM2: tile preprocessing 및 UNI2 embedding
- IM3: patient/slide embedding clustering
- IM4a: clinical/mutation association, 데이터가 없으면 pending으로 기록
- IM4c: cluster-drug link
- IM5: image modal summary report

규모/비용 통제 기준:

- WSI 기본 목표 개수: 100개
- WSI 최대 개수: 200개
- 먼저 1개 slide smoke 다운로드
- smoke `.svs`가 S3에 올라온 것을 확인한 뒤 main WSI 다운로드
- main WSI 다운로드는 기본 4개 병렬 worker
- 목표 raw `.svs` 개수에 도달하기 전에는 tile/embedding을 실행하지 않는다.
- 임베딩은 기본 4-way SageMaker part
  - 100개: 25/25/25/25
  - 200개: 50/50/50/50
- 4-way split을 지킬 수 없으면 비용 발생 job을 보류하고 이유를 보고한다.

## 권한 사전검사

비용이 발생하는 job이나 업로드 전에 권한을 먼저 확인한다.

- S3 `ListBucket`, `HeadObject`, `GetObject`, `PutObject`, multipart upload
- SageMaker `CreateProcessingJob`, `DescribeProcessingJob`, `StopProcessingJob`
- CloudWatch Logs read/write
- ECR pull
- Secrets Manager `GetSecretValue`
- SageMaker role에 대한 `iam:PassRole`

권한이 부족하면:

- 안전하게 추가 가능한 최소 권한 inline policy를 생성/수정한다.
- 권한 보강 후 preflight를 다시 실행한다.
- explicit deny 또는 계정 단위 정책이면 비용 발생 job을 실행하지 않는다.
- 막힌 action/resource를 기록한다.

## 중복 실행 방지

새 SageMaker job을 띄우기 전에 항상 확인한다.

- 같은 질환/step의 active job이 있는지
- target S3 output이 이미 nonzero인지
- pending/failed/completed 상태가 정확한지
- upstream 산출물이 완전한지

이미 완료된 step은 재실행하지 않는다. partial output은 누락된 부분만 이어서 처리한다.

## 재현성 기준

- `random_seed: 42`를 config에 기록한다.
- `random`, `numpy`, `torch`, `sklearn` seed를 고정한다.
- KMeans는 `random_state=42`, `n_init=10` 기준으로 실행한다.
- train/test split과 CV fold도 가능한 경우 `random_state=42`를 사용한다.
- IM2 embedding merge는 정렬된 sample/slide 순서를 사용한다.

## 산출물 정리

로컬 실행 산출물은 질환별 폴더 아래에 남긴다.

예:

```text
OV_pipeline/
  outputs/
    final_selection/
    model_runs/
    image_modal/
    validation/
    agent_reports/
```

GitHub에는 경량 결과만 올린다.

포함:

- CSV, JSON, Markdown
- 작은 PNG plot
- config dump
- validation report
- agent preflight/postflight log

제외:

- `.svs`
- `.npy`, `.npz`
- tile/embedding `.h5`
- 대용량 parquet
- 모델 바이너리/checkpoint
- secret/API key/token
- raw cache 전체

대용량 원본과 중간 산출물은 S3에 두고, 비용이 큰 원본 `.svs`는 후속 산출물이 확보된 뒤 삭제 후보로 본다.

## AWS 이관 관계

이 로컬 프로토콜은 AWS 이관 전 검증용이자 기준 동작이다.

- 로컬: 에이전트 4개가 확인/실행/모니터링/repair를 맡는다.
- AWS: Lambda가 오케스트레이션하고 SageMaker/Step Functions가 실행한다.
- 공통: 권한 preflight, 데이터 재사용, 1-slide smoke, 4-way 병렬, seed 고정, manifest 기록, 중복 job 방지 원칙은 동일하다.

AWS 완전 자동화 문서는 `pipeline/sagemaker/README_sagemaker.md`와 `pipeline/sagemaker/automation_protocol.md`를 따른다.
