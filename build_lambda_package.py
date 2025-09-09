#!/usr/bin/env python3
"""
Build Lambda package using Docker to ensure Linux compatibility
"""
import os
import subprocess
import zipfile
import tempfile
import shutil

def build_with_docker():
    """Build Lambda package using Docker for Linux compatibility"""
    print("🐳 Building Lambda package with Docker (Linux compatibility)...")
    
    # Create a simple Dockerfile for building
    dockerfile_content = """
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt -t /var/task/

# Copy application files
COPY main.py database.py schemas.py lambda_function.py /var/task/

# Create the package
WORKDIR /var/task
RUN zip -r /tmp/lambda_package.zip .

CMD ["echo", "Package built"]
"""
    
    # Write Dockerfile
    with open("Dockerfile.lambda", "w") as f:
        f.write(dockerfile_content)
    
    try:
        # Build Docker image
        print("📦 Building Docker image...")
        subprocess.run([
            "docker", "build", "-f", "Dockerfile.lambda", "-t", "lambda-builder", "."
        ], check=True)
        
        # Run container and copy package
        print("🏃 Running container to build package...")
        subprocess.run([
            "docker", "run", "--name", "lambda-build-container", "lambda-builder"
        ], check=True)
        
        # Copy package from container
        print("📋 Copying package from container...")
        subprocess.run([
            "docker", "cp", "lambda-build-container:/tmp/lambda_package.zip", "./lambda_package_linux.zip"
        ], check=True)
        
        # Cleanup
        subprocess.run(["docker", "rm", "lambda-build-container"], check=False)
        subprocess.run(["docker", "rmi", "lambda-builder"], check=False)
        os.remove("Dockerfile.lambda")
        
        return "lambda_package_linux.zip"
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker build failed: {e}")
        return None

def update_lambda_function(zip_file):
    """Update the Lambda function with new package"""
    print("🔄 Updating Lambda function...")
    
    try:
        subprocess.run([
            "aws", "lambda", "update-function-code",
            "--function-name", "duo-mapping-api",
            "--zip-file", f"fileb://{zip_file}"
        ], check=True)
        
        print("✅ Lambda function updated successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update Lambda function: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Building Linux-compatible Lambda package")
    print("=" * 50)
    
    # Try Docker build first
    zip_file = build_with_docker()
    
    if zip_file and os.path.exists(zip_file):
        print(f"✅ Package created: {zip_file}")
        
        if update_lambda_function(zip_file):
            print("\n🎉 Lambda function updated with Linux-compatible package!")
            print("🧪 Test your API at: https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/")
        else:
            print("\n❌ Failed to update Lambda function")
    else:
        print("❌ Failed to create package")
