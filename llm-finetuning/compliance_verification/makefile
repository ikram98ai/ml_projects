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
	docker run -p 8080:8080 -e OPENAI_API_KEY=${OPENAI_API_KEY} PINECONE_API_KEY=${PINECONE_API_KEY} apparel-lambda

deploy:
	@echo "Deploying to AWS Lambda..."
	cd terraform
	terraform init
	terraform plan -var="openai_api_key=${OPENAI_API_KEY}" -var="pinecone_api_key=${PINECONE_API_KEY}"
	terraform apply
	cd ..
	