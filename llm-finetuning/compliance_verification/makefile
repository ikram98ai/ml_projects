include .env

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

dev: 
	@echo "Running the application..."
	uvicorn main:app --reload

docker: 
	@echo "Building Docker image..."
	docker build -t apparel-lambda .

	@echo "Running Docker container..."
	docker run -p 8080:8080 -e GEMINI_API_KEY=${GEMINI_API_KEY} -e -var="openai_api_key=${OPENAI_API_KEY}" -e PINECONE_API_KEY=${PINECONE_API_KEY} apparel-lambda

tf_backend:
	@echo "Create S3 bucket for Terraform state"
	aws s3 mb s3://terraform-state-20250610

	@echo "Create DynamoDB table for state locking"
	aws dynamodb create-table \
		--table-name terraform-state-lock \
		--attribute-definitions AttributeName=LockID,AttributeType=S \
		--key-schema AttributeName=LockID,KeyType=HASH \
		--provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5


deploy:
	@echo "Deploying to AWS Lambda..."
	terraform -chdir=terraform init
	terraform -chdir=terraform plan -var="gemini_api_key=${GEMINI_API_KEY}" -var="openai_api_key=${OPENAI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"
	terraform -chdir=terraform apply -var="gemini_api_key=${GEMINI_API_KEY}" -var="openai_api_key=${OPENAI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"
	
destroy:
	@echo "Destroying AWS resources..."
	terraform -chdir=terraform destroy -var="gemini_api_key=${GEMINI_API_KEY}" -var="openai_api_key=${OPENAI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"