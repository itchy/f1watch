output "lambda_function_name" {
  value = aws_lambda_function.next_f1_session.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.next_f1_session.arn
}

output "lambda_function_url" {
  value = aws_lambda_function_url.next_f1_session.function_url
}

output "cloudfront_domain_name" {
  value = data.aws_cloudfront_distribution.f1_api.domain_name
}

output "cloudfront_aliases" {
  value = data.aws_cloudfront_distribution.f1_api.aliases
}
