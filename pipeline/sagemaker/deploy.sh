#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-2}"
ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
SAGEMAKER_ROLE_ARN="${SAGEMAKER_ROLE_ARN:-arn:aws:iam::${ACCOUNT_ID}:role/SKKU-SageMaker-Processing-Execution-Role}"
STEP_FUNCTIONS_ROLE_ARN="${STEP_FUNCTIONS_ROLE_ARN:-arn:aws:iam::${ACCOUNT_ID}:role/drug-repurposing-step-functions-role}"
LAMBDA_ROLE_ARN="${LAMBDA_ROLE_ARN:-arn:aws:iam::${ACCOUNT_ID}:role/drug-repurposing-lambda-role}"
S3_OUTPUT_PATH="${S3_OUTPUT_PATH:-s3://say2-4team/pipeline_results}"
ANTHROPIC_SECRET_ID="${ANTHROPIC_SECRET_ID:-drug-repurposing/anthropic}"
RESOURCE_PROJECT_TAG="${RESOURCE_PROJECT_TAG:-pre-4team}"
PIPELINE_REPO="drug-repurposing-basic"
IM_GPU_REPO="drug-repurposing-im-gpu"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAGEMAKER_DIR="${ROOT_DIR}/sagemaker"

basic_uri="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PIPELINE_REPO}:latest"
im_gpu_uri="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${IM_GPU_REPO}:latest"


ensure_iam_role() {
  local role_name="$1" trust_file="$2" policy_file="$3"
  if aws iam get-role --role-name "${role_name}" >/dev/null 2>&1; then
    return 0
  fi
  if [[ "${CREATE_IAM_ROLES:-1}" != "1" ]]; then
    echo "Missing IAM role ${role_name}. Set CREATE_IAM_ROLES=1 or create it manually." >&2
    exit 1
  fi
  aws iam create-role --role-name "${role_name}" --assume-role-policy-document "file://${trust_file}" >/dev/null
  aws iam put-role-policy --role-name "${role_name}" --policy-name "${role_name}-inline" --policy-document "file://${policy_file}" >/dev/null
  echo "Created IAM role ${role_name}; waiting for propagation..."
  sleep 10
}

prepare_iam_roles() {
  local workdir="/tmp/drug-repurposing-iam"
  mkdir -p "${workdir}"
  cat > "${workdir}/lambda-trust.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  cat > "${workdir}/sfn-trust.json" <<'JSON'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"states.amazonaws.com"},"Action":"sts:AssumeRole"}]}
JSON
  cat > "${workdir}/lambda-policy.json" <<JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],"Resource":"*"},
 {"Effect":"Allow","Action":["secretsmanager:GetSecretValue","secretsmanager:DescribeSecret"],"Resource":"arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${ANTHROPIC_SECRET_ID}*"},
 {"Effect":"Allow","Action":["s3:ListBucket"],"Resource":"arn:aws:s3:::say2-4team"},
 {"Effect":"Allow","Action":["s3:GetObject","s3:HeadObject"],"Resource":"arn:aws:s3:::say2-4team/*"},
 {"Effect":"Allow","Action":["sts:GetCallerIdentity"],"Resource":"*"}
]}
JSON
  cat > "${workdir}/sfn-policy.json" <<JSON
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":["lambda:InvokeFunction"],"Resource":["arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:drug-repurposing-config","arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:drug-repurposing-validate"]},
 {"Effect":"Allow","Action":["sns:Publish"],"Resource":"arn:aws:sns:${REGION}:${ACCOUNT_ID}:drug-repurposing-alerts"},
 {"Effect":"Allow","Action":["sagemaker:CreateProcessingJob","sagemaker:DescribeProcessingJob","sagemaker:StopProcessingJob","sagemaker:CreateTrainingJob","sagemaker:DescribeTrainingJob","sagemaker:StopTrainingJob"],"Resource":"*"},
 {"Effect":"Allow","Action":["events:PutTargets","events:PutRule","events:DescribeRule"],"Resource":"*"},
 {"Effect":"Allow","Action":["iam:PassRole"],"Resource":"${SAGEMAKER_ROLE_ARN}"}
]}
JSON
  ensure_iam_role "$(basename "${LAMBDA_ROLE_ARN}")" "${workdir}/lambda-trust.json" "${workdir}/lambda-policy.json"
  ensure_iam_role "$(basename "${STEP_FUNCTIONS_ROLE_ARN}")" "${workdir}/sfn-trust.json" "${workdir}/sfn-policy.json"
}

prepare_iam_roles

echo "[1/6] ECR repositories"
aws ecr describe-repositories --repository-names "${PIPELINE_REPO}" --region "${REGION}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${PIPELINE_REPO}" --region "${REGION}" >/dev/null
aws ecr describe-repositories --repository-names "${IM_GPU_REPO}" --region "${REGION}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${IM_GPU_REPO}" --region "${REGION}" >/dev/null

aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "[2/6] Build/push basic image"
docker build --platform linux/amd64 -t "${PIPELINE_REPO}:latest" -f "${SAGEMAKER_DIR}/Dockerfile.basic" "${ROOT_DIR}"
docker tag "${PIPELINE_REPO}:latest" "${basic_uri}"
docker push "${basic_uri}"

if [[ "${BUILD_IM_GPU:-0}" == "1" ]]; then
  echo "[2b/6] Build/push IM GPU image"
  docker build --platform linux/amd64 -t "${IM_GPU_REPO}:latest" -f "${SAGEMAKER_DIR}/Dockerfile.im-gpu" "${ROOT_DIR}"
  docker tag "${IM_GPU_REPO}:latest" "${im_gpu_uri}"
  docker push "${im_gpu_uri}"
else
  echo "[2b/6] Skipping IM GPU image build. Set BUILD_IM_GPU=1 to build Dockerfile.im-gpu."
fi

echo "[3/6] Package Lambdas"
rm -rf /tmp/drug-repurposing-lambda && mkdir -p /tmp/drug-repurposing-lambda/config /tmp/drug-repurposing-lambda/validate
cp "${SAGEMAKER_DIR}/lambda_config.py" /tmp/drug-repurposing-lambda/config/lambda_function.py
cp "${SAGEMAKER_DIR}/lambda_validate.py" /tmp/drug-repurposing-lambda/validate/lambda_function.py
(cd /tmp/drug-repurposing-lambda/config && zip -q ../lambda_config.zip lambda_function.py)
(cd /tmp/drug-repurposing-lambda/validate && zip -q ../lambda_validate.zip lambda_function.py)

upsert_lambda() {
  local name="$1" zipfile="$2" handler="$3"
  if aws lambda get-function --function-name "${name}" --region "${REGION}" >/dev/null 2>&1; then
    aws lambda update-function-code --function-name "${name}" --zip-file "fileb://${zipfile}" --region "${REGION}" >/dev/null
  else
    aws lambda create-function --function-name "${name}" --runtime python3.11 --role "${LAMBDA_ROLE_ARN}" \
      --handler "${handler}" --zip-file "fileb://${zipfile}" --timeout 300 \
      --tags "project=${RESOURCE_PROJECT_TAG}" --region "${REGION}" >/dev/null
  fi
}

echo "[4/6] Deploy Lambdas"
upsert_lambda drug-repurposing-config /tmp/drug-repurposing-lambda/lambda_config.zip lambda_function.handler
upsert_lambda drug-repurposing-validate /tmp/drug-repurposing-lambda/lambda_validate.zip lambda_function.handler
aws lambda update-function-configuration --function-name drug-repurposing-config --region "${REGION}" \
  --environment "Variables={AWS_ACCOUNT_ID=${ACCOUNT_ID},SAGEMAKER_ROLE_ARN=${SAGEMAKER_ROLE_ARN},PIPELINE_IMAGE_URI=${basic_uri},IM_GPU_IMAGE_URI=${im_gpu_uri},S3_OUTPUT_PATH=${S3_OUTPUT_PATH},ANTHROPIC_SECRET_ID=${ANTHROPIC_SECRET_ID},WSI_DEFAULT_LIMIT=${WSI_DEFAULT_LIMIT:-100},WSI_MAX_LIMIT=${WSI_MAX_LIMIT:-200},WSI_SMOKE_COUNT=${WSI_SMOKE_COUNT:-1},WSI_PARALLEL_DOWNLOADS=${WSI_PARALLEL_DOWNLOADS:-4},EMBEDDING_PARALLEL_PARTS=${EMBEDDING_PARALLEL_PARTS:-4}}" >/dev/null

echo "[5/6] SNS topic"
aws sns create-topic --name drug-repurposing-alerts --region "${REGION}" >/dev/null
if [[ -n "${SNS_EMAIL:-}" ]]; then
  aws sns subscribe --topic-arn "arn:aws:sns:${REGION}:${ACCOUNT_ID}:drug-repurposing-alerts" --protocol email --notification-endpoint "${SNS_EMAIL}" --region "${REGION}" >/dev/null
fi

echo "[6/6] Step Functions definition"
def_file="/tmp/drug_repurposing_step_functions_definition.json"
sed -e "s/{region}/${REGION}/g" -e "s/{account}/${ACCOUNT_ID}/g" "${SAGEMAKER_DIR}/step_functions_definition.json" > "${def_file}"
if aws stepfunctions describe-state-machine --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:drug-repurposing" --region "${REGION}" >/dev/null 2>&1; then
  aws stepfunctions update-state-machine --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:drug-repurposing" \
    --definition "file://${def_file}" --role-arn "${STEP_FUNCTIONS_ROLE_ARN}" --region "${REGION}" >/dev/null
else
  aws stepfunctions create-state-machine --name drug-repurposing --definition "file://${def_file}" \
    --role-arn "${STEP_FUNCTIONS_ROLE_ARN}" --type STANDARD --region "${REGION}" >/dev/null
fi

echo "Done. Start test:"
echo "aws stepfunctions start-execution --state-machine-arn arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:drug-repurposing --input '{\"disease_name\":\"난소암\",\"disease_slug\":\"ov\"}'"
