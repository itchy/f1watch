variable "aws_region" {
  description = "AWS region for Lambda and related resources."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name used by Terraform."
  type        = string
  default     = "f1-sso"
}

variable "lambda_function_name" {
  description = "Existing Lambda function name."
  type        = string
  default     = "next-f1-session"
}

variable "lambda_role_arn" {
  description = "IAM role ARN already used by Lambda."
  type        = string
  default     = "arn:aws:iam::373892137535:role/service-role/next-f1-session-role-m81fwq00"
}

variable "lambda_handler" {
  description = "Lambda handler entrypoint."
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "lambda_runtime" {
  description = "Lambda runtime."
  type        = string
  default     = "python3.13"
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 10
}

variable "lambda_memory_size" {
  description = "Lambda memory in MB."
  type        = number
  default     = 128
}

variable "lambda_layers" {
  description = "Lambda layer ARNs."
  type        = list(string)
  default = [
    "arn:aws:lambda:us-east-1:373892137535:layer:rfc3339:1",
  ]
}

variable "lambda_environment" {
  description = "Lambda environment variables."
  type        = map(string)
  default = {
    DATA_BUCKET = "f1-data-00000000"
  }
}

variable "cloudfront_distribution_id" {
  description = "Existing CloudFront distribution ID for the API domain."
  type        = string
  default     = "E5W6U8ERMNWNJ"
}

variable "api_name" {
  description = "API Gateway HTTP API name for F1 payload."
  type        = string
  default     = "f1-next-session-api"
}

variable "api_custom_domain_name" {
  description = "API Gateway custom domain used by CloudFront origin path."
  type        = string
  default     = "f1.itchy7.com"
}

variable "api_custom_domain_certificate_arn" {
  description = "ACM certificate ARN for API Gateway custom domain."
  type        = string
  default     = "arn:aws:acm:us-east-1:373892137535:certificate/20d94070-f29c-4162-8ea1-480dc8e93438"
}

variable "enable_scrape_publish_lambda" {
  description = "Create scrape/publish Lambda and hourly EventBridge trigger."
  type        = bool
  default     = true
}

variable "scrape_lambda_function_name" {
  description = "Scrape/publish Lambda function name."
  type        = string
  default     = "scrape-f1-data"
}

variable "scrape_lambda_handler" {
  description = "Scrape/publish Lambda handler entrypoint."
  type        = string
  default     = "lambda_scrape_function.lambda_handler"
}

variable "scrape_lambda_timeout" {
  description = "Scrape/publish Lambda timeout in seconds."
  type        = number
  default     = 180
}

variable "scrape_lambda_memory_size" {
  description = "Scrape/publish Lambda memory in MB."
  type        = number
  default     = 512
}

variable "scrape_lambda_environment" {
  description = "Scrape/publish Lambda environment variables."
  type        = map(string)
  default = {
    DATA_BUCKET = "f1-data-00000000"
    F1_YEAR     = "2026"
  }
}

variable "scrape_schedule_expression" {
  description = "EventBridge schedule expression for scrape/publish Lambda."
  type        = string
  default     = "rate(1 hour)"
}
