# AWS Setup Instructions for GitHub Actions

## 🎯 **Goal**
Set up AWS credentials for GitHub Actions to automatically deploy the Duo Mapping API to Lambda.

## 🔐 **Option 1: Create Dedicated IAM User (Recommended)**

### Step 1: Create IAM User
1. Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
2. Click "Users" → "Create user"
3. User name: `github-actions-deployer`
4. Access type: ✅ **Programmatic access** (Access key)
5. Click "Next"

### Step 2: Create Custom Policy
1. In IAM Console, go to "Policies" → "Create policy"
2. Choose "JSON" tab
3. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaDeploymentPermissions",
            "Effect": "Allow",
            "Action": [
                "lambda:UpdateFunctionCode",
                "lambda:GetFunction",
                "lambda:UpdateFunctionConfiguration"
            ],
            "Resource": "arn:aws:lambda:us-east-1:393512459264:function:duo-mapping-api"
        },
        {
            "Sid": "LambdaWaitPermissions", 
            "Effect": "Allow",
            "Action": [
                "lambda:GetFunction"
            ],
            "Resource": "arn:aws:lambda:us-east-1:393512459264:function:duo-mapping-api"
        }
    ]
}
```

4. Name: `GitHubActionsLambdaDeployment`
5. Click "Create policy"

### Step 3: Attach Policy to User
1. Go back to the user: `github-actions-deployer`
2. Click "Add permissions" → "Attach policies directly"
3. Search for: `GitHubActionsLambdaDeployment`
4. Select it and click "Add permissions"

### Step 4: Generate Access Keys
1. Go to user: `github-actions-deployer`
2. Click "Security credentials" tab
3. Click "Create access key"
4. Choose "Third-party service"
5. Click "Create access key"
6. **⚠️ IMPORTANT:** Copy and save:
   - **Access Key ID**
   - **Secret Access Key**

## 🔐 **Option 2: Use Existing User with Sufficient Permissions**

If you already have an IAM user with Lambda permissions, you can use those credentials instead.

### Required Permissions for Existing User:
- `lambda:UpdateFunctionCode`
- `lambda:GetFunction`
- `lambda:UpdateFunctionConfiguration`

## 🔧 **GitHub Repository Setup**

### Step 1: Add Secrets to GitHub
1. Go to: https://github.com/mparsin/duo_mapping_api/settings/secrets/actions
2. Click "New repository secret"

**Secret 1:**
- Name: `AWS_ACCESS_KEY_ID`
- Value: [The Access Key ID from Step 4 above]

**Secret 2:**
- Name: `AWS_SECRET_ACCESS_KEY`  
- Value: [The Secret Access Key from Step 4 above]

### Step 2: Test the Setup
1. Make a small change to any file in the repository
2. Commit and push to main/master branch:
   ```bash
   git add .
   git commit -m "Test auto-deployment"
   git push origin master
   ```
3. Check GitHub Actions: https://github.com/mparsin/duo_mapping_api/actions

## ✅ **Verification**

After setup, you should see:
- ✅ GitHub Actions workflow runs automatically on push
- ✅ Tests pass
- ✅ Lambda function gets updated
- ✅ API endpoints respond correctly

## 🔍 **Troubleshooting**

### Common Issues:
1. **Access Denied:** Check IAM policy permissions
2. **Function Not Found:** Verify Lambda function name matches
3. **Region Mismatch:** Ensure us-east-1 region is correct
4. **"GITHUB_SCHEMA_PR_OWNER and GITHUB_SCHEMA_PR_REPO must be set":** Lambda does **not** load a `.env` file. You must set these (and `GITHUB_TOKEN_ENCRYPTION_KEY`) as Lambda environment variables—see **Create-schema-pr / GitHub env vars** below.

### Create-schema-pr / GitHub env vars

`POST /api/create-schema-pr` and `PUT /api/github-connection` need these **Lambda environment variables** (they are not read from `.env` in the cloud):

| Variable | Required | Example |
|----------|----------|---------|
| `GITHUB_SCHEMA_PR_OWNER` | Yes | `mparsin` |
| `GITHUB_SCHEMA_PR_REPO` | Yes | `duo-mapping-client` |
| `GITHUB_TOKEN_ENCRYPTION_KEY` | Yes (for token encrypt/decrypt) | 32-byte base64 key |

**Option A – AWS Console**

1. Open [Lambda → duo-mapping-api](https://us-east-1.console.aws.amazon.com/lambda/home?region=us-east-1#/functions/duo-mapping-api).
2. **Configuration** → **Environment variables** → **Edit**.
3. Add `GITHUB_SCHEMA_PR_OWNER`, `GITHUB_SCHEMA_PR_REPO`, and `GITHUB_TOKEN_ENCRYPTION_KEY` (same values as in your local `.env`).
4. Save.

**Option B – AWS CLI**

`update-function-configuration` replaces all environment variables, so you must include existing ones (e.g. `DATABASE_URL`) plus the new ones:

```bash
aws lambda update-function-configuration --function-name duo-mapping-api --region us-east-1 \
  --environment "Variables={DATABASE_URL=<your-db-url>,GITHUB_SCHEMA_PR_OWNER=mparsin,GITHUB_SCHEMA_PR_REPO=duo-mapping-client,GITHUB_TOKEN_ENCRYPTION_KEY=<your-base64-key>}"
```

Replace `<your-db-url>` and `<your-base64-key>` with your values. To see current vars first: `aws lambda get-function-configuration --function-name duo-mapping-api --query 'Environment.Variables'`.

### Support:
- GitHub Actions logs: Available in repository Actions tab
- AWS CloudWatch logs: Available for Lambda function debugging

## 🛡️ **Security Best Practices**

✅ **Use dedicated IAM user** (not admin credentials)  
✅ **Minimal permissions** (only Lambda deployment)  
✅ **Regular key rotation** (every 90 days)  
✅ **Monitor usage** via CloudTrail  

## 📊 **Current Lambda Function Details**

- **Function Name:** `duo-mapping-api`
- **Region:** `us-east-1`
- **Account:** `393512459264`
- **Runtime:** `python3.11`
- **Current Size:** ~16MB
