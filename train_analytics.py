from src.salary_data.scraper import Scraper
from src.salary_data.analytics import AnalyticsPipeline
import pandas as pd
import os
import sys

# Add src to path just in case
sys.path.append(os.path.join(os.getcwd(), "src"))

def main():
    print("--- Starting Monthly Update Pipeline ---")
    
    # 1. Initialize tools
    scraper = Scraper()
    pipeline = AnalyticsPipeline()
    
    # 2. Fetch latest data
    print("Step 1: Fetching data from CGECSE and INDEC...")
    try:
        # Align data starting from Dec 2016 for consistency
        START_LIMIT = '2016-12-01'
        df_nom = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO).loc[START_LIMIT:]
        df_ipc = scraper.get_ipc_indec()['infl_Nivel_general'].loc[START_LIMIT:]
        
        # Calculate real salary for the pipeline
        # Using a recent date as base to keep values intuitive
        base_date = df_nom.index[-1].strftime("%Y-%m-%d")
        
        # REMOVE PROMEDIO PONDERADO BEFORE TRAINING
        if "Promedio Ponderado (MG Total)" in df_nom.columns:
            df_nom = df_nom.drop(columns=["Promedio Ponderado (MG Total)"])
            
        df_real = scraper.calculate_real_salary(df_nom, df_ipc, base_date=base_date)
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # 3. Run Analytics Pipeline
    print(f"Step 2: Training models with base_date={base_date}...")
    try:
        df_clusters, df_anomalies = pipeline.run_pipeline(df_real, n_clusters=6)
        print("Pipeline finished successfully.")
        print(f"Clusters updated: {len(df_clusters)} provinces.")
        print(f"Anomalies updated: {len(df_anomalies)} records.")
    except Exception as e:
        print(f"Error during analytics pipeline: {e}")
        return

    print("--- Monthly Update Complete ---")

if __name__ == "__main__":
    main()
