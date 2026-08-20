output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.fastapi_lambda.arn
}
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.fastapi_lambda.function_name
}

output "lambda_function_url" {
  value = aws_lambda_function_url.lambda_url.function_url
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.apparel_fastapi_repo.repository_url
}