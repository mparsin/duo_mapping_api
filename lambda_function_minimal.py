import json

def handler(event, context):
    """Minimal Lambda function for testing"""
    
    # Extract HTTP method and path
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    
    # Simple routing
    if path == '/':
        response_body = {
            "message": "Duo Mapping API is running on AWS Lambda!",
            "version": "1.0.0",
            "platform": "aws-lambda"
        }
    elif path == '/api/health':
        response_body = {
            "status": "healthy",
            "platform": "aws-lambda"
        }
    elif path.startswith('/api/'):
        response_body = {
            "message": "API endpoint working",
            "path": path,
            "method": http_method,
            "available_endpoints": [
                "/",
                "/api/health",
                "/api/test"
            ]
        }
    else:
        response_body = {
            "error": "Not found",
            "path": path
        }
    
    # Return API Gateway response format
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization'
        },
        'body': json.dumps(response_body)
    }
