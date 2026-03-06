#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TF_BIN="${TERRAFORM_BIN:-terraform}"
if ! command -v "$TF_BIN" >/dev/null 2>&1; then
  if [ -x /opt/homebrew/bin/terraform ]; then
    TF_BIN=/opt/homebrew/bin/terraform
  else
    echo "terraform binary not found on PATH and /opt/homebrew/bin/terraform is missing" >&2
    exit 1
  fi
fi

"$TF_BIN" init
"$TF_BIN" import aws_lambda_function.next_f1_session next-f1-session || true
"$TF_BIN" import aws_lambda_function_url.next_f1_session next-f1-session || true
"$TF_BIN" import aws_lambda_permission.function_url_public next-f1-session/FunctionURLAllowPublicAccess || true
"$TF_BIN" import aws_apigatewayv2_api.f1_next_session rswa7d9iui || true
"$TF_BIN" import aws_apigatewayv2_integration.f1_next_session_lambda rswa7d9iui/vngkyh6 || true
"$TF_BIN" import aws_apigatewayv2_route.f1_next_session_get_root rswa7d9iui/t11l2qk || true
"$TF_BIN" import aws_apigatewayv2_stage.f1_next_session_default 'rswa7d9iui/$default' || true
"$TF_BIN" import aws_apigatewayv2_domain_name.f1_custom_domain f1.itchy7.com || true
"$TF_BIN" import aws_apigatewayv2_api_mapping.f1_custom_domain_root '99th9m/f1.itchy7.com' || true
"$TF_BIN" import aws_lambda_permission.apigateway_invoke_next_f1_session next-f1-session/AllowApiGatewayInvokeNextF1Session || true
"$TF_BIN" plan
