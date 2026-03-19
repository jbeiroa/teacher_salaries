import os
import pandas as pd
import boto3
from io import BytesIO
from typing import Dict, Optional
from salary_data.scraper import Scraper
from salary_data.analytics import AnalyticsPipeline


class DataLoader:
    """Handles loading and caching data from S3 or local fallback."""

    def __init__(self):
        self.bucket = os.getenv("AWS_S3_BUCKET")
        self.region = os.getenv("AWS_REGION", "us-east-1")

        # Get credentials from environment
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")

        if self.bucket:
            # Check for manually provided user keys. 
            # Note: Lambda's internal keys start with 'ASIA'. We should let boto3 handle those automatically.
            is_manual_key = access_key and not access_key.startswith("ASIA")
            
            if is_manual_key and secret_key and access_key.strip() and secret_key.strip():
                print(f"[DataLoader] Detected manual Access Key (starting with: {access_key[:5]}...)")
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=access_key.strip(),
                    aws_secret_access_key=secret_key.strip(),
                    aws_session_token=session_token.strip() if session_token else None,
                    region_name=self.region,
                )
            else:
                # No manual keys provided (or we are in Lambda with temporary ASIA keys).
                # Boto3's default credential chain handles IAM Roles and ASIA keys automatically.
                print("[DataLoader] Relying on default credential chain / IAM Role.")
                self.s3_client = boto3.client("s3", region_name=self.region)
        else:
            print("[DataLoader] WARNING: AWS_S3_BUCKET not set.")
            self.s3_client = None

        self.scraper = Scraper()
        self.pipeline = AnalyticsPipeline()

    def _load_from_s3(self, key: str) -> Optional[pd.DataFrame]:
        """Loads a Parquet file from S3."""
        if not self.s3_client or not self.bucket:
            return None
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return pd.read_parquet(BytesIO(response["Body"].read()))
        except Exception as e:
            print(f"[DataLoader] Failed to load {key} from S3: {e}")
            return None

    def _save_to_s3(self, df: pd.DataFrame, key: str):
        """Saves a DataFrame to S3 as Parquet."""
        if not self.s3_client or not self.bucket:
            return
        try:
            out_buffer = BytesIO()
            df.to_parquet(out_buffer, index=True)
            self.s3_client.put_object(
                Bucket=self.bucket, Key=key, Body=out_buffer.getvalue()
            )
            print(f"[DataLoader] Saved {key} to S3.")
        except Exception as e:
            print(f"[DataLoader] Failed to save {key} to S3: {e}")

    def get_all_data(self) -> Dict[str, pd.DataFrame]:
        """
        Main entry point for the app to get all necessary data.
        Tries S3 first, then scrapes/calculates if missing.
        """
        data = {}

        # Keys mapping
        keys = {
            "net_salaries": "raw/net_salaries.parquet",
            "gross_salaries": "raw/gross_salaries.parquet",
            "basic_salaries": "raw/basic_salaries.parquet",
            "inflation_ipc": "raw/inflation_ipc.parquet",
            "poverty_lines": "raw/poverty_lines.parquet",
            "clusters": "artifacts/clusters.parquet",
            "anomalies": "artifacts/anomalies.parquet",
        }

        loaded_count = 0
        for name, key in keys.items():
            df = self._load_from_s3(key)
            if df is not None:
                data[name] = df
                loaded_count += 1

        # If any data is missing from S3, perform a full scrape (fallback)
        if loaded_count < len(keys):
            # CRITICAL: Do NOT auto-scrape in Lambda production environment as it causes timeouts (10s+).
            # The bucket should be primed beforehand.
            if os.getenv("LAMBDA_TASK_ROOT"):
                print(f"[DataLoader] ERROR: Missing {len(keys) - loaded_count} keys in S3. Skipping auto-scrape to prevent timeout.")
                # We return whatever we have, or partial data, 
                # but we don't trigger a 20-second scrape.
                return data

            print(
                f"[DataLoader] Only {loaded_count}/{len(keys)} found in S3. Falling back to scraper."
            )
            scraped_data = self.scrape_and_process_all()
            # Update missing pieces in 'data' dictionary
            for k, v in scraped_data.items():
                if k not in data:
                    data[k] = v

        return data

    def scrape_and_process_all(self) -> Dict[str, pd.DataFrame]:
        """Performs a full scrape and analytics run."""
        print("[DataLoader] Scraping all data sources...")

        df_net = self.scraper.get_cgecse_salaries(self.scraper.URL_TESTIGO_NETO)
        df_gross = self.scraper.get_cgecse_salaries(self.scraper.URL_TESTIGO_BRUTO)
        df_basic = self.scraper.get_cgecse_salaries(self.scraper.URL_BASICO)
        df_ipc = self.scraper.get_ipc_indec()
        df_poverty = self.scraper.get_cba_cbt()

        # Align data for analytics (Dec 2016 onwards)
        START_LIMIT = "2016-12-01"
        df_net_trunc = df_net.loc[START_LIMIT:]
        df_ipc_trunc = df_ipc.loc[START_LIMIT:]

        # Calculate real salary for analytics
        df_real = self.scraper.calculate_real_salary(
            df_net_trunc,
            df_ipc_trunc["infl_Nivel_general"],
            base_date=df_net_trunc.index.min(),
        )

        # Run Analytics
        print("[DataLoader] Running analytics pipeline...")
        df_clusters, df_anomalies = self.pipeline.run_pipeline(df_real)

        return {
            "net_salaries": df_net,
            "gross_salaries": df_gross,
            "basic_salaries": df_basic,
            "inflation_ipc": df_ipc,
            "poverty_lines": df_poverty,
            "clusters": df_clusters,
            "anomalies": df_anomalies,
        }

    def upload_all_to_s3(self, data: Dict[str, pd.DataFrame]):
        """Uploads the entire dataset to S3."""
        keys = {
            "net_salaries": "raw/net_salaries.parquet",
            "gross_salaries": "raw/gross_salaries.parquet",
            "basic_salaries": "raw/basic_salaries.parquet",
            "inflation_ipc": "raw/inflation_ipc.parquet",
            "poverty_lines": "raw/poverty_lines.parquet",
            "clusters": "artifacts/clusters.parquet",
            "anomalies": "artifacts/anomalies.parquet",
        }
        for name, key in keys.items():
            if name in data:
                self._save_to_s3(data[name], key)
