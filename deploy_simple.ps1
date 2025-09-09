# Simple PowerShell deployment script for AWS Lambda
Write-Host "🚀 Deploying Duo Mapping API to AWS Lambda" -ForegroundColor Green

# Configuration
$FunctionName = "duo-mapping-api"
$ZipFile = "lambda_deployment.zip"
$Runtime = "python3.11"
$Handler = "lambda_function.handler"
$Timeout = 30
$MemorySize = 512

# Get AWS Account ID
Write-Host "📋 Getting AWS Account ID..." -ForegroundColor Yellow
$AccountId = aws sts get-caller-identity --query Account --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to get AWS Account ID. Make sure AWS CLI is configured." -ForegroundColor Red
    exit 1
}

Write-Host "Account ID: $AccountId" -ForegroundColor Cyan

# Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow

# Create temp directory
$TempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
Write-Host "Working directory: $TempDir" -ForegroundColor Cyan

try {
    # Install dependencies
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt -t $TempDir
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
    
    # Copy application files
    Write-Host "Copying application files..." -ForegroundColor Yellow
    $AppFiles = @("main.py", "database.py", "schemas.py", "lambda_function.py")
    
    foreach ($File in $AppFiles) {
        if (Test-Path $File) {
            Copy-Item $File -Destination $TempDir
            Write-Host "  ✅ Copied $File" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Warning: $File not found" -ForegroundColor Yellow
        }
    }
    
    # Create ZIP file
    Write-Host "Creating ZIP package..." -ForegroundColor Yellow
    Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -Force
    
    $SizeMB = (Get-Item $ZipFile).Length / 1MB
    Write-Host "Package size: $([math]::Round($SizeMB, 2)) MB" -ForegroundColor Cyan
    
    if ($SizeMB -gt 50) {
        Write-Host "⚠️  Warning: Package size exceeds 50MB" -ForegroundColor Yellow
    }
    
} finally {
    # Cleanup
    Remove-Item $TempDir -Recurse -Force
}

# Check if Lambda function exists
Write-Host "🔍 Checking if Lambda function exists..." -ForegroundColor Yellow
$FunctionExists = $false

aws lambda get-function --function-name $FunctionName 2>$null
if ($LASTEXITCODE -eq 0) {
    $FunctionExists = $true
    Write-Host "Function exists - will update" -ForegroundColor Cyan
} else {
    Write-Host "Function does not exist - will create" -ForegroundColor Cyan
}

# Deploy function
if ($FunctionExists) {
    Write-Host "🔄 Updating Lambda function..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile"
} else {
    Write-Host "✨ Creating Lambda function..." -ForegroundColor Yellow
    
    # Note: You may need to create an execution role first
    $RoleArn = "arn:aws:iam::${AccountId}:role/lambda-execution-role"
    
    aws lambda create-function `
        --function-name $FunctionName `
        --runtime $Runtime `
        --role $RoleArn `
        --handler $Handler `
        --zip-file "fileb://$ZipFile" `
        --timeout $Timeout `
        --memory-size $MemorySize `
        --environment "Variables={DATABASE_URL=postgresql://postgres:postgres@duo-mapping.cefhyz1bpgbv.us-east-2.rds.amazonaws.com:5432/duo-mapping-db}"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Lambda function deployed successfully!" -ForegroundColor Green
    
    # Get function info
    Write-Host "📊 Function details:" -ForegroundColor Yellow
    aws lambda get-function --function-name $FunctionName --query "Configuration.[FunctionName,Runtime,MemorySize,Timeout]" --output table
    
    Write-Host ""
    Write-Host "🌐 Next steps:" -ForegroundColor Green
    Write-Host "1. Create API Gateway in AWS Console" -ForegroundColor White
    Write-Host "2. Create REST API with Lambda proxy integration" -ForegroundColor White
    Write-Host "3. Point integration to function: $FunctionName" -ForegroundColor White
    Write-Host "4. Deploy API to get HTTPS endpoint" -ForegroundColor White
    
} else {
    Write-Host "❌ Failed to deploy Lambda function" -ForegroundColor Red
}

# Cleanup
if (Test-Path $ZipFile) {
    Write-Host "🧹 Cleaning up deployment package..." -ForegroundColor Yellow
    # Remove-Item $ZipFile
    Write-Host "Deployment package saved as: $ZipFile" -ForegroundColor Cyan
}
