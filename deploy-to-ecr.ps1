# PowerShell script for Windows - AWS ECR Deployment Script for Duo Mapping API
# Make sure you have AWS CLI configured with appropriate credentials

# Configuration
$AWS_ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
$AWS_REGION = "us-east-1"
$ECR_REPOSITORY = "duo-mapping-api"
$IMAGE_TAG = "latest"

Write-Host "AWS Account ID: $AWS_ACCOUNT_ID"
Write-Host "AWS Region: $AWS_REGION"
Write-Host "ECR Repository: $ECR_REPOSITORY"

# Create ECR repository if it doesn't exist
Write-Host "Creating ECR repository..."
try {
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION 2>$null
} catch {
    Write-Host "Repository already exists or error occurred"
}

# Get ECR login token
Write-Host "Logging into ECR..."
$loginCommand = aws ecr get-login-password --region $AWS_REGION
$loginCommand | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Build Docker image
Write-Host "Building Docker image..."
docker build -t "${ECR_REPOSITORY}:${IMAGE_TAG}" .

# Tag image for ECR
Write-Host "Tagging image for ECR..."
docker tag "${ECR_REPOSITORY}:${IMAGE_TAG}" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"

# Push image to ECR
Write-Host "Pushing image to ECR..."
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"

Write-Host "Image URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"
Write-Host "Deployment complete! Use this Image URI in App Runner."
