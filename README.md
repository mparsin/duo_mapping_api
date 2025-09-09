# Duo Mapping API

A FastAPI application for mapping business data fields to ERP table columns, deployed on AWS Lambda with automatic HTTPS access.

## 🚀 Live API

**Base URL:** https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod

### Available Endpoints

- `GET /` - API status
- `GET /api/health` - Health check
- `GET /api/categories` - Get all categories with mapping percentages
- `GET /api/categories/{id}` - Get specific category
- `GET /api/categories/{id}/sub-categories` - Get sub-categories
- `GET /api/categories/{id}/lines` - Get category lines with mappings
- `GET /api/tables` - Get all ERP tables
- `GET /api/tables/{id}/columns` - Get table columns
- `GET /api/search-columns?columnName=X` - Search columns
- `POST /api/find-table-matches` - Find matching tables
- `PATCH /api/lines/{id}` - Update line mappings
- `POST /api/categories/recalculate-percent-mapped` - Recalculate mapping percentages

## 🏗️ Architecture

- **Backend:** FastAPI (Python 3.11)
- **Database:** PostgreSQL
- **Hosting:** AWS Lambda + API Gateway
- **Deployment:** GitHub Actions (CI/CD)
- **Security:** HTTPS with CORS enabled

## 🔄 Automatic Deployment

This repository uses GitHub Actions for automatic deployment:

- **Triggers:** Push to `main` or `master` branch
- **Process:** Test → Build → Deploy → Verify
- **Target:** AWS Lambda function `duo-mapping-api`

### Deployment Status

![Deploy to AWS Lambda](https://github.com/mparsin/duo_mapping_api/actions/workflows/deploy.yml/badge.svg)

## 🛠️ Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL access
- AWS CLI (for deployment)

### Setup

1. **Clone repository:**
   ```bash
   git clone https://github.com/mparsin/duo_mapping_api.git
   cd duo_mapping_api
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For testing
   ```

3. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:port/db"
   ```

4. **Run locally:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Run tests:**
   ```bash
   python test_api.py
   # or
   pytest test_api.py
   ```

## 📦 Manual Deployment

If you need to deploy manually:

```bash
# Build and deploy
python deploy_lambda.py

# Or with Docker (for Linux compatibility)
docker build -f Dockerfile.lambda-build -t lambda-builder .
docker run --name temp-container lambda-builder
docker cp temp-container:/tmp/lambda_full_package.zip ./package.zip
aws lambda update-function-code --function-name duo-mapping-api --zip-file fileb://package.zip
```

## 🔐 AWS Setup Required

For automatic deployment, these AWS credentials need to be set in GitHub Secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Required AWS Resources

- Lambda function: `duo-mapping-api`
- API Gateway: REST API with proxy integration
- IAM role: `lambda-execution-role` with basic Lambda permissions
- PostgreSQL database (accessible from Lambda)

## 📊 Monitoring

- **Lambda Console:** [AWS Lambda Function](https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/duo-mapping-api)
- **API Gateway:** [AWS API Gateway](https://console.aws.amazon.com/apigateway/main/apis/xwrhlmtfk9)
- **CloudWatch Logs:** Available for debugging and monitoring

## 🚦 Health Check

Check if the API is running:

```bash
curl https://xwrhlmtfk9.execute-api.us-east-1.amazonaws.com/prod/api/health
```

Expected response:
```json
{"status": "healthy"}
```

## 📝 API Documentation

When running locally, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_api.py`
5. Push to your branch
6. Create a Pull Request

## 📄 License

This project is part of the RedZone ERP mapping system.
