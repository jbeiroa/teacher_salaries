# Deployment and Automation Guide

This document explains how to maintain and automate the **Teacher Salaries Dashboard** in a production environment (like Render).

## 1. Production Strategy: Artifact Bundling
The application is configured to prioritize loading analytics data (clusters and anomalies) from local files located in the `artifacts/` directory.

- `artifacts/clusters.parquet`
- `artifacts/anomalies.parquet`

This approach avoids the need for a live MLflow server in production, reducing latency and infrastructure costs.

## 2. Automated Updates with GitHub Actions
To keep the dashboard updated with the latest monthly data from CGECSE and INDEC, we use a GitHub Action.

### Workflow Configuration
Create `.github/workflows/monthly_update.yml` with the following content:

```yaml
name: Monthly Data & Model Update

on:
  schedule:
    - cron: '0 0 1 * *' # 1st of every month
  workflow_dispatch:

jobs:
  update-analytics:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

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

      - name: Commit and Push Changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add artifacts/*.parquet
          git commit -m "chore: automated monthly analytics update [skip ci]" || echo "No changes to commit"
          git push
```

### Required Repository Settings
1. **GitHub Settings**: 
   - Navigate to `Settings > Actions > General`.
   - Under **Workflow permissions**, select **Read and write permissions**.
   - Save.

2. **Render Settings**:
   - Ensure **Auto-Deploy** is enabled for your Web Service.
   - When the GitHub Action pushes a commit, Render will automatically redeploy the app with the latest data.

## 3. Local Training
If you wish to update the models manually before a deployment:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
poetry run python train_analytics.py
```
This will update the files in `artifacts/`, which you can then commit and push manually.
