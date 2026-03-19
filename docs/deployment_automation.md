# Deployment and Automation Guide

This document explains how to maintain and automate the **Teacher Salaries Dashboard** in a production environment using **AWS Lambda** and **Amazon S3**.


## 1. Production Strategy: S3-First Data Loading
The application uses a decoupled data architecture managed by the `DataLoader` class. Instead of bundling data into the Docker image, the app fetches the latest datasets and analytics artifacts directly from **Amazon S3**.

### Data Hierarchy
1. **S3 (Primary):** The app attempts to load Parquet files from `s3://<BUCKET>/raw/` and `s3://<BUCKET>/artifacts/`.
2. **Scraper (Fallback):** If S3 is empty or inaccessible, the app automatically triggers the `Scraper` to fetch fresh data from government portals and runs the `AnalyticsPipeline` locally.

### Benefits
- **Zero-Redeploy Updates:** Data can be updated in S3 without rebuilding or redeploying the Lambda function.
- **Consistency:** The UI and the AI Agent always see the same synchronized datasets.
- **Performance:** Parquet files on S3 are optimized for fast loading.

## 2. Automated Updates with GitHub Actions
To keep the data fresh, we use a dedicated GitHub Action that runs twice a month (1st and 15th). This workflow scrapes new data, runs the analytics pipeline, and uploads the results to S3.

### Workflow: `Update Salary Data`
**File:** `.github/workflows/data_update.yml`

This workflow is independent of the application deployment. It ensures that even if the app isn't redeployed for months, the data remains current.

### Required Repository Secrets
Add these to `Settings > Secrets and variables > Actions`:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `OPENAI_API_KEY` (Used by the guardrails during the update check)

## 3. Deploying the Application to AWS Lambda

### Build and Push Docker Image to ECR
1. **Login to ECR**:
   ```bash
   aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com
   ```

2. **Build the Image**:
   ```bash
   docker build -t teacher-salaries-app .
   ```

3. **Tag and Push**:
   ```bash
   docker tag teacher-salaries-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
   ```

### Update Lambda Function
```bash
aws lambda update-function-code \
    --function-name teacher-salaries-app \
    --image-uri <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
```

## 4. Manual Data Refresh
To manually trigger a data update and S3 upload from your local machine:
```bash
poetry run python scripts/update_data.py
```
This script will check for new data and only upload to S3 if it finds more recent records than those already stored.

## 5. Environment Configuration
Ensure your production environment (Lambda) has the following variables set:

| Variable | Description |
| :--- | :--- |
| `AWS_S3_BUCKET` | Name of the S3 bucket for data storage. |
| `OPENAI_API_KEY` | Key for GPT-4o-mini (Agent) and GPT-4.1-nano (Guardrails). |
| `GUARDRAIL_MODEL` | Set to `openai/gpt-4.1-nano`. |
| `AGENT_MODEL` | Set to `openai/gpt-4o-mini`. |
