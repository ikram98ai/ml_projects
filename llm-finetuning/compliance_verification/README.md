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
│   ├── main.py
│   └── rag.py
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── .dockerignore
├── .env
├── .gitignore
├── Dockerfile
├── main.py
├── makefile
├── README.md
└── requirements.txt
```

## Setup Instructions

### 1. Prerequisites
- AWS Account with appropriate permissions
- GitHub repository
- OpenAI API key
- Pinecone API key

### 2. AWS Permissions Required
Your AWS IAM user/role needs these permissions:
- ECR: Full access to create and manage repositories
- Lambda: Full access to create and manage functions
- IAM: Create and manage roles and policies
- API Gateway: Full access
- CloudWatch: Create and manage log groups

### 3. GitHub Secrets Setup
Add these secrets to your GitHub repository:
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `OPENAI_API_KEY`: Your OpenAI API key
- `PINECONE_API_KEY`: Your Pinecone API key


### 4. Initial Terraform Setup
```bash
make deploy
```

### 5. Deploy via GitHub Actions
1. Push your code to the `main` branch
2. GitHub Actions will automatically:
   - Run tests
   - Build Docker image
   - Push to ECR
   - Deploy infrastructure with Terraform
   - Update Lambda function
   - Clean up old images

### Infrastructure
- **AWS Lambda**: Serverless compute with container support
- **API Gateway**: HTTP API for routing requests
- **ECR**: Container registry for Docker images
- **CloudWatch**: Logging and monitoring
- **IAM**: Least privilege access control

### CI/CD Pipeline
- **Automated Testing**: Run tests on every push/PR
- **Docker Build**: Multi-stage builds for optimization
- **Infrastructure as Code**: Terraform for resource management
- **Automated Deployment**: Deploy on merge to main
- **Image Cleanup**: Remove old ECR images to save costs


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

### Docker Testing
```bash
make docker
```

## Monitoring and Troubleshooting

### CloudWatch Logs
- Lambda logs: `/aws/lambda/apparel_verification_app`
- API Gateway logs: `/aws/apigateway/apparel_verification_app`

### Common Issues
1. **Cold starts**: First request may be slower
2. **Memory limits**: Adjust Lambda memory if needed
3. **Timeout**: Increase Lambda timeout for longer operations
4. **API limits**: Monitor OpenAI API usage and rate limits

## Cost Optimization
- Lambda: Pay only for requests and compute time
- API Gateway: Pay per million requests
- ECR: Storage costs for container images
- CloudWatch: Log retention set to 14 days

## Security Best Practices
- OpenAI and Pinecone API keys stored as environment variable
- IAM roles with minimal permissions
- CORS configured for API Gateway
- Container scanning enabled in ECR
- No hardcoded secrets in code

## Scaling Considerations
- Lambda automatically scales to handle requests
- API Gateway handles high traffic
- Consider Lambda reserved concurrency for predictable workloads
- Monitor costs and set billing alerts