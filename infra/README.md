# Terraform for F1 Watch

This directory adds Infrastructure as Code for the existing Lambda API first, without forcing a rebuild of CloudFront/DNS on day one.

## What is managed now

- Lambda function: `next-f1-session`
- Lambda Function URL
- Public Function URL permission (`FunctionURLAllowPublicAccess`)
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

## CloudFront and DNS

CloudFront (`f1.itchy7.com`) is intentionally read-only in this first pass, to avoid accidental replacement while bootstrapping IaC. After this Lambda layer is stable in Terraform state, we can add CloudFront and DNS resources and import them in a second pass.
