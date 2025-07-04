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
        Action = [
          "lambda:InvokeFunctionUrl",
          "lambda:GetFunctionUrlConfig"  # Required for URL management
        ]
        Effect   = "Allow"
        Resource = "*"
      },
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
  timeout      = 90
  memory_size  = 512
  architectures = ["x86_64"]


  environment {
    variables = {
      OPENAI_API_KEY = var.openai_api_key
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



# Lambda Function URL
resource "aws_lambda_function_url" "lambda_url" {
  function_name      = aws_lambda_function.fastapi_lambda.function_name
  authorization_type = "NONE"  # Use "AWS_IAM" for IAM authentication

  cors {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["*"]
    allow_origins     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}