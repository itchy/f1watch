output "lambda_function_name" {
  value = aws_lambda_function.next_f1_session.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.next_f1_session.arn
}

output "lambda_function_url" {
  value = aws_lambda_function_url.next_f1_session.function_url
}

output "api_gateway_id" {
  value = aws_apigatewayv2_api.f1_next_session.id
}

output "api_gateway_endpoint" {
  value = aws_apigatewayv2_api.f1_next_session.api_endpoint
}

output "api_gateway_custom_domain_target" {
  value = aws_apigatewayv2_domain_name.f1_custom_domain.domain_name_configuration[0].target_domain_name
}

output "cloudfront_domain_name" {
  value = data.aws_cloudfront_distribution.f1_api.domain_name
}

output "cloudfront_aliases" {
  value = data.aws_cloudfront_distribution.f1_api.aliases
}

output "scrape_lambda_function_name" {
  value = try(one(aws_lambda_function.scrape_publish[*].function_name), null)
}

output "scrape_lambda_function_arn" {
  value = try(one(aws_lambda_function.scrape_publish[*].arn), null)
}

output "scrape_lambda_schedule_rule" {
  value = try(one(aws_cloudwatch_event_rule.scrape_publish_hourly[*].name), null)
}
