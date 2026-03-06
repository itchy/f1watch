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
"$TF_BIN" plan
