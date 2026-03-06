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
  default     = 3
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
