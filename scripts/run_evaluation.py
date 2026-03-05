import mlflow
import pandas as pd
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.salary_data.scraper import Scraper
from src.salary_data.agent import DataJournalistAgent
from dotenv import load_dotenv

load_dotenv()

def run_evaluation():
    # 1. Setup Data
    scraper = Scraper()
    df_net = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO)
    df_ipc = scraper.get_ipc_indec()
    df_poverty = scraper.get_cba_cbt()
    
    dfs_dict = {
        "net_salaries": df_net,
        "inflation_ipc": df_ipc,
        "poverty_lines": df_poverty
    }

    # 2. Define Evaluation Cases (Ground Truth)
    eval_cases = [
        {
            "q": "Which is the top paying province in September 2025 and what is the salary?",
            "gt": "Neuquén ($1,471,200)"
        },
        {
            "q": "What was the purchasing power loss in Buenos Aires between September 2023 and September 2025?",
            "gt": "-30.45%"
        },
        {
            "q": "Compare the salary evolution of Córdoba versus Inflation (IPC) between December 2023 and September 2025.",
            "gt": "Salary: +175.90%, IPC: +165.60% (Beat inflation by ~10 pts)"
        },
        {
            "q": "What was the real salary index for Santa Fe in June 2024 (Base 100 = September 2023)?",
            "gt": "75.94"
        },
        {
            "q": "Which province had the highest percentage growth in real salary between September 2023 and September 2025?",
            "gt": "Neuquén (+23.8%)"
        },
        {
            "q": "Which provinces lost more purchasing power between November 2023 and today?",
            "gt": """Neuquén (+23.8%), Santa Cruz (+21.3%), Tierra del Fuego (+9.7%)
            Salta (-34.5%), Santiago del Estero (-34.5%), San Luis (-47.3%)"""
        }
    ]

    # 3. Models to Evaluate
    models = [
        {"model": "openai/gpt-4o-mini"},
        {"model": "ollama/qwen3.5:9b", "base_url": "http://localhost:11434"},
        {"model": "ollama/qwen3.5:4b", "base_url": "http://localhost:11434"},
        {"model": "ollama/llama3.2:3b", "base_url": "http://localhost:11434"}
    ]

    mlflow.set_experiment("Agent_Comparison_March_2026")

    for m_params in models:
        print(f"\n>>> Evaluating Model: {m_params['model']}")
        m_params["temperature"] = 0
        
        agent = DataJournalistAgent(dfs_dict, model_params=m_params)
        
        # Start a single run for the entire model evaluation
        with mlflow.start_run(run_name=f"Model_{m_params['model'].split('/')[-1]}"):
            mlflow.log_params(m_params)
            
            for case in eval_cases:
                print(f"Question: {case['q']}")
                try:
                    agent.query_and_log(case['q'], ground_truth=case['gt'])
                except Exception as e:
                    print(f"Error in query: {e}")
                    continue

    print("\n--- Evaluation Complete ---")
    print("Run 'mlflow ui' to see results.")

if __name__ == "__main__":
    run_evaluation()
