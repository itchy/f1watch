resource "aws_apigatewayv2_api" "f1_next_session" {
  name                         = var.api_name
  protocol_type                = "HTTP"
  disable_execute_api_endpoint = false
}

resource "aws_apigatewayv2_integration" "f1_next_session_lambda" {
  api_id                 = aws_apigatewayv2_api.f1_next_session.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.next_f1_session.arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

resource "aws_apigatewayv2_route" "f1_next_session_get_root" {
  api_id    = aws_apigatewayv2_api.f1_next_session.id
  route_key = "GET /"
  target    = "integrations/${aws_apigatewayv2_integration.f1_next_session_lambda.id}"
}

resource "aws_apigatewayv2_stage" "f1_next_session_default" {
  api_id      = aws_apigatewayv2_api.f1_next_session.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigateway_invoke_next_f1_session" {
  statement_id  = "AllowApiGatewayInvokeNextF1Session"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.next_f1_session.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.f1_next_session.execution_arn}/*/*"
}

resource "aws_apigatewayv2_domain_name" "f1_custom_domain" {
  domain_name = var.api_custom_domain_name

  domain_name_configuration {
    certificate_arn = var.api_custom_domain_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "f1_custom_domain_root" {
  api_id      = aws_apigatewayv2_api.f1_next_session.id
  domain_name = aws_apigatewayv2_domain_name.f1_custom_domain.id
  stage       = aws_apigatewayv2_stage.f1_next_session_default.id
}

