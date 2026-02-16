#!/bin/bash

# Deploy OHLCV Ingestion Lambda to AWS
# Usage: ./deploy.sh <aws-account-id> <region> <lambda-function-name>

set -e

# Check arguments
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <aws-account-id> <region> <lambda-function-name>"
    echo "Example: $0 123456789012 us-east-2 ohlcv-ingestion"
    exit 1
fi

AWS_ACCOUNT_ID=$1
AWS_REGION=$2
LAMBDA_FUNCTION_NAME=$3
ECR_REPO_NAME="bamboo-analytics/data-platform"
IMAGE_TAG="latest"

echo "=========================================="
echo "AWS Lambda Deployment Script"
echo "=========================================="
echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "Region: ${AWS_REGION}"
echo "Lambda Function: ${LAMBDA_FUNCTION_NAME}"
echo "ECR Repository: ${ECR_REPO_NAME}"
echo "=========================================="

# Step 1: Create ECR repository if it doesn't exist
echo ""
echo "Step 1: Creating ECR repository..."
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} 2>/dev/null || \
    aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${AWS_REGION}

# Step 2: Authenticate Docker to ECR
echo ""
echo "Step 2: Authenticating Docker to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Step 3: Build Docker image
echo ""
echo "Step 3: Building Docker image..."
docker build -t ${ECR_REPO_NAME}:${IMAGE_TAG} .

# Step 4: Tag Docker image for ECR
echo ""
echo "Step 4: Tagging Docker image..."
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Step 5: Push Docker image to ECR
echo ""
echo "Step 5: Pushing Docker image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Step 6: Update or Create Lambda function
echo ""
echo "Step 6: Checking if Lambda function exists..."
IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}"

if aws lambda get-function --function-name ${LAMBDA_FUNCTION_NAME} --region ${AWS_REGION} 2>/dev/null; then
    echo "Lambda function exists. Updating code..."
    aws lambda update-function-code \
        --function-name ${LAMBDA_FUNCTION_NAME} \
        --image-uri ${IMAGE_URI} \
        --region ${AWS_REGION}
    
    echo "Waiting for update to complete..."
    aws lambda wait function-updated --function-name ${LAMBDA_FUNCTION_NAME} --region ${AWS_REGION}
    
    echo "Lambda function updated successfully!"
else
    echo "Lambda function does not exist. Please create it manually with the following command:"
    echo ""
    echo "aws lambda create-function \\"
    echo "  --function-name ${LAMBDA_FUNCTION_NAME} \\"
    echo "  --package-type Image \\"
    echo "  --code ImageUri=${IMAGE_URI} \\"
    echo "  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-execution-role \\"
    echo "  --timeout 300 \\"
    echo "  --memory-size 512 \\"
    echo "  --environment Variables='{MY_AWS_BUCKET_NAME=bamboo-analytics-data-platform}' \\"
    echo "  --region ${AWS_REGION}"
    echo ""
    echo "Make sure to:"
    echo "1. Create an IAM role with S3 write permissions and Lambda execution permissions"
    echo "2. Update the role ARN in the command above"
    echo "3. Set appropriate environment variables (MY_AWS_BUCKET_NAME, etc.)"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Image URI: ${IMAGE_URI}"
echo ""
echo "To test the Lambda function, use:"
echo "aws lambda invoke \\"
echo "  --function-name ${LAMBDA_FUNCTION_NAME} \\"
echo "  --payload '{\"symbols\": [\"AAPL\", \"GOOGL\"]}' \\"
echo "  --region ${AWS_REGION} \\"
echo "  response.json"
echo ""
echo "To create an EventBridge schedule:"
echo "1. Go to EventBridge console"
echo "2. Create a new rule with schedule expression (e.g., cron(0 9 * * ? *))"
echo "3. Add target: Lambda function ${LAMBDA_FUNCTION_NAME}"
echo "4. Configure constant JSON input with symbols list"
