terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ECR Repository
resource "aws_ecr_repository" "apparel_fastapi_repo" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

# ECR Repository Policy
resource "aws_ecr_repository_policy" "apparel_fastapi_repo_policy" {
  repository = aws_ecr_repository.apparel_fastapi_repo.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPull"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
      }
    ]
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.function_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = aws_ecr_repository.apparel_fastapi_repo.arn
      }
    ]
  })
}

# 🔧 Build & Push Docker Image
resource "null_resource" "build_and_push_image" {
  provisioner "local-exec" {
    command = <<EOT
      cd ..
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.apparel_fastapi_repo.repository_url}
      docker build -t ${var.ecr_repository_name} .
      docker tag ${var.ecr_repository_name}:latest ${aws_ecr_repository.apparel_fastapi_repo.repository_url}:${var.image_tag}
      docker push ${aws_ecr_repository.apparel_fastapi_repo.repository_url}:${var.image_tag}
    EOT
  }

  triggers = {
    image_tag = var.image_tag
  }

  depends_on = [aws_ecr_repository.apparel_fastapi_repo]
}

# Lambda Function
resource "aws_lambda_function" "fastapi_lambda" {
  function_name = var.function_name
  role         = aws_iam_role.lambda_role.arn
  package_type = "Image"
  image_uri    = "${aws_ecr_repository.apparel_fastapi_repo.repository_url}:${var.image_tag}"
  timeout      = 30
  memory_size  = 512
  architectures = ["x86_64"]


  environment {
    variables = {
      GEMINI_API_KEY = var.gemini_api_key
      PINECONE_API_KEY = var.pinecone_api_key
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
    null_resource.build_and_push_image
  ]

  tags = var.tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 14
  tags              = var.tags
}

#############################################################API GATEWAY CONFIGURATION#############################################################

# API Gateway (HTTP API)
resource "aws_apigatewayv2_api" "lambda_api" {
  name          = "${var.function_name}-api"
  protocol_type = "HTTP"
  tags          = var.tags

   cors_configuration {
    allow_credentials = false
    expose_headers    = ["*"]
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    max_age          = 86400
  }
}

# API Gateway Integration with Lambda
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.lambda_api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.fastapi_lambda.arn
  integration_method = "POST"
}


resource "aws_apigatewayv2_route" "proxy_route" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# OPTIONS method for CORS preflight
resource "aws_apigatewayv2_route" "options_route" {
  api_id    = aws_apigatewayv2_api.lambda_api.id
  route_key = "OPTIONS /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.lambda_api.id
  name        = "$default"
  auto_deploy = true
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fastapi_lambda.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lambda_api.execution_arn}/*/*"
}


# # API Gateway v2 (HTTP API)
# resource "aws_apigatewayv2_api" "fastapi_api" {
#   name          = "${var.function_name}-api"
#   protocol_type = "HTTP"
#   description   = "API Gateway for FastAPI Lambda function"

#   cors_configuration {
#     allow_credentials = false
#     allow_headers     = ["*"]
#     allow_methods     = ["*"]
#     allow_origins     = ["*"]
#     max_age          = 86400
#   }

#   tags = var.tags
# }

# # API Gateway Stage
# resource "aws_apigatewayv2_stage" "fastapi_stage" {
#   api_id      = aws_apigatewayv2_api.fastapi_api.id
#   name        = var.stage_name
#   auto_deploy = true

#   access_log_settings {
#     destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
#     format = jsonencode({
#       requestId      = "$context.requestId"
#       ip            = "$context.identity.sourceIp"
#       requestTime   = "$context.requestTime"
#       httpMethod    = "$context.httpMethod"
#       routeKey      = "$context.routeKey"
#       status        = "$context.status"
#       protocol      = "$context.protocol"
#       responseLength = "$context.responseLength"
#     })
#   }

#   tags = var.tags
# }

# # CloudWatch Log Group for API Gateway
# resource "aws_cloudwatch_log_group" "api_gateway_logs" {
#   name              = "/aws/apigateway/${var.function_name}"
#   retention_in_days = 14
#   tags              = var.tags
# }

# # API Gateway Integration
# resource "aws_apigatewayv2_integration" "fastapi_integration" {
#   api_id             = aws_apigatewayv2_api.fastapi_api.id
#   integration_type   = "AWS_PROXY"
#   integration_method = "POST"
#   integration_uri    = aws_lambda_function.fastapi_lambda.invoke_arn
# }

# # API Gateway Route
# resource "aws_apigatewayv2_route" "fastapi_route" {
#   api_id    = aws_apigatewayv2_api.fastapi_api.id
#   route_key = "ANY /{proxy+}"
#   target    = "integrations/${aws_apigatewayv2_integration.fastapi_integration.id}"
# }

# # Lambda Permission for API Gateway
# resource "aws_lambda_permission" "api_gateway_lambda" {
#   statement_id  = "AllowExecutionFromAPIGateway"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.fastapi_lambda.function_name
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "${aws_apigatewayv2_api.fastapi_api.execution_arn}/*/*"
# }