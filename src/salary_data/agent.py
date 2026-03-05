from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_litellm import ChatLiteLLM
from langchain_core.tools import tool
from src.salary_data.scraper import Scraper
import pandas as pd
import numpy as np
import mlflow


class DataJournalistAgent:
    def __init__(self, dfs_dict: dict[str, pd.DataFrame], model_params=None):
        """
        Initializes the agent with a dictionary of dataframes and performs 
        alignment and pre-calculations to simplify the LLM's task.
        """
        # Default for LM Studio or Ollama
        self.model_params = model_params or {
            "model": "ollama/qwen3.5:4b",
            "base_url": "http://localhost:11434",
            "temperature": 0
        }
        
        # Pre-process dataframes
        self.dfs_dict = self._prepare_data(dfs_dict)
        self.agent = self._setup_agent()

    def _prepare_data(self, dfs_dict):
        """Aligns data and adds pre-calculated real salaries."""
        scraper = Scraper()
        
        df_net = dfs_dict.get('net_salaries')
        df_ipc = dfs_dict.get('inflation_ipc')
        df_poverty = dfs_dict.get('poverty_lines')
        
        # resample dfs to common index
        common_index = df_net.index.intersection(df_ipc.index)
        df_net = df_net.loc[common_index]
        df_ipc = df_ipc.loc[common_index]
        df_poverty = df_poverty.loc[common_index]
        
        # Calculate Real Salaries using scraper logic from first date in df_net
        start_limit = df_net.index.min()
        df_real = scraper.calculate_real_salary(df_net, df_ipc['infl_Nivel_general'], base_date=start_limit)
        
        # Calculate Real Salary Index (Base 100 = start_limit)
        base_values = df_real.loc[start_limit]
        df_real_index = (df_real / base_values) * 100
            
        return {
            "nominal_salaries": df_net,
            "real_salaries": df_real,
            "purchasing_power_index": df_real_index,
            "inflation_ipc": df_ipc,
            "poverty_lines": df_poverty
        }

    def _setup_agent(self):
        # LiteLLM allows using ollama or lm_studio/ easily
        llm = ChatLiteLLM(**self.model_params)
        
        df_list = list(self.dfs_dict.values())
        
        # Define Tools using the @tool decorator
        @tool
        def calculate_purchasing_power_loss(query: str) -> str:
            """Calculates % change in real salary between two dates. Input: 'start_date, end_date, province' (province optional). Use YYYY-MM-DD."""
            try:
                parts = [p.strip() for p in query.split(",")]
                start_date, end_date = parts[0], parts[1]
                province = parts[2] if len(parts) > 2 else None
                
                df_real = self.dfs_dict['real_salaries']
                
                if province and province in df_real.columns:
                    val_start = df_real.loc[start_date, province]
                    val_end = df_real.loc[end_date, province]
                    loss = (val_end / val_start - 1) * 100
                    return f"Purchasing power change for {province} between {start_date} and {end_date}: {loss:.2f}%"
                else:
                    series_start = df_real.loc[start_date]
                    series_end = df_real.loc[end_date]
                    loss_all = (series_end / series_start - 1) * 100
                    return f"Purchasing power change for all provinces between {start_date} and {end_date}:\n{loss_all.to_string()}"
            except Exception as e:
                return f"Error calculating loss: {str(e)}. Ensure dates are in YYYY-MM-DD format and provinces are spelled correctly."

        @tool
        def compare_evolution(query: str) -> str:
            """Compares % growth of Nominal Salary vs Inflation vs Poverty Line. Input: 'start_date, end_date, province'. Use YYYY-MM-DD."""
            try:
                parts = [p.strip() for p in query.split(",")]
                start_date, end_date = parts[0], parts[1]
                province = parts[2]
                
                # Nominal Salary Change
                df_nom = self.dfs_dict['nominal_salaries']
                nom_change = (df_nom.loc[end_date, province] / df_nom.loc[start_date, province] - 1) * 100
                
                # IPC Change
                df_ipc = self.dfs_dict['inflation_ipc']['infl_Nivel_general']
                ipc_change = (df_ipc.loc[end_date] / df_ipc.loc[start_date] - 1) * 100
                
                # CBT Change
                df_pov = self.dfs_dict['poverty_lines']['linea_pobreza']
                # CBT is monthly, salaries might be quarterly. Find closest date if exact match fails
                cbt_start = df_pov.asof(start_date) if start_date not in df_pov.index else df_pov.loc[start_date]
                cbt_end = df_pov.asof(end_date) if end_date not in df_pov.index else df_pov.loc[end_date]
                cbt_change = (cbt_end / cbt_start - 1) * 100
                
                res = (
                    f"Evolution Comparison ({start_date} to {end_date}) for {province}:\n"
                    f"- Nominal Salary: {nom_change:+.2f}%\n"
                    f"- Inflation (IPC): {ipc_change:+.2f}%\n"
                    f"- Poverty Line (CBT): {cbt_change:+.2f}%\n"
                    f"Net result vs Inflation: {(nom_change - ipc_change):+.2f} points."
                )
                return res
            except Exception as e:
                return f"Error in comparison: {str(e)}. Check dates and province name."

        @tool
        def get_rebased_index(query: str) -> str:
            """Recalculates the Purchasing Power Index (Base 100) using a new base date. Input: 'YYYY-MM-DD'."""
            try:
                base_date = query.strip()
                df_real = self.dfs_dict['real_salaries']
                base_values = df_real.loc[base_date]
                rebased = (df_real / base_values) * 100
                return f"Rebased Index (Base 100 = {base_date}) for the last 3 available dates:\n{rebased.tail(3).to_string()}"
            except Exception as e:
                return f"Error rebasing: {str(e)}. Use YYYY-MM-DD format."

        custom_tools = [calculate_purchasing_power_loss, compare_evolution, get_rebased_index]
        
        # Metadata to help the agent
        provinces = list(self.dfs_dict['nominal_salaries'].columns)
        date_min = self.dfs_dict['nominal_salaries'].index.min().strftime('%Y-%m-%d')
        date_max = self.dfs_dict['nominal_salaries'].index.max().strftime('%Y-%m-%d')
        
        df_descriptions = [
            f"- df1: 'nominal_salaries' (AR$ values for all provinces. Index: 'date', Range: {date_min} to {date_max})",
            f"- df2: 'real_salaries' (Inflation-adjusted AR$ for all provinces. Index: 'date', Range: {date_min} to {date_max})",
            f"- df3: 'purchasing_power_index' (Base 100 at {date_min}. Index: 'date', Range: {date_min} to {date_max})",
            f"- df4: 'inflation_ipc' (Inflation indices. Index: 'date', Range: {date_min} to {date_max})",
            f"- df5: 'poverty_lines' (CBA and CBT values. Index: 'date', Range: {date_min} to {date_max})"
        ]
        
        prefix = f"""
You are an expert Argentinian Data Journalist. 
CRITICAL: The data range is from {date_min} to {date_max} and is quarterly, but some tools may require monthly data. If a specific date is not available, use the closest previous date's data for calculations.
The 'df.head()' samples you see below only show the first few months, but the data covers multiple years up to {date_max}.

{"\n".join(df_descriptions)}

PROVINCES AVAILABLE: {", ".join(provinces)}

All dataframes are indexed by 'date'. Access it via 'df.index'.

YOU HAVE CUSTOM TOOLS (PREFER THESE OVER RAW PANDAS):
- calculate_purchasing_power_loss
- compare_evolution
- get_rebased_index

STRICT FORMAT:
Thought: I need to check data for 2024.
Action: calculate_purchasing_power_loss
Action Input: 2023-12-01, 2024-12-01, Buenos Aires
Observation: ...
Final Answer: [Your analysis]
"""
        
        agent = create_pandas_dataframe_agent(
            llm, 
            df_list,
            verbose=True,
            allow_dangerous_code=True,
            prefix=prefix,
            max_iterations=10,
            extra_tools=custom_tools,
            include_df_in_prompt=True,
            number_of_head_rows=2 # Save tokens and prevent early-date bias
        )
        return agent


    def query(self, user_prompt: str, context_metadata: dict = None):
        """
        Executes a natural language query.
        """
        full_prompt = user_prompt
        if context_metadata:
            full_prompt += f"\n\nContext Metadata: {context_metadata}"
            
        return self.agent.invoke({"input": full_prompt})

    def query_and_log(self, question: str, ground_truth: str = None):
        """
        Executes a query and logs the interaction to MLflow for evaluation.
        """
        if mlflow.active_run() is None:
            mlflow.start_run(run_name=f"Eval_{self.model_params['model']}")
            
        response = self.query(question)
        output = response.get("output", "")
        
        # Log to a simple evaluation table
        eval_data = {
            "question": [question],
            "answer": [output],
            "ground_truth": [ground_truth],
            "model": [self.model_params['model']]
        }
        
        mlflow.log_table(data=eval_data, artifact_file="eval_results.json")
        return output
