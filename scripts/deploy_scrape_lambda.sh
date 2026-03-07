#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

PROFILE="${AWS_PROFILE:-f1-sso}"
REGION="${AWS_REGION:-us-east-1}"
FUNCTION_NAME="${SCRAPE_LAMBDA_FUNCTION_NAME:-scrape-f1-data}"
RULE_NAME="${SCRAPE_RULE_NAME:-${FUNCTION_NAME}-hourly}"
SCHEDULE_EXPRESSION="${SCRAPE_SCHEDULE_EXPRESSION:-rate(1 hour)}"
ROLE_ARN="${SCRAPE_LAMBDA_ROLE_ARN:-arn:aws:iam::373892137535:role/service-role/next-f1-session-role-m81fwq00}"
YEAR="${F1_YEAR:-2026}"
BUCKET="${DATA_BUCKET:-f1-data-00000000}"
RUNTIME="${SCRAPE_LAMBDA_RUNTIME:-python3.13}"
TIMEOUT="${SCRAPE_LAMBDA_TIMEOUT:-180}"
MEMORY_SIZE="${SCRAPE_LAMBDA_MEMORY_SIZE:-512}"

usage() {
  cat <<USAGE
Usage:
  scripts/deploy_scrape_lambda.sh [options]

Options:
  --profile <name>     AWS profile (default: $PROFILE)
  --region <region>    AWS region (default: $REGION)
  --function <name>    Lambda function name (default: $FUNCTION_NAME)
  --rule <name>        EventBridge rule name (default: $RULE_NAME)
  --schedule <expr>    Schedule expression (default: $SCHEDULE_EXPRESSION)
  --role-arn <arn>     Lambda role ARN (default: $ROLE_ARN)
  --year <year>        F1 year env var (default: $YEAR)
  --bucket <bucket>    S3 bucket env var (default: $BUCKET)
  --runtime <runtime>  Lambda runtime (default: $RUNTIME)
  --timeout <sec>      Lambda timeout seconds (default: $TIMEOUT)
  --memory <mb>        Lambda memory MB (default: $MEMORY_SIZE)
  -h, --help           Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --function) FUNCTION_NAME="$2"; shift 2 ;;
    --rule) RULE_NAME="$2"; shift 2 ;;
    --schedule) SCHEDULE_EXPRESSION="$2"; shift 2 ;;
    --role-arn) ROLE_ARN="$2"; shift 2 ;;
    --year) YEAR="$2"; shift 2 ;;
    --bucket) BUCKET="$2"; shift 2 ;;
    --runtime) RUNTIME="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --memory) MEMORY_SIZE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

for cmd in aws python3 zip; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
done

BUILD_ROOT="$(mktemp -d)"
PKG_DIR="$BUILD_ROOT/pkg"
ZIP_PATH="$BUILD_ROOT/${FUNCTION_NAME}.zip"
mkdir -p "$PKG_DIR"

echo "Packaging scraper lambda..."
python3 -m pip install -r requirements.txt -t "$PKG_DIR" >/dev/null
cp lambda_scrape_function.py "$PKG_DIR/"
cp -R src "$PKG_DIR/"
(
  cd "$PKG_DIR"
  zip -r "$ZIP_PATH" . >/dev/null
)

echo "Ensuring lambda role has S3 read/write for bucket $BUCKET"
ROLE_NAME="${ROLE_ARN##*/}"
cat > "$BUILD_ROOT/s3-policy.json" <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::$BUCKET"
    },
    {
      "Sid": "ReadWriteObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::$BUCKET/*"
    }
  ]
}
POLICY
aws iam put-role-policy \
  --profile "$PROFILE" \
  --policy-name "scrape-f1-data-s3-access" \
  --role-name "$ROLE_NAME" \
  --policy-document "file://$BUILD_ROOT/s3-policy.json" >/dev/null

if aws lambda get-function --profile "$PROFILE" --region "$REGION" --function-name "$FUNCTION_NAME" >/dev/null 2>&1; then
  echo "Updating existing lambda: $FUNCTION_NAME"
  aws lambda update-function-code \
    --profile "$PROFILE" \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_PATH" >/dev/null
  aws lambda update-function-configuration \
    --profile "$PROFILE" \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler "lambda_scrape_function.lambda_handler" \
    --timeout "$TIMEOUT" \
    --memory-size "$MEMORY_SIZE" \
    --environment "Variables={DATA_BUCKET=$BUCKET,F1_YEAR=$YEAR}" >/dev/null
else
  echo "Creating lambda: $FUNCTION_NAME"
  aws lambda create-function \
    --profile "$PROFILE" \
    --region "$REGION" \
    --function-name "$FUNCTION_NAME" \
    --role "$ROLE_ARN" \
    --runtime "$RUNTIME" \
    --handler "lambda_scrape_function.lambda_handler" \
    --timeout "$TIMEOUT" \
    --memory-size "$MEMORY_SIZE" \
    --environment "Variables={DATA_BUCKET=$BUCKET,F1_YEAR=$YEAR}" \
    --zip-file "fileb://$ZIP_PATH" >/dev/null
fi

FUNCTION_ARN=$(aws lambda get-function --profile "$PROFILE" --region "$REGION" --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text)

echo "Configuring EventBridge rule: $RULE_NAME ($SCHEDULE_EXPRESSION)"
aws events put-rule \
  --profile "$PROFILE" \
  --region "$REGION" \
  --name "$RULE_NAME" \
  --schedule-expression "$SCHEDULE_EXPRESSION" \
  --state ENABLED >/dev/null

aws events put-targets \
  --profile "$PROFILE" \
  --region "$REGION" \
  --rule "$RULE_NAME" \
  --targets "Id"="1","Arn"="$FUNCTION_ARN" >/dev/null

RULE_ARN=$(aws events describe-rule --profile "$PROFILE" --region "$REGION" --name "$RULE_NAME" --query 'Arn' --output text)

aws lambda add-permission \
  --profile "$PROFILE" \
  --region "$REGION" \
  --function-name "$FUNCTION_NAME" \
  --statement-id "AllowEventBridgeInvoke" \
  --action "lambda:InvokeFunction" \
  --principal events.amazonaws.com \
  --source-arn "$RULE_ARN" >/dev/null 2>&1 || true

echo "Done."
echo "Lambda: $FUNCTION_NAME"
echo "Rule:   $RULE_NAME"
echo "Bucket: $BUCKET"
