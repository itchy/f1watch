# Terraform for F1 Watch

This directory manages the current Lambda + API Gateway stack behind `f1.itchy7.com`.

## What is managed now

- Lambda function: `next-f1-session`
- Lambda Function URL
- Public Function URL permission (`FunctionURLAllowPublicAccess`)
- API Gateway HTTP API: `f1-next-session-api`
- API Gateway integration/route/stage (`GET /`, `$default`)
- API Gateway custom domain + mapping (`f1.itchy7.com`)
- Lambda invoke permission for API Gateway
- Optional second Lambda function: `next-pl-session`
- Optional second Lambda Function URL + public URL permission
- Lambda code packaging from:
  - `lambda_function.py`
  - `lambda_pl_function.py`
  - `src/`
- CloudFront distribution lookup as read-only data (for outputs/reference)

## Prerequisites

- Terraform `>= 1.6`
- AWS credentials/profile (`f1-sso` by default)
- `zip` command available locally

## First-time setup (import existing resources)

```bash
cd /Users/scott/code/f1/infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform import aws_lambda_function.next_f1_session next-f1-session
terraform import aws_lambda_function_url.next_f1_session next-f1-session
terraform import aws_lambda_permission.function_url_public next-f1-session/FunctionURLAllowPublicAccess
terraform import aws_apigatewayv2_api.f1_next_session rswa7d9iui
terraform import aws_apigatewayv2_integration.f1_next_session_lambda rswa7d9iui/vngkyh6
terraform import aws_apigatewayv2_route.f1_next_session_get_root rswa7d9iui/t11l2qk
terraform import aws_apigatewayv2_stage.f1_next_session_default 'rswa7d9iui/$default'
terraform import aws_apigatewayv2_domain_name.f1_custom_domain f1.itchy7.com
terraform import aws_apigatewayv2_api_mapping.f1_custom_domain_root '99th9m/f1.itchy7.com'
terraform import aws_lambda_permission.apigateway_invoke_next_f1_session next-f1-session/AllowApiGatewayInvokeNextF1Session
terraform plan
```

If `terraform plan` shows drift you do not want, update `terraform.tfvars` (for env vars, layers, role ARN, etc.) and run `plan` again until clean.

## Normal workflow

```bash
cd /Users/scott/code/f1/infra
terraform plan
terraform apply
```

## Premier League template endpoint

This Terraform setup can create a second Lambda stack for a future Premier League watchface:

- Function name default: `next-pl-session`
- Handler: `lambda_pl_function.lambda_handler`
- Logic file: `/Users/scott/code/f1/src/f1watch/api/premier_league_handler.py`

The current handler returns a template payload with short cache headers. Replace its data-loading logic with real PL fixtures/standings when ready.

## CloudFront

CloudFront is currently lookup-only in Terraform (`data.aws_cloudfront_distribution.f1_api`) and not yet fully managed as a mutable Terraform resource.
