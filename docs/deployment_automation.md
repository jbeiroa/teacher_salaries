# Deployment and Automation Guide

This document explains how to maintain and automate the **Teacher Salaries Dashboard** in a production environment using **AWS Lambda** and **Amazon ECR**.

For security and cost-control configuration of the AI agent, see the **[Guardrails Deployment Guide](guardrails_amazon_bedrock.md)**.

## 1. Production Strategy: Artifact Bundling
The application is configured to prioritize loading analytics data (clusters and anomalies) from local files located in the `artifacts/` directory.

- `artifacts/clusters.parquet`
- `artifacts/anomalies.parquet`

This approach avoids the need for a live MLflow server in production, reducing latency and infrastructure costs. These artifacts are bundled directly into the Docker container image deployed to AWS Lambda.

## 2. Deploying to AWS Lambda

### Authentication
Ensure you have the AWS CLI installed and configured with credentials that have access to ECR and Lambda:
```bash
aws configure
```

### Build and Push Docker Image to ECR
1. **Login to ECR**:
   ```bash
   aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com
   ```

2. **Create ECR Repository (First time only)**:
   ```bash
   aws ecr create-repository --repository-name teacher-salaries-app --region <YOUR_REGION>
   ```

3. **Build the Image**:
   ```bash
   docker build -t teacher-salaries-app .
   ```

4. **Tag the Image**:
   ```bash
   docker tag teacher-salaries-app:latest <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
   ```

5. **Push the Image**:
   ```bash
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
   ```

### Update Lambda Function
Once the new image is pushed, update the Lambda function to use the latest image:
```bash
aws lambda update-function-code \
    --function-name teacher-salaries-app \
    --image-uri <AWS_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com/teacher-salaries-app:latest
```

## 3. Automated Updates with GitHub Actions
To keep the dashboard updated with the latest monthly data from CGECSE and INDEC, we use a GitHub Action. The workflow trains the models and pushes a new Docker image to ECR.

### Required Repository Secrets
Add the following secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_ACCOUNT_ID`

### Workflow Configuration
Create `.github/workflows/monthly_update.yml` with the following content:

```yaml
name: Monthly Data & Model Update

on:
  schedule:
    - cron: '0 0 1 * *' # 1st of every month
  workflow_dispatch:

jobs:
  update-analytics-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Poetry
        uses: snok/install-poetry@v1
        with:
          virtualenvs-create: true
          virtualenvs-in-project: true

      - name: Install Dependencies
        run: poetry install --no-interaction

      - name: Run Update Pipeline
        run: |
          export PYTHONPATH=$PYTHONPATH:$(pwd)/src
          poetry run python train_analytics.py

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to Amazon ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: teacher-salaries-app
          IMAGE_TAG: latest
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

      - name: Update Lambda Function Code
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: teacher-salaries-app
          IMAGE_TAG: latest
        run: |
          aws lambda update-function-code \
            --function-name teacher-salaries-app \
            --image-uri $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

## 4. Local Training
If you wish to update the models manually before a deployment:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
poetry run python train_analytics.py
```
This will update the files in `artifacts/`, which you can then test locally or bundle in your next Docker build.