import os
from mangum import Mangum
from main import app

# API Gateway stage prefix (e.g. /prod) - strip so FastAPI receives / and /api/health
# Set API_GATEWAY_BASE_PATH in Lambda env if using a different stage name
api_gateway_base_path = os.getenv("API_GATEWAY_BASE_PATH", "/prod")

handler = Mangum(app, lifespan="off", api_gateway_base_path=api_gateway_base_path)
