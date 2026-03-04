from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_litellm import ChatLiteLLM
from src.salary_data.scraper import Scraper
import pandas as pd
import numpy as np


class DataJournalistAgent:
    def __init__(self, dfs_dict: dict[str, pd.DataFrame], model_params=None):
        """
        Initializes the agent with a dictionary of dataframes and performs 
        alignment and pre-calculations to simplify the LLM's task.
        """
        # Default for LM Studio or Ollama
        self.model_params = model_params or {
            "model": "ollama/qwen2.5:7b",
            "base_url": "http://localhost:11434",
            "temperature": 0
        }
        
        # Pre-process dataframes
        self.dfs_dict = self._prepare_data(dfs_dict)
        self.agent = self._setup_agent()

    def _prepare_data(self, dfs_dict):
        """Aligns data and adds pre-calculated real salaries."""
        scraper = Scraper()
        start_limit = '2016-12-01'
        
        df_net = dfs_dict.get('net_salaries')
        # Ensure we have data before slicing
        if df_net is not None:
            df_net = df_net.loc[df_net.index >= start_limit]
        
        df_ipc = dfs_dict.get('inflation_ipc')
        if df_ipc is not None:
            df_ipc = df_ipc.loc[df_ipc.index >= start_limit]
            
        df_poverty = dfs_dict.get('poverty_lines')
        if df_poverty is not None:
            df_poverty = df_poverty.loc[df_poverty.index >= start_limit]
        
        # Calculate Real Salaries using scraper logic
        df_real = scraper.calculate_real_salary(df_net, df_ipc['infl_Nivel_general'])
        
        # Calculate Real Salary Index (Base 100 = Nov 2023)
        ref_date = '2023-11-01'
        if ref_date in df_real.index:
            base_values = df_real.loc[ref_date]
            df_real_index = (df_real / base_values) * 100
        else:
            # Find the closest date to Nov 2023 if exact date is missing
            closest_date = df_real.index[df_real.index.get_indexer([pd.to_datetime(ref_date)], method='nearest')[0]]
            df_real_index = (df_real / df_real.loc[closest_date]) * 100 
            
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
        
        # Metadata to help the agent
        provinces = list(self.dfs_dict['nominal_salaries'].columns)
        date_min = self.dfs_dict['nominal_salaries'].index.min().strftime('%Y-%m')
        date_max = self.dfs_dict['nominal_salaries'].index.max().strftime('%Y-%m')
        
        df_descriptions = [
            "- df1: 'nominal_salaries' (Current AR$ values. Index: 'date', Columns: Province names)",
            "- df2: 'real_salaries' (Inflation-adjusted AR$. Index: 'date', Columns: Province names)",
            "- df3: 'purchasing_power_index' (Base 100 at 2023-11-01. Index: 'date'. Values < 100 mean loss since Nov 23)",
            "- df4: 'inflation_ipc' (Inflation indices. Index: 'date')",
            "- df5: 'poverty_lines' (CBA and CBT values. Index: 'date')"
        ]
        
        prefix = f"""
You are an expert Argentinian Data Journalist specializing in teacher salaries. 
You have access to 5 dataframes with data from {date_min} to {date_max}.
{"\n".join(df_descriptions)}

PROVINCES AVAILABLE: {", ".join(provinces)}

IMPORTANT: The 'date' is the INDEX of all dataframes. Access it via 'df.index'.

STRICT FORMAT FOR ACTIONS:
You MUST follow this EXACT format for every step. Do NOT skip any part.
Thought: I need to check the last available salaries.
Action: python_repl_ast
Action Input: print(df1.tail(3))
Observation: <output from python>
... (repeat if needed)
Final Answer: <your final detailed analysis in natural language>

If you have already found the answer, skip Thought/Action and go straight to Final Answer.
"""
        
        agent = create_pandas_dataframe_agent(
            llm, 
            df_list,
            verbose=True,
            allow_dangerous_code=True,
            prefix=prefix,
            max_iterations=10,
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
