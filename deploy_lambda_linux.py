#!/usr/bin/env python3
"""
Deploy Lambda with Linux-compatible dependencies
"""
import os
import subprocess
import tempfile
import zipfile
import shutil

def create_linux_compatible_package():
    """Create Lambda package with Linux-compatible wheels"""
    print("🐧 Creating Linux-compatible Lambda package...")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Working directory: {temp_dir}")
    
    try:
        # Install dependencies for Linux platform
        print("📦 Installing Linux-compatible dependencies...")
        subprocess.run([
            "pip", "install", 
            "--platform", "linux_x86_64",
            "--target", temp_dir,
            "--implementation", "cp",
            "--python-version", "3.11", 
            "--only-binary=:all:",
            "--upgrade",
            "-r", "requirements.txt"
        ], check=True)
        
        # Copy application files
        print("📋 Copying application files...")
        app_files = ["main.py", "database.py", "schemas.py", "lambda_function.py"]
        
        for file in app_files:
            if os.path.exists(file):
                shutil.copy2(file, temp_dir)
                print(f"  ✅ Copied {file}")
        
        # Create ZIP file
        zip_path = "lambda_deployment_linux.zip"
        print(f"🗜️  Creating ZIP file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_file.write(file_path, arc_name)
        
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"📊 Package size: {size_mb:.2f} MB")
        
        return zip_path
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating package: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir)

def update_lambda_function(zip_path):
    """Update Lambda function with new package"""
    print("🔄 Updating Lambda function...")
    
    try:
        result = subprocess.run([
            "aws", "lambda", "update-function-code",
            "--function-name", "duo-mapping-api", 
            "--zip-file", f"fileb://{zip_path}"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Lambda function updated successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to update Lambda function: {e}")
        print(f"Error output: {e.stderr}")
        return False

if __name__ == "__main__":
    print("🚀 Deploying Linux-compatible Lambda package")
    print("=" * 60)
    
    # Create the package
    zip_path = create_linux_compatible_package()
    
    if zip_path and os.path.exists(zip_path):
        print(f"✅ Package created: {zip_path}")
        
        # Update Lambda function
        if update_lambda_function(zip_path):
            print("\n🎉 Deployment successful!")
            print("🧪 Test endpoints:")
            print("   Root: https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/")
            print("   Health: https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/api/health")
            print("   Categories: https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/api/categories")
        else:
            print("\n❌ Deployment failed")
    else:
        print("❌ Failed to create deployment package")
