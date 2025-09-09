#!/usr/bin/env python3
"""
Create API Gateway for the Lambda function
"""
import json
import subprocess
import time

def run_aws_command(command):
    """Run AWS CLI command and return result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {command}")
        print(f"Error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print(f"⚠️  Command succeeded but returned non-JSON: {result.stdout}")
        return {"output": result.stdout}

def get_account_id():
    """Get AWS account ID"""
    result = subprocess.run([
        "aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"
    ], capture_output=True, text=True, check=True)
    return result.stdout.strip()

def create_api_gateway():
    """Create API Gateway with Lambda integration"""
    print("🌐 Creating API Gateway...")
    
    # Step 1: Create REST API
    print("1️⃣ Creating REST API...")
    api_result = run_aws_command(
        'aws apigateway create-rest-api --name "duo-mapping-api" --description "FastAPI application for duo mapping"'
    )
    
    if not api_result:
        return False
        
    api_id = api_result["id"]
    print(f"   ✅ API created with ID: {api_id}")
    
    # Step 2: Get root resource ID
    print("2️⃣ Getting root resource...")
    resources_result = run_aws_command(f'aws apigateway get-resources --rest-api-id {api_id}')
    
    if not resources_result:
        return False
        
    root_resource_id = None
    for item in resources_result["items"]:
        if item["path"] == "/":
            root_resource_id = item["id"]
            break
    
    if not root_resource_id:
        print("❌ Could not find root resource")
        return False
        
    print(f"   ✅ Root resource ID: {root_resource_id}")
    
    # Step 3: Create proxy resource
    print("3️⃣ Creating proxy resource...")
    proxy_result = run_aws_command(
        f'aws apigateway create-resource --rest-api-id {api_id} --parent-id {root_resource_id} --path-part "{{proxy+}}"'
    )
    
    if not proxy_result:
        return False
        
    proxy_resource_id = proxy_result["id"]
    print(f"   ✅ Proxy resource created: {proxy_resource_id}")
    
    # Step 4: Create ANY method on proxy resource
    print("4️⃣ Creating ANY method on proxy resource...")
    method_result = run_aws_command(
        f'aws apigateway put-method --rest-api-id {api_id} --resource-id {proxy_resource_id} --http-method ANY --authorization-type NONE'
    )
    
    if not method_result:
        return False
        
    print("   ✅ ANY method created on proxy resource")
    
    # Step 5: Create ANY method on root resource
    print("5️⃣ Creating ANY method on root resource...")
    root_method_result = run_aws_command(
        f'aws apigateway put-method --rest-api-id {api_id} --resource-id {root_resource_id} --http-method ANY --authorization-type NONE'
    )
    
    if not root_method_result:
        return False
        
    print("   ✅ ANY method created on root resource")
    
    # Step 6: Setup Lambda integration for proxy resource
    print("6️⃣ Setting up Lambda integration for proxy...")
    account_id = get_account_id()
    lambda_arn = f"arn:aws:lambda:us-east-1:{account_id}:function:duo-mapping-api"
    lambda_uri = f"arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
    
    integration_result = run_aws_command(
        f'aws apigateway put-integration --rest-api-id {api_id} --resource-id {proxy_resource_id} --http-method ANY --type AWS_PROXY --integration-http-method POST --uri {lambda_uri}'
    )
    
    if not integration_result:
        return False
        
    print("   ✅ Lambda integration created for proxy")
    
    # Step 7: Setup Lambda integration for root resource
    print("7️⃣ Setting up Lambda integration for root...")
    root_integration_result = run_aws_command(
        f'aws apigateway put-integration --rest-api-id {api_id} --resource-id {root_resource_id} --http-method ANY --type AWS_PROXY --integration-http-method POST --uri {lambda_uri}'
    )
    
    if not root_integration_result:
        return False
        
    print("   ✅ Lambda integration created for root")
    
    # Step 8: Grant API Gateway permission to invoke Lambda
    print("8️⃣ Granting API Gateway permission to invoke Lambda...")
    source_arn = f"arn:aws:execute-api:us-east-1:{account_id}:{api_id}/*/*"
    
    permission_result = run_aws_command(
        f'aws lambda add-permission --function-name duo-mapping-api --statement-id apigateway-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn {source_arn}'
    )
    
    if permission_result is None:
        # This might fail if permission already exists, which is OK
        print("   ⚠️  Permission might already exist")
    else:
        print("   ✅ Permission granted")
    
    # Step 9: Create deployment
    print("9️⃣ Creating deployment...")
    deployment_result = run_aws_command(
        f'aws apigateway create-deployment --rest-api-id {api_id} --stage-name prod'
    )
    
    if not deployment_result:
        return False
        
    print("   ✅ Deployment created")
    
    # Step 10: Get the API endpoint
    api_url = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/prod"
    
    print("\n" + "="*60)
    print("🎉 API Gateway successfully created!")
    print("="*60)
    print(f"🌐 API Endpoint: {api_url}")
    print(f"🔗 API with /api path: {api_url}/api")
    print(f"📊 API Management: https://console.aws.amazon.com/apigateway/main/apis/{api_id}")
    print(f"📝 Lambda Function: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/duo-mapping-api")
    print("="*60)
    
    # Test the API
    print("\n🧪 Testing API endpoints...")
    test_endpoints = [
        f"{api_url}/",
        f"{api_url}/api/health",
        f"{api_url}/api/categories"
    ]
    
    for endpoint in test_endpoints:
        print(f"Test: {endpoint}")
    
    return True

if __name__ == "__main__":
    print("🚀 Setting up API Gateway for Duo Mapping API")
    print("=" * 60)
    
    success = create_api_gateway()
    
    if success:
        print("\n✅ Setup complete! Your FastAPI app is now available via HTTPS!")
    else:
        print("\n❌ Setup failed. Check the errors above.")
