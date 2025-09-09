#!/usr/bin/env python3
"""
Deploy simple test Lambda function
"""
import os
import subprocess
import tempfile
import zipfile
import shutil

def create_simple_package():
    """Create a simple Lambda package for testing"""
    print("🧪 Creating simple test Lambda package...")
    
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Working directory: {temp_dir}")
    
    try:
        # Install minimal dependencies
        print("📦 Installing minimal dependencies...")
        subprocess.run([
            "pip", "install",
            "--platform", "linux_x86_64", 
            "--target", temp_dir,
            "--implementation", "cp",
            "--python-version", "3.11",
            "--only-binary=:all:",
            "--upgrade",
            "-r", "requirements_simple.txt"
        ], check=True)
        
        # Copy simple lambda function
        print("📋 Copying simple lambda function...")
        shutil.copy2("lambda_function_simple.py", os.path.join(temp_dir, "lambda_function.py"))
        
        # Create ZIP
        zip_path = "lambda_simple_test.zip"
        print(f"🗜️  Creating ZIP: {zip_path}")
        
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
        print(f"❌ Error: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir)

def update_lambda_function(zip_path):
    """Update Lambda function"""
    print("🔄 Updating Lambda function...")
    
    try:
        subprocess.run([
            "aws", "lambda", "update-function-code",
            "--function-name", "duo-mapping-api",
            "--zip-file", f"fileb://{zip_path}"
        ], check=True)
        
        print("✅ Lambda function updated!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Update failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Deploying Simple Test Lambda")
    print("=" * 40)
    
    zip_path = create_simple_package()
    
    if zip_path and os.path.exists(zip_path):
        if update_lambda_function(zip_path):
            print("\n✅ Test deployment successful!")
            print("🧪 Test the API:")
            print("   https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/")
            print("   https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/api/health")
        else:
            print("\n❌ Deployment failed")
    else:
        print("❌ Package creation failed")
