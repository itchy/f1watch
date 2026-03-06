locals {
  lambda_zip_path = "${abspath(path.module)}/build/${var.lambda_function_name}.zip"
  pl_lambda_zip_path = "${abspath(path.module)}/build/${var.pl_lambda_function_name}.zip"
  lambda_sources = concat(
    ["${path.module}/../lambda_function.py", "${path.module}/../lambda_pl_function.py"],
    [for file in fileset("${path.module}/../src", "**") : "${path.module}/../src/${file}"]
  )
  lambda_source_hash = sha256(join("", [for file in local.lambda_sources : filesha256(file)]))
}

resource "terraform_data" "package_lambda" {
  triggers_replace = [
    local.lambda_source_hash,
  ]

  provisioner "local-exec" {
    command = "mkdir -p ${abspath(path.module)}/build && rm -f ${local.lambda_zip_path} && cd ${abspath(path.module)}/.. && zip -r ${local.lambda_zip_path} lambda_function.py src >/dev/null"
  }
}

resource "terraform_data" "package_pl_lambda" {
  count = var.enable_premier_league_lambda ? 1 : 0

  triggers_replace = [
    local.lambda_source_hash,
  ]

  provisioner "local-exec" {
    command = "mkdir -p ${abspath(path.module)}/build && rm -f ${local.pl_lambda_zip_path} && cd ${abspath(path.module)}/.. && zip -r ${local.pl_lambda_zip_path} lambda_pl_function.py src >/dev/null"
  }
}

resource "aws_lambda_function" "next_f1_session" {
  function_name = var.lambda_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.lambda_handler
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  layers        = var.lambda_layers

  filename         = local.lambda_zip_path
  source_code_hash = base64encode(local.lambda_source_hash)

  environment {
    variables = var.lambda_environment
  }

  depends_on = [
    terraform_data.package_lambda,
  ]
}

resource "aws_lambda_function_url" "next_f1_session" {
  function_name      = aws_lambda_function.next_f1_session.function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"
}

resource "aws_lambda_permission" "function_url_public" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.next_f1_session.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function" "premier_league" {
  count = var.enable_premier_league_lambda ? 1 : 0

  function_name = var.pl_lambda_function_name
  role          = var.lambda_role_arn
  runtime       = var.lambda_runtime
  handler       = var.pl_lambda_handler
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  layers        = var.lambda_layers

  filename         = local.pl_lambda_zip_path
  source_code_hash = base64encode(local.lambda_source_hash)

  environment {
    variables = var.pl_lambda_environment
  }

  depends_on = [
    terraform_data.package_pl_lambda,
  ]
}

resource "aws_lambda_function_url" "premier_league" {
  count = var.enable_premier_league_lambda ? 1 : 0

  function_name      = aws_lambda_function.premier_league[0].function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"
}

resource "aws_lambda_permission" "premier_league_function_url_public" {
  count = var.enable_premier_league_lambda ? 1 : 0

  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.premier_league[0].function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
