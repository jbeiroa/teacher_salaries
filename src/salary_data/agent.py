from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_litellm import ChatLiteLLM
from langchain_ollama import ChatOllama
from langchain_aws import ChatBedrock
from langchain_core.tools import tool
from salary_data.scraper import Scraper
from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.exceptions import OutputParserException
import pandas as pd
import mlflow
import re

import json

# --- Tool Input Schemas ---


class ProvinceSalaryInput(BaseModel):
    province: str = Field(description="Name of the province.")
    period: Optional[str] = Field(
        None, description="Period in YYYY-MM-DD format. If None, uses latest."
    )


class PurchasingPowerLossInput(BaseModel):
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")
    province: Optional[str] = Field(
        None, description="Province name. If omitted, returns all provinces."
    )
    k: Optional[int] = Field(
        None, description="Number of results to return if ranking all provinces."
    )
    most_loss: bool = Field(
        True,
        description="If True, returns provinces that lost the most. If False, returns those that gained/lost the least.",
    )


class TopKProvincesInput(BaseModel):
    k: int = Field(description="Number of provinces to return in the ranking")
    period: str = Field(description="Target period in YYYY-mm format")
    asc: bool = Field(
        False,
        description="True for bottom-paying ranking (lowest nominal salary), False for top-paying ranking (highest nominal salary)",
    )


class InflationChangeInput(BaseModel):
    start_date: str = Field(description="Start date in YYYY-MM-DD format")
    end_date: str = Field(description="End date in YYYY-MM-DD format")


def _parse_input(input_val: any, target_key: str) -> any:
    """Helper to handle cases where LLM passes a JSON string instead of unpacked args."""
    if isinstance(input_val, str):
        cleaned = input_val.strip(" '\"[]")
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                data = json.loads(cleaned)
                return data.get(target_key, cleaned)
            except Exception:
                return cleaned
    return input_val


class DataJournalistAgent:
    def __init__(self, dfs_dict: dict[str, pd.DataFrame], model_params=None):
        self.model_params = model_params or {
            "model": "ollama/llama3.1:8b",
            "base_url": "http://localhost:11434",
            "temperature": 0,
        }
        self.dfs_dict = self._prepare_data(dfs_dict)
        self.agent = self._setup_agent()

    def _prepare_data(self, dfs_dict):
        scraper = Scraper()
        df_net = dfs_dict.get("net_salaries")
        df_ipc = dfs_dict.get("inflation_ipc")
        df_poverty = dfs_dict.get("poverty_lines")
        df_anomalies = dfs_dict.get("anomalies")

        common_index = df_net.index.intersection(df_ipc.index)
        df_net = df_net.loc[common_index]
        df_ipc = df_ipc.loc[common_index]
        df_poverty = df_poverty.loc[common_index]

        start_limit = df_net.index.min()
        df_real = scraper.calculate_real_salary(
            df_net, df_ipc["infl_Nivel_general"], base_date=start_limit
        )

        return {
            "nominal_salaries": df_net,
            "real_salaries": df_real,
            "inflation_ipc": df_ipc,
            "poverty_lines": df_poverty,
            "anomalies": df_anomalies,
        }

    def _setup_agent(self):
        model_name = self.model_params.get("model", "")
        if model_name.startswith("ollama/"):
            clean_name = model_name.replace("ollama/", "")
            llm = ChatOllama(
                model=clean_name,
                base_url=self.model_params.get("base_url", "http://localhost:11434"),
                temperature=self.model_params.get("temperature", 0),
            )
        elif model_name.startswith("bedrock/"):
            clean_name = model_name.replace("bedrock/", "")
            llm = ChatBedrock(
                model_id=clean_name,
                model_kwargs={"temperature": self.model_params.get("temperature", 0)},
            )
        else:
            llm = ChatLiteLLM(**self.model_params)

        df_list = list(self.dfs_dict.values())
        df_net = self.dfs_dict["nominal_salaries"]

        @tool("get_province_salary", args_schema=ProvinceSalaryInput)
        def get_province_salary(province: str, period: str = None) -> str:
            """Get the nominal salary for a SPECIFIC province. Use this for single-province lookups."""
            try:
                province = _parse_input(province, "province")
                province = province.strip(" '\"[]")
                available = df_net.index

                period_val = _parse_input(period, "period") if period else None
                if period_val and str(period_val).lower() != "none":
                    tgt = pd.to_datetime(str(period_val).strip(" '\"[]"))
                    closest = available[available <= tgt].max()
                else:
                    closest = available.max()

                if province not in df_net.columns:
                    return f"Error: Province '{province}' not found. Available: {', '.join(df_net.columns)}"

                val = df_net.loc[closest, province]
                return f"Nominal salary for {province} in {closest.strftime('%Y-%m')}: ${val:,.2f}"
            except Exception as e:
                return f"Error: {e}. Ensure province name is correct."

        @tool("calculate_purchasing_power_loss", args_schema=PurchasingPowerLossInput)
        def calculate_purchasing_power_loss(
            start_date: str,
            end_date: str,
            province: str = None,
            k: int = None,
            most_loss: bool = True,
        ) -> str:
            """Calculates % change in real salary (purchasing power) between two dates.
            Use this for ALL questions about EVOLUTION, LOSS, GAIN, or RANKING BY CHANGE over time."""
            try:
                df_real = self.dfs_dict["real_salaries"]
                s_d = _parse_input(start_date, "start_date")
                e_d = _parse_input(end_date, "end_date")
                prov = _parse_input(province, "province") if province else None
                k_val = _parse_input(k, "k") if k else None
                most_loss_val = _parse_input(most_loss, "most_loss")

                s_d = str(s_d).strip(" '\"[]")
                e_d = str(e_d).strip(" '\"[]")

                # Align dates to available indices
                available = df_real.index
                s_date = available[available >= pd.to_datetime(s_d)].min()
                e_date = available[available <= pd.to_datetime(e_d)].max()

                if prov and str(prov).lower() != "none":
                    prov = str(prov).strip(" '\"[]")
                    loss = (
                        df_real.loc[e_date, prov] / df_real.loc[s_date, prov] - 1
                    ) * 100
                    return f"Purchasing power change for {prov} ({s_date.strftime('%Y-%m')} to {e_date.strftime('%Y-%m')}): {loss:+.2f}%"
                else:
                    loss_all = (df_real.loc[e_date] / df_real.loc[s_date] - 1) * 100
                    loss_all = loss_all[
                        loss_all.index != "Promedio Ponderado (MG Total)"
                    ]

                    if k_val:
                        # Sort: If most_loss is True, we want the lowest % changes (most negative) at the top.
                        sorted_loss = loss_all.sort_values(
                            ascending=bool(most_loss_val)
                        )
                        top_k = sorted_loss.head(int(k_val))
                        res = f"{'Worst' if most_loss_val else 'Best'} {k_val} provinces in purchasing power change ({s_date.strftime('%Y-%m')} to {e_date.strftime('%Y-%m')}):\n"
                        for p, v in top_k.items():
                            res += f"- {p}: {v:+.2f}%\n"
                        return res

                    return f"Purchasing power change for all provinces ({s_date.strftime('%Y-%m')} to {e_date.strftime('%Y-%m')}):\n{loss_all.to_string()}"
            except Exception as e:
                return f"Error: {e}."

        @tool("get_ranking_top_k", args_schema=TopKProvincesInput)
        def get_ranking_top_k(k: int, period: str, asc: bool = False) -> str:
            """Returns a RANKED LIST of provinces by NOMINAL salary at a SINGLE POINT IN TIME.
            Use ONLY for 'Who pays more/less RIGHT NOW?' questions.
            DO NOT use for 'Who lost/gained more?' (use calculate_purchasing_power_loss instead)."""
            try:
                k_val = _parse_input(k, "k")
                period_val = _parse_input(period, "period")
                asc_val = _parse_input(asc, "asc")

                tgt = pd.to_datetime(str(period_val).strip(" '\"[]"))
                available = df_net.index
                closest = available[available <= tgt].max()
                salaries = df_net.loc[closest].sort_values(ascending=bool(asc_val))
                salaries = salaries[salaries.index != "Promedio Ponderado (MG Total)"]
                top_k = salaries.head(int(k_val))
                res = f"{'Bottom' if asc_val else 'Top'} {k_val} provinces in {closest.strftime('%Y-%m')}:\n"
                for prov, val in top_k.items():
                    res += f"- {prov}: ${val:,.2f}\n"
                return res
            except Exception as e:
                return f"Error: {e}."

        @tool("calculate_inflation_change", args_schema=InflationChangeInput)
        def calculate_inflation_change(start_date: str, end_date: str) -> str:
            """Calculates the percentage change in the general inflation index (IPC) between two dates.
            Use this when you need to compare salary evolution against inflation, or when asked directly about inflation."""
            try:
                df_ipc = self.dfs_dict["inflation_ipc"]
                s_d = _parse_input(start_date, "start_date")
                e_d = _parse_input(end_date, "end_date")

                s_d = str(s_d).strip(" '\"[]")
                e_d = str(e_d).strip(" '\"[]")

                available = df_ipc.index
                s_date = available[available >= pd.to_datetime(s_d)].min()
                e_date = available[available <= pd.to_datetime(e_d)].max()

                start_val = df_ipc.loc[s_date, "infl_Nivel_general"]
                end_val = df_ipc.loc[e_date, "infl_Nivel_general"]
                inflation_change = (end_val / start_val - 1) * 100
                return f"Inflation (IPC) change from {s_date.strftime('%Y-%m')} to {e_date.strftime('%Y-%m')}: {inflation_change:+.2f}%"
            except Exception as e:
                return f"Error: {e}."

        custom_tools = [
            get_province_salary,
            calculate_purchasing_power_loss,
            get_ranking_top_k,
            calculate_inflation_change,
        ]
        provinces = list(self.dfs_dict["nominal_salaries"].columns)
        date_min = self.dfs_dict["nominal_salaries"].index.min().strftime("%Y-%m-%d")
        date_max = self.dfs_dict["nominal_salaries"].index.max().strftime("%Y-%m-%d")

        prefix = f"""
You are "Lia", the AI Data Journalist for the Teacher Salaries Dashboard.
Your persona is professional, helpful, and data-driven. 

IDENTITY & CONTEXT:
- If asked "Who are you?" or "What can you do?", explain that you are an assistant designed to analyze Argentinian teacher salaries, inflation, provincial data, and anomalies (unusual drops or gains in real salary) using the dashboard's datasets.
- Always be polite and professional.

TOOL SELECTION RULES:
1. TOOL PREFERENCE: Always prefer using the provided custom tools (`calculate_purchasing_power_loss`, `calculate_inflation_change`, `get_province_salary`, `get_ranking_top_k`). Only write your own Python code if a specific task cannot be accomplished with these tools.
2. FOR EVOLUTION / CHANGE OVER TIME: Always use 'calculate_purchasing_power_loss' for salaries. If asked to compare against inflation, use 'calculate_inflation_change'.
3. FOR SNAPSHOTS / CURRENT STATE: Use 'get_ranking_top_k' only to compare salaries at a single point in time (e.g., "highest salary in Jan 2024").
4. FOR SINGLE PROVINCE: Use 'get_province_salary'.

LANGUAGE & OUTPUT RULES:
1. RESPONSE LANGUAGE: Match the user's language (Spanish for Spanish, English for English).
2. DATE CLARITY: ALWAYS mention the exact date range (YYYY-MM) in your final answer.
3. RELATIVE DATES: Treat "last year" or "last X years" relative to the "Latest Data Point Available" provided in the context.
4. COMPLETE SENTENCES: Always include the DATA (numbers/percentages) in a natural sentence. 
5. PERCENTAGES: When discussing loss or gain, ALWAYS include the percentage (%) provided by the tool.

BEHAVIORAL RULES:
1. For general conversation or identity questions, respond DIRECTLY without using tools.
2. EDGE CASES: If a user asks about a province or location not in the dataset (e.g., fictional places like "Narnia"), politely state that it is not a valid province instead of using tools.
3. ALWAYS provide a clear, conversational answer to the user.

DATA SPECS:
- Range: {date_min} to {date_max}.
- Provinces: {", ".join(provinces)}
"""
        agent = create_pandas_dataframe_agent(
            llm,
            df_list,
            verbose=True,
            allow_dangerous_code=True,
            prefix=prefix,
            max_iterations=15,
            extra_tools=custom_tools,
            include_df_in_prompt=True,
            number_of_head_rows=2,
            agent_type="tool-calling",
        )
        return agent

    def query(
        self, user_prompt: str, context_metadata: dict = None, chat_history: list = None
    ):
        import datetime

        now = datetime.datetime.now().strftime("%Y-%m-%d")
        date_max = self.dfs_dict["nominal_salaries"].index.max().strftime("%Y-%m-%d")

        metadata_block = (
            f"DASHBOARD FILTERS: {context_metadata}" if context_metadata else ""
        )
        lang = (
            context_metadata.get("language_preference", "es")
            if context_metadata
            else "es"
        )
        history_block = (
            "RECENT CONVERSATION:\n"
            + "\n".join(
                [f"{m['role'].upper()}: {m['content']}" for m in chat_history[-3:]]
            )
            if chat_history
            else ""
        )

        full_prompt = f"""
{metadata_block}

{history_block}

CONTEXT:
- Today's Date: {now}
- Latest Data Point Available: {date_max}

USER QUESTION: {user_prompt}

INSTRUCTIONS:
- When asked for "last year", "last two years", or relative dates, use the "Latest Data Point Available" ({date_max}) as the most recent reference.
- ALWAYS state the exact date range (YYYY-MM to YYYY-MM) used in your Final Answer.
- Respond in {lang.upper()} (matching the user's current question language).
- Provide a concise, complete-sentence answer.
"""

        print(f"\n--- [AGENT QUERY START] ---\n{full_prompt}\n---")
        try:
            res = self.agent.invoke({"input": full_prompt})
            ans = res.get("output", "")

            # --- Output Cleaning ---
            # Remove "Final Answer:" label if present
            if "Final Answer:" in ans:
                ans = ans.split("Final Answer:")[-1].strip()

            # Remove leading "Thought:" sections that might have leaked
            # This regex looks for "Thought:" at the start of the string or after a newline,
            # and removes it along with everything until the next double newline or the end.
            ans = re.sub(
                r"(^|\n)Thought:.*?\n(\n|$)", "\n", ans, flags=re.DOTALL | re.IGNORECASE
            ).strip()
            ans = re.sub(r"^Thought:.*", "", ans, flags=re.IGNORECASE).strip()

            res["output"] = ans
            print(f"--- [AGENT RESPONSE (CLEAN)] ---\n{ans}\n---")
            return res
        except OutputParserException as e:
            output = str(e.llm_output) if hasattr(e, "llm_output") else str(e)
            # Recovery cleaning
            if "Final Answer:" in output:
                output = output.split("Final Answer:")[-1]
            output = re.sub(r"^Thought:.*?\n", "", output, flags=re.IGNORECASE).strip()

            print(f"--- [AGENT PARSE ERROR RECOVERY] ---\n{output}\n---")
            return {"output": output.strip()}
        except Exception as e:
            if any(x in str(e).lower() for x in ["rate_limit", "429", "quota"]):
                return {"output": "⚠️ **Quota reached.** Please wait 30s."}
            return {"output": f"Error: {str(e)}"}

    def generate_executive_summary(self, lang="es") -> str:
        """Generates a data-driven executive summary with macro indicators and tabular salary comparison."""
        df_net = self.dfs_dict["nominal_salaries"]
        df_real = self.dfs_dict["real_salaries"]
        df_ipc = self.dfs_dict["inflation_ipc"]
        df_poverty = self.dfs_dict["poverty_lines"]

        last_date = df_net.index.max()
        prev_quarter = last_date - pd.DateOffset(months=3)
        prev_year = last_date - pd.DateOffset(years=1)

        # Annual accumulated (YTD): from Dec of previous year
        dec_prev_year_date = pd.Timestamp(year=last_date.year - 1, month=12, day=1)
        if dec_prev_year_date not in df_net.index:
            dec_prev_year_date = df_net.index[df_net.index <= dec_prev_year_date].max()

        # Formatting helpers
        def f_curr(v):
            return f"${v:,.0f}"

        def f_pct(v):
            return f"{v * 100:+.1f}%"

        # Localized date formatting helper
        def f_date(dt, lang):
            months_es = {
                1: "Enero",
                2: "Febrero",
                3: "Marzo",
                4: "Abril",
                5: "Mayo",
                6: "Junio",
                7: "Julio",
                8: "Agosto",
                9: "Septiembre",
                10: "Octubre",
                11: "Noviembre",
                12: "Diciembre",
            }
            if lang == "es":
                return f"{months_es[dt.month]} {dt.year}"
            return dt.strftime("%B %Y")

        # --- Macroeconomic Table ---
        # IPC (General), CBT (Family 4), CBA (Family 4)
        ipc_col = "infl_Nivel_general"
        cbt_col = "linea_pobreza"
        cba_col = "linea_indigencia"

        macro_data = []
        for label, col, df in [
            ("IPC", ipc_col, df_ipc),
            ("CBT (Pobreza)", cbt_col, df_poverty),
            ("CBA (Indigencia)", cba_col, df_poverty),
        ]:
            if col in df.columns:
                q_var = (df.loc[last_date, col] / df.loc[prev_quarter, col]) - 1
                ytd_var = (df.loc[last_date, col] / df.loc[dec_prev_year_date, col]) - 1
                i_var = (df.loc[last_date, col] / df.loc[prev_year, col]) - 1

                row_label = (
                    label
                    if lang == "es"
                    else label.replace("Pobreza", "Poverty").replace(
                        "Indigencia", "Indigency"
                    )
                )
                macro_data.append(
                    {
                        "Indicator" if lang == "en" else "Indicador": row_label,
                        "Last Quarter" if lang == "en" else "Últ. Trimestre": f_pct(
                            q_var
                        ),
                        "Annual Acc." if lang == "en" else "Acum. Anual": f_pct(
                            ytd_var
                        ),
                        "Interannual" if lang == "en" else "Interanual": f_pct(i_var),
                    }
                )

        df_macro_table = pd.DataFrame(macro_data)
        last_cbt = f_curr(df_poverty.loc[last_date, cbt_col])
        last_cba = f_curr(df_poverty.loc[last_date, cba_col])

        # --- Salary Table ---
        summary_df = pd.DataFrame(index=df_net.columns)
        summary_df["Last Net Salary"] = df_net.loc[last_date]

        # Nominal variations
        summary_df["Nom Q"] = (df_net.loc[last_date] / df_net.loc[prev_quarter]) - 1
        summary_df["Nom YTD"] = (
            df_net.loc[last_date] / df_net.loc[dec_prev_year_date]
        ) - 1
        summary_df["Nom I"] = (df_net.loc[last_date] / df_net.loc[prev_year]) - 1

        # Real variations
        summary_df["Real Q"] = (df_real.loc[last_date] / df_real.loc[prev_quarter]) - 1
        summary_df["Real YTD"] = (
            df_real.loc[last_date] / df_real.loc[dec_prev_year_date]
        ) - 1
        summary_df["Real I"] = (df_real.loc[last_date] / df_real.loc[prev_year]) - 1

        summary_df = summary_df.sort_values(by="Last Net Salary", ascending=False)

        # Real Salary Drop (Average YoY) for insights
        real_drop_avg = summary_df["Real I"].mean()

        # Table Formatting for Salary
        display_df = pd.DataFrame(index=summary_df.index)
        display_df["Last Net Salary" if lang == "en" else "Últ. Salario Neto"] = (
            summary_df["Last Net Salary"].apply(f_curr)
        )

        real_label = "Real" if lang == "en" else "Real"
        display_df["Quarterly Var." if lang == "en" else "Var. Trimestral"] = [
            f"{f_pct(n)} ({real_label}: {f_pct(r)})"
            for n, r in zip(summary_df["Nom Q"], summary_df["Real Q"])
        ]
        display_df["Annual Acc. Var." if lang == "en" else "Var. Acum. Anual"] = [
            f"{f_pct(n)} ({real_label}: {f_pct(r)})"
            for n, r in zip(summary_df["Nom YTD"], summary_df["Real YTD"])
        ]
        display_df["Interannual Var." if lang == "en" else "Var. Interanual"] = [
            f"{f_pct(n)} ({real_label}: {f_pct(r)})"
            for n, r in zip(summary_df["Nom I"], summary_df["Real I"])
        ]
        display_df.index.name = "Province" if lang == "en" else "Provincia"

        # Insights
        top_province = summary_df.index[0]
        bottom_province = summary_df.index[-1]
        gap = summary_df["Last Net Salary"].max() / summary_df["Last Net Salary"].min()
        max_var_prov = summary_df["Nom I"].idxmax()
        min_var_prov = summary_df["Nom I"].idxmin()

        if lang == "es":
            report = f"""# Resumen Ejecutivo sobre los Salarios de los Docentes en Argentina

Entre diciembre de 2016 y {f_date(last_date, "es")} ({df_net.index.min().strftime("%Y-%m")} a {last_date.strftime("%Y-%m")}), los salarios de los docentes en Argentina han experimentado variaciones significativas. 

### Indicadores Macroeconómicos ({f_date(last_date, "es")})
Últimos valores de referencia (Canasta para familia de 4):
*   **Línea de Pobreza (CBT):** {last_cbt}
*   **Línea de Indigencia (CBA):** {last_cba}

{df_macro_table.to_markdown(index=False)}

### Evolución del Poder Adquisitivo
Durante el último año, desde {f_date(prev_year, "es")} hasta {f_date(last_date, "es")}, los salarios reales han bajado **{abs(real_drop_avg) * 100:.1f}%** en promedio. Esta caída refleja que los ajustes salariales no han logrado compensar el aumento sostenido del IPC.

### Tabla de Salarios y Variaciones ({f_date(last_date, "es")})
La siguiente tabla detalla la situación salarial por jurisdicción, ordenada por el salario neto más reciente. Las variaciones muestran el cambio nominal seguido del ajuste real (poder de compra) entre paréntesis.

{display_df.reset_index().to_markdown(index=False)}

### Hallazgos Clave
*   **Brecha Federal:** Existe una diferencia de **{gap:.1f} veces** entre el salario más alto ({top_province}: {f_curr(summary_df["Last Net Salary"].max())}) y el más bajo ({bottom_province}: {f_curr(summary_df["Last Net Salary"].min())}).
*   **Variación Interanual:** Mientras que **{max_var_prov}** registró el mayor incremento nominal interanual ({f_pct(summary_df["Nom I"].max())}), **{min_var_prov}** tuvo el ajuste más bajo ({f_pct(summary_df["Nom I"].min())}).
*   **Dinámica Trimestral:** El promedio de ajuste trimestral para todas las provincias fue de **{summary_df["Nom Q"].mean() * 100:.1f}%**, con variaciones que oscilan entre el {f_pct(summary_df["Nom Q"].min())} y el {f_pct(summary_df["Nom Q"].max())}.

Los datos reflejan un panorama complejo donde, a pesar de los aumentos nominales, el poder adquisitivo real sigue bajo presión en todo el territorio nacional.
"""
        else:
            report = f"""# Executive Summary: Teacher Salaries in Argentina

Between December 2016 and {f_date(last_date, "en")} ({df_net.index.min().strftime("%Y-%m")} to {last_date.strftime("%Y-%m")}), teacher salaries in Argentina have undergone significant variations.

### Macroeconomic Indicators ({f_date(last_date, "en")})
Reference values (Basket for a family of 4):
*   **Poverty Line (CBT):** {last_cbt}
*   **Indigency Line (CBA):** {last_cba}

{df_macro_table.to_markdown(index=False)}

### Purchasing Power Evolution
Over the last year, from {f_date(prev_year, "en")} to {f_date(last_date, "en")}, real salaries have decreased by **{abs(real_drop_avg) * 100:.1f}%** on average. This decline reflects that salary adjustments have not managed to compensate for the sustained increase in the IPC.

### Salary and Variations Table ({f_date(last_date, "en")})
The following table details the salary situation by jurisdiction, sorted by the most recent net salary. Variations show the nominal change followed by the real adjustment (purchasing power) in parentheses.

{display_df.reset_index().to_markdown(index=False)}

### Key Findings
*   **Federal Gap:** There is a difference of **{gap:.1f} times** between the highest salary ({top_province}: {f_curr(summary_df["Last Net Salary"].max())}) and the lowest ({bottom_province}: {f_curr(summary_df["Last Net Salary"].min())}).
*   **Interannual Variation:** While **{max_var_prov}** recorded the highest interannual nominal increase ({f_pct(summary_df["Nom I"].max())}), **{min_var_prov}** had the lowest adjustment ({f_pct(summary_df["Nom I"].min())}).
*   **Quarterly Dynamics:** The average quarterly adjustment for all provinces was **{summary_df["Nom Q"].mean() * 100:.1f}%**, with variations ranging between {f_pct(summary_df["Nom Q"].min())} and {f_pct(summary_df["Nom Q"].max())}.

The data reflects a complex landscape where, despite nominal increases, real purchasing power remains under pressure throughout the national territory.
"""
        return report

    def query_and_log(
        self, question: str, ground_truth: str = None, chat_history: list = None
    ):
        if mlflow.active_run() is None:
            mlflow.start_run(run_name=f"Eval_{self.model_params['model']}")
        res = self.query(question, chat_history=chat_history)
        out = res.get("output", "")
        eval_data = {
            "question": [question],
            "answer": [out],
            "ground_truth": [ground_truth],
            "model": [self.model_params["model"]],
        }
        mlflow.log_table(data=eval_data, artifact_file="eval_results.json")
        return out
