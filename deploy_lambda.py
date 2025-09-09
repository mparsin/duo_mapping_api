#!/usr/bin/env python3
"""
Deployment script for AWS Lambda + API Gateway
"""
import os
import json
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path

def create_lambda_package():
    """Create a deployment package for AWS Lambda"""
    print("🚀 Creating Lambda deployment package...")
    
    # Create temporary directory for the package
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Working directory: {temp_dir}")
    
    try:
        # Install dependencies to temp directory
        print("📦 Installing dependencies...")
        subprocess.run([
            "pip", "install", "-r", "requirements.txt", "-t", temp_dir
        ], check=True)
        
        # Copy application files
        print("📋 Copying application files...")
        app_files = [
            "main.py",
            "database.py", 
            "schemas.py",
            "lambda_function.py"
        ]
        
        for file in app_files:
            if os.path.exists(file):
                shutil.copy2(file, temp_dir)
                print(f"  ✅ Copied {file}")
            else:
                print(f"  ⚠️  Warning: {file} not found")
        
        # Create the ZIP file
        zip_path = "lambda_deployment.zip"
        print(f"🗜️  Creating ZIP file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_file.write(file_path, arc_name)
        
        # Get file size
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"📊 Package size: {size_mb:.2f} MB")
        
        if size_mb > 50:
            print("⚠️  Warning: Package size exceeds 50MB - consider using Lambda layers")
        
        return zip_path
        
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir)

def create_lambda_function(zip_path, function_name="duo-mapping-api"):
    """Create or update Lambda function"""
    print(f"🔧 Creating Lambda function: {function_name}")
    
    # Check if function exists
    try:
        result = subprocess.run([
            "aws", "lambda", "get-function", "--function-name", function_name
        ], capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            print("🔄 Function exists, updating...")
            # Update function code
            subprocess.run([
                "aws", "lambda", "update-function-code",
                "--function-name", function_name,
                "--zip-file", f"fileb://{zip_path}"
            ], check=True)
        else:
            print("✨ Creating new function...")
            # Create new function
            subprocess.run([
                "aws", "lambda", "create-function",
                "--function-name", function_name,
                "--runtime", "python3.11",
                "--role", f"arn:aws:iam::{get_account_id()}:role/lambda-execution-role",
                "--handler", "lambda_function.handler",
                "--zip-file", f"fileb://{zip_path}",
                "--timeout", "30",
                "--memory-size", "512",
                "--environment", json.dumps({
                    "Variables": {
                        "DATABASE_URL": "postgresql://postgres:postgres@duo-mapping.cefhyz1bpgbv.us-east-2.rds.amazonaws.com:5432/duo-mapping-db"
                    }
                })
            ], check=True)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating Lambda function: {e}")
        return False
    
    print("✅ Lambda function ready!")
    return True

def get_account_id():
    """Get AWS account ID"""
    result = subprocess.run([
        "aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"
    ], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def create_api_gateway(function_name="duo-mapping-api"):
    """Create API Gateway for the Lambda function"""
    print("🌐 Setting up API Gateway...")
    
    try:
        # This would require additional AWS CLI commands
        # For now, we'll provide manual instructions
        print("📋 Manual API Gateway setup required:")
        print("1. Go to AWS API Gateway console")
        print("2. Create new REST API")
        print(f"3. Create proxy resource with Lambda integration to: {function_name}")
        print("4. Deploy API to get HTTPS endpoint")
        
    except Exception as e:
        print(f"❌ Error setting up API Gateway: {e}")

if __name__ == "__main__":
    print("🎯 AWS Lambda + API Gateway Deployment")
    print("=" * 50)
    
    # Create package
    zip_path = create_lambda_package()
    
    if zip_path and os.path.exists(zip_path):
        print(f"✅ Package created: {zip_path}")
        
        # Deploy to Lambda
        if create_lambda_function(zip_path):
            create_api_gateway()
        
    else:
        print("❌ Failed to create deployment package")
