from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_litellm import ChatLiteLLM
from langchain_core.tools import tool
from src.salary_data.scraper import Scraper
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.exceptions import OutputParserException
import pandas as pd
import numpy as np
import mlflow
import re

# --- Tool Input Schemas ---

class ProvinceSalaryInput(BaseModel):
    province: str = Field(description="Name of the province. DO NOT include quotes.")
    period: Optional[str] = Field(None, description="Period in YYYY-MM-DD format. If None, uses latest.")

class PurchasingPowerLossInput(BaseModel):
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")
    province: Optional[str] = Field(None, description="Province name. If omitted, returns all provinces.")

class TopKProvincesInput(BaseModel):
    k: int = Field(description="Number of provinces to return in the ranking")
    period: str = Field(description="Target period in YYYY-mm format")
    asc: bool = Field(False, description="True for bottom-paying ranking, False for top-paying ranking")

class DataJournalistAgent:
    def __init__(self, dfs_dict: dict[str, pd.DataFrame], model_params=None):
        self.model_params = model_params or {
            "model": "ollama/qwen3.5:4b",
            "base_url": "http://localhost:11434",
            "temperature": 0
        }
        self.dfs_dict = self._prepare_data(dfs_dict)
        self.agent = self._setup_agent()

    def _prepare_data(self, dfs_dict):
        scraper = Scraper()
        df_net = dfs_dict.get('net_salaries')
        df_ipc = dfs_dict.get('inflation_ipc')
        df_poverty = dfs_dict.get('poverty_lines')
        common_index = df_net.index.intersection(df_ipc.index)
        df_net = df_net.loc[common_index]
        df_ipc = df_ipc.loc[common_index]
        df_poverty = df_poverty.loc[common_index]
        start_limit = df_net.index.min()
        df_real = scraper.calculate_real_salary(df_net, df_ipc['infl_Nivel_general'], base_date=start_limit)
        return {
            "nominal_salaries": df_net,
            "real_salaries": df_real,
            "inflation_ipc": df_ipc,
            "poverty_lines": df_poverty
        }

    def _setup_agent(self):
        llm = ChatLiteLLM(**self.model_params)
        df_list = list(self.dfs_dict.values())
        df_net = self.dfs_dict['nominal_salaries']

        @tool("get_province_salary", args_schema=ProvinceSalaryInput)
        def get_province_salary(province: str, period: str = None) -> str:
            """Get the nominal salary for a SPECIFIC province. Use this for single-province lookups."""
            try:
                province = province.strip(" '\"[]")
                available = df_net.index
                if period and str(period).lower() != "none":
                    tgt = pd.to_datetime(str(period).strip(" '\"[]"))
                    closest = available[available <= tgt].max()
                else:
                    closest = available.max()
                val = df_net.loc[closest, province]
                return f"Nominal salary for {province} in {closest.strftime('%Y-%m')}: ${val:,.2f}"
            except Exception as e:
                return f"Error: {e}. Ensure province name is correct."

        @tool("calculate_purchasing_power_loss", args_schema=PurchasingPowerLossInput)
        def calculate_purchasing_power_loss(start_date: str, end_date: str, province: str = None) -> str:
            """Calculates % change in real salary (purchasing power) between two dates."""
            try:
                df_real = self.dfs_dict['real_salaries']
                s_d = str(start_date).strip(" '\"[]"); e_d = str(end_date).strip(" '\"[]")
                if province and str(province).lower() != "none":
                    prov = str(province).strip(" '\"[]")
                    loss = (df_real.loc[e_d, prov] / df_real.loc[s_d, prov] - 1) * 100
                    return f"Purchasing power change for {prov} ({s_d} to {e_d}): {loss:+.2f}%"
                else:
                    loss_all = (df_real.loc[e_d] / df_real.loc[s_d] - 1) * 100
                    return f"Purchasing power change for all provinces:\n{loss_all.to_string()}"
            except Exception as e: return f"Error: {e}."

        @tool("get_ranking_top_k", args_schema=TopKProvincesInput)
        def get_ranking_top_k(k: int, period: str, asc: bool = False) -> str:
            """Returns a RANKED LIST of provinces. Use ONLY for comparisons like 'Who pays more?'."""
            try:
                tgt = pd.to_datetime(str(period).strip(" '\"[]")); available = df_net.index
                closest = available[available <= tgt].max()
                salaries = df_net.loc[closest].sort_values(ascending=asc)
                salaries = salaries[salaries.index != 'Promedio Ponderado (MG Total)']
                top_k = salaries.head(int(k))
                res = f"{'Bottom' if asc else 'Top'} {k} provinces in {closest.strftime('%Y-%m')}:\n"
                for prov, val in top_k.items(): res += f"- {prov}: ${val:,.2f}\n"
                return res
            except Exception as e: return f"Error: {e}."

        custom_tools = [get_province_salary, calculate_purchasing_power_loss, get_ranking_top_k]
        provinces = list(self.dfs_dict['nominal_salaries'].columns)
        date_min = self.dfs_dict['nominal_salaries'].index.min().strftime('%Y-%m-%d')
        date_max = self.dfs_dict['nominal_salaries'].index.max().strftime('%Y-%m-%d')
        
        prefix = f"""
You are a professional Argentinian Data Journalist. 
Your goal is to provide direct, data-driven answers that are complete yet concise.

STRICT FORMATTING RULE:
Every response MUST follow this exact structure:
Thought: [Your internal reasoning]
Action: [Tool name]
Action Input: {{{{ "arg1": "val1" }}}} <-- VALID JSON
Observation: [Tool result]
...
Final Answer: [Direct response]

TOOL SELECTION RULES:
1. For questions about a SINGLE province, use 'get_province_salary'.
2. For questions about LOSS, GAIN, or EVOLUTION, use 'calculate_purchasing_power_loss'.
3. For questions asking for a RANKING, TOP, or BOTTOM list, use 'get_ranking_top_k'.

DATA SPECS:
- Range: {date_min} to {date_max}.
- Provinces: {", ".join(provinces)}
"""
        agent = create_pandas_dataframe_agent(llm, df_list, verbose=True, allow_dangerous_code=True, prefix=prefix, max_iterations=15, extra_tools=custom_tools, include_df_in_prompt=True, number_of_head_rows=2)
        return agent

    def query(self, user_prompt: str, context_metadata: dict = None, chat_history: list = None):
        metadata_block = f"DASHBOARD FILTERS: {context_metadata}" if context_metadata else ""
        history_block = "RECENT CONVERSATION:\n" + "\n".join([f"{m['role'].upper()}: {m['content']}" for m in chat_history[-3:]]) if chat_history else ""
        full_prompt = f"{metadata_block}\n\n{history_block}\n\nUSER QUESTION: {user_prompt}\n\nINSTRUCTIONS:\n- Use history to identify subjects.\n- ALWAYS use Thought/Final Answer format."
        
        print(f"\n--- [AGENT QUERY START] ---\n{full_prompt}\n---")
        try:
            res = self.agent.invoke({"input": full_prompt})
            print(f"--- [AGENT RESPONSE] ---\n{res.get('output', 'No output')}\n---")
            return res
        except OutputParserException as e:
            output = str(e.llm_output) if hasattr(e, 'llm_output') else str(e)
            output = output.replace("Final Answer:", "").strip()
            print(f"--- [AGENT PARSE ERROR RECOVERY] ---\n{output}\n---")
            return {"output": output}
        except Exception as e:
            if any(x in str(e).lower() for x in ["rate_limit", "429", "quota"]):
                return {"output": "⚠️ **Quota reached.** Please wait 30s."}
            return {"output": f"Error: {str(e)}"}

    def generate_executive_summary(self, lang='es') -> str:
        prompt = "Generate a Markdown executive summary of Argentinian teacher salaries."
        return self.query(prompt).get("output", "Error.")

    def query_and_log(self, question: str, ground_truth: str = None):
        if mlflow.active_run() is None:
            mlflow.start_run(run_name=f"Eval_{self.model_params['model']}")
        res = self.query(question)
        out = res.get("output", "")
        eval_data = {"question": [question], "answer": [out], "ground_truth": [ground_truth], "model": [self.model_params['model']]}
        mlflow.log_table(data=eval_data, artifact_file="eval_results.json")
        return out
