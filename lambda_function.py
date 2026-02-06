import json
import os
import traceback

# API Gateway stage prefix (e.g. /prod) - strip so FastAPI receives / and /api/health
API_GATEWAY_BASE_PATH = os.getenv("API_GATEWAY_BASE_PATH", "/prod")

# Lazy: import app and create Mangum inside handler so import-time errors are caught
# and returned in the response (otherwise Lambda fails at load and returns generic 500).
_mangum_handler = None


def _error_response(e):
    return {
        "statusCode": 500,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Internal server error",
            "detail": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }),
    }


def handler(event, context):
    global _mangum_handler
    try:
        if _mangum_handler is None:
            from main import app
            from mangum import Mangum
            _mangum_handler = Mangum(
                app, lifespan="off", api_gateway_base_path=API_GATEWAY_BASE_PATH
            )
        return _mangum_handler(event, context)
    except Exception as e:
        return _error_response(e)
