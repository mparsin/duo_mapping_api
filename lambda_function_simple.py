from mangum import Mangum
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Duo Mapping API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Duo Mapping API is running on Lambda!"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "platform": "aws-lambda"}

@app.get("/api/test")
async def test_endpoint():
    return {
        "message": "Test endpoint working",
        "endpoints": [
            "/",
            "/api/health", 
            "/api/test"
        ]
    }

# Lambda handler
handler = Mangum(app, lifespan="off")
