#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

terraform init
terraform import aws_lambda_function.next_f1_session next-f1-session || true
terraform import aws_lambda_function_url.next_f1_session next-f1-session || true
terraform import aws_lambda_permission.function_url_public next-f1-session/FunctionURLAllowPublicAccess || true
terraform plan

