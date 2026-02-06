import os
import traceback
from mangum import Mangum
from main import app

# API Gateway stage prefix (e.g. /prod) - strip so FastAPI receives / and /api/health
# Set API_GATEWAY_BASE_PATH in Lambda env if using a different stage name
api_gateway_base_path = os.getenv("API_GATEWAY_BASE_PATH", "/prod")

_mangum_handler = Mangum(app, lifespan="off", api_gateway_base_path=api_gateway_base_path)


def handler(event, context):
    """Wrap Mangum so we return actual errors in response body for debugging."""
    try:
        return _mangum_handler(event, context)
    except Exception as e:
        # Return 500 with error details so deployment test logs show the real cause
        body = {
            "message": "Internal server error",
            "detail": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": __import__("json").dumps(body),
        }
