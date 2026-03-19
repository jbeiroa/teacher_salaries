import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from salary_data.loader import DataLoader


def run_update():
    load_dotenv()

    loader = DataLoader()

    # 1. Scrape everything
    print(f"[{datetime.now()}] Starting data update check...")
    current_data = loader.scrape_and_process_all()

    # 2. Check if update is actually needed (optional optimization)
    # We compare the latest date in the scraped salary data with what's on S3
    latest_s3_net = loader._load_from_s3("raw/net_salaries.parquet")

    if latest_s3_net is not None:
        last_s3_date = latest_s3_net.index.max()
        last_scraped_date = current_data["net_salaries"].index.max()

        print(f"Last date in S3: {last_s3_date}")
        print(f"Last date scraped: {last_scraped_date}")

        if last_scraped_date <= last_s3_date:
            print("No new salary data detected. Skipping upload to S3.")
            # Note: We might still want to update if IPC or Poverty data changed,
            # but usually they move together or close enough.
            # To be safe, we could also check IPC.
            return

    # 3. Upload to S3
    print("New data detected or S3 was empty. Uploading to S3...")
    loader.upload_all_to_s3(current_data)
    print("Update completed successfully.")


if __name__ == "__main__":
    run_update()
