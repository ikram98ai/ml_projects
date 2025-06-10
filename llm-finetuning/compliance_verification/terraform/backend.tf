# terraform/backend.tf
terraform {
  backend "s3" {
    bucket         = "terraform-state-20250610"  # Replace with your S3 bucket
    key            = "apparel-fastapi-lambda/terraform.tfstate"
    region         = var.aws_region
    encrypt        = true
    dynamodb_table = "terraform-state-lock"         # Replace with your DynamoDB table
  }
}


