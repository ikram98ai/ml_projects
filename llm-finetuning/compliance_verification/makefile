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
	docker run -p 8080:8080 -e GEMINI_API_KEY=${GEMINI_API_KEY} -e PINECONE_API_KEY=${PINECONE_API_KEY} apparel-lambda

deploy:
	@echo "Deploying to AWS Lambda..."
	terraform -chdir=terraform init
	terraform -chdir=terraform plan -var="gemini_api_key=${GEMINI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"
	terraform -chdir=terraform apply -var="gemini_api_key=${GEMINI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"
	
destroy:
	@echo "Destroying AWS resources..."
	terraform -chdir=terraform destroy -var="gemini_api_key=${GEMINI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"