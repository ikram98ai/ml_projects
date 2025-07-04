# FastAPI + OpenAI AWS Lambda CI/CD Pipeline

## Project Structure
```
apperals_verification/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── ai/
│   ├── data/
│   ├── ai_agents.py
│   └── rag.py
├── terraform/
│   ├── main.tf
│   ├── backend.tf
│   ├── var.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── .dockerignore
├── .env
├── .gitignore
├── Dockerfile
├── main.py
├── utils.py
├── makefile
├── README.md
└── requirements.txt
```

## Deployment

This project uses Terraform for infrastructure provisioning and GitHub Actions for automated CI/CD to AWS Lambda.

### 1. Prerequisites

*   **AWS Account**: With programmatic access (Access Key ID and Secret Access Key).
*   **GitHub Repository**: Where this project's code is hosted.
*   **OpenAI API Key**: For the application's functionality.
*   **Pinecone API Key**: For the application's functionality.

### 2. AWS Permissions Required

Your AWS IAM user/role needs the following permissions:

*   **ECR**: `ecr:*` (to create repositories, push images)
*   **Lambda**: `lambda:*` (to create functions, update code, manage function URLs)
*   **IAM**: `iam:*` (to create roles and policies for Lambda)
*   **S3**: `s3:*` (to create and manage the Terraform state bucket)
*   **DynamoDB**: `dynamodb:*` (to create and manage the Terraform state lock table)
*   **CloudWatch**: `logs:*` (to create and manage log groups for Lambda)

### 3. GitHub Secrets Setup

Add the following secrets to your GitHub repository (Settings > Secrets and variables > Actions > New repository secret):

*   `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID.
*   `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key.
*   `AWS_REGION`: The AWS region where you want to deploy (e.g., `us-east-1`).
*   `OPENAI_API_KEY`: Your OpenAI API Key.
*   `PINECONE_API_KEY`: Your Pinecone API Key.

### 4. Initial Terraform Backend Setup

Before the first deployment, you need to set up the S3 bucket for Terraform state and a DynamoDB table for state locking. This is a one-time setup.

```bash
make tf_backend
```
*Note: The `make tf_backend` command creates an S3 bucket named `terraform-state-20250610` and a DynamoDB table named `terraform-state-lock`. If these names are already in use, you will need to modify the `makefile` and `terraform/backend.tf` to use unique names.*

### 5. Deployment

#### A. Automated Deployment via GitHub Actions

The project is configured for continuous deployment. Any push to the `main` branch will automatically trigger the GitHub Actions workflow:

1.  **Checkout code**: Fetches the latest code.
2.  **Configure AWS credentials**: Uses the GitHub secrets to set up AWS access.
3.  **Setup Terraform**: Installs Terraform.
4.  **Terraform Init**: Initializes the Terraform working directory, connecting to the S3 backend.
5.  **Terraform Apply**: Applies the Terraform configuration, which includes:
    *   Building the Docker image.
    *   Pushing the Docker image to AWS ECR.
    *   Creating/updating the AWS Lambda function.
    *   Configuring the Lambda Function URL.
    *   Setting environment variables (`OPENAI_API_KEY`, `PINECONE_API_KEY`) for the Lambda function.

#### B. Manual Deployment (for testing or specific scenarios)

You can also trigger a deployment manually using the `makefile` after setting up your AWS credentials locally.

```bash
# Ensure your AWS CLI is configured with credentials and default region
# export OPENAI_API_KEY="your_openai_api_key"
# export PINECONE_API_KEY="your_pinecone_api_key"
make deploy
```
This command will:
1.  Initialize Terraform.
2.  Show a plan of changes.
3.  Apply the Terraform configuration, building and pushing the Docker image, and deploying the Lambda function.

### 6. Destroying AWS Resources

To destroy all AWS resources provisioned by Terraform:

```bash
# Ensure your AWS CLI is configured with credentials and default region
# export OPENAI_API_KEY="your_openai_api_key"
# export PINECONE_API_KEY="your_pinecone_api_key"
make destroy
```
*Use with caution, as this will permanently delete all associated resources.*

### Infrastructure

*   **AWS Lambda**: Serverless compute with container image support.
*   **AWS ECR**: Container registry for Docker images.
*   **AWS IAM**: Roles and policies for secure access.
*   **AWS S3**: For Terraform state management.
*   **AWS DynamoDB**: For Terraform state locking.
*   **AWS CloudWatch**: For logging and monitoring Lambda functions.
*   **AWS Lambda Function URL**: Provides a dedicated HTTP endpoint for the Lambda function.

### CI/CD Pipeline

*   **GitHub Actions**: Automates the build, push, and deploy process.
*   **Docker Build**: Creates a container image for the Lambda function.
*   **Terraform**: Manages infrastructure as code.
*   **Automated Deployment**: Triggered on pushes to the `main` branch.


## API Endpoints

The application exposes the following API endpoints:

### `POST /compliance_flow`

*   **Description**: Performs compliance verification on uploaded apparel design images using a direct flow. This endpoint integrates image analysis, rule retrieval, and compliance evaluation to determine if a design adheres to general and licensing rules.
*   **Input**: `images` (List[UploadFile]) - A list of up to two image files (PNG, JPG, JPEG) for analysis.
*   **Output**: A JSON object containing the `compliance_status` (e.g., "Compliant", "Non-compliant") and `violation_reason` (a brief explanation if non-compliant).
*   **Example Usage**:
    ```bash
    curl -X POST "http://localhost:8000/compliance_flow" \
      -H "accept: application/json" \
      -H "Content-Type: multipart/form-data" \
      -F "images=@./path/to/your/image1.png" \
      -F "images=@./path/to/your/image2.jpeg"
    ```

### `POST /compliance_agent`

*   **Description**: Performs compliance verification using an AI agent-based approach. This endpoint leverages a more sophisticated agentic workflow for compliance checking, allowing for more dynamic rule application and reasoning.
*   **Input**: `images` (List[UploadFile]) - A list of up to two image files (PNG, JPG, JPEG) for analysis.
*   **Output**: A JSON object containing the `compliance_status` and `violation_reason`.
*   **Example Usage**:
    ```bash
    curl -X POST "http://localhost:8000/compliance_agent" \
      -H "accept: application/json" \
      -H "Content-Type: multipart/form-data" \
      -F "images=@./path/to/your/image1.png"
    ```

### `POST /trademark`

*   **Description**: Detects trademarks (e.g., Greek letters, collegiate marks) within uploaded apparel design images.
*   **Input**: `images` (List[UploadFile]) - A list of up to two image files (PNG, JPG, JPEG) for analysis.
*   **Output**: A JSON object indicating `trademark_detected` ("Yes" or "No") and the `organization` name if a trademark is found.
*   **Example Usage**:
    ```bash
    curl -X POST "http://localhost:8000/trademark" \
      -H "accept: application/json" \
      -H "Content-Type: multipart/form-data" \
      -F "images=@./path/to/your/image.png"
    ```

### `POST /upsert`

*   **Description**: Upserts (updates or inserts) new licensing rules or documents into the Pinecone vector database. This allows for dynamic updating of the knowledge base used by the compliance agents.
*   **Input**: `docs` (List[UploadFile]) - A list of `.docx` files containing the rules to be upserted.
*   **Output**: A JSON object confirming the success of the upsert operation.
*   **Example Usage**:
    ```bash
    curl -X POST "http://localhost:8000/upsert" \
      -H "accept: application/json" \
      -H "Content-Type: multipart/form-data" \
      -F "docs=@./path/to/your/rules.docx"
    ```

## Local Development

### Running Locally
```bash
# Install dependencies
make install

# Set environment variable
export OPENAI_API_KEY=your_key_here

# Run the application
make dev
```

### Initial Data Upsert
To upsert initial RAG (Retrieval Augmented Generation) data to the Pinecone database, use the following command:
```bash
make upsert_rag
```
This command runs the `ai/rag.py` script with the `--upsert` flag, which is responsible for populating the vector database with necessary information for the AI models.

### Docker Testing
```bash
make docker
```

## Monitoring and Troubleshooting

### CloudWatch Logs
- Lambda logs: `/aws/lambda/apparel_verification_app`
