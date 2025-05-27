# terraform/terraform.tfvars
aws_region           = "us-east-1"
function_name        = "apperal-fastapi-openai-app"
ecr_repository_name  = "apperal-fastapi-openai-app"
stage_name          = "prod"

tags = {
  Environment   = "production"
  Project      = "apperal-fastapi-openai-app"
  ManagedBy    = "terraform"
  Team         = "devops"
}