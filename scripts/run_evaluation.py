import mlflow
import sys
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from salary_data.scraper import Scraper
from salary_data.agent import DataJournalistAgent
from dotenv import load_dotenv

load_dotenv()


def grade_response(question, agent_answer, ground_truth):
    """Uses LLM-as-a-judge to score the answer from 0 to 5."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = PromptTemplate.from_template(
        "You are an expert evaluator. Score the following AI agent's answer against the expected ground truth from 0 to 5.\n"
        "5 = Perfect accuracy, follows all instructions, includes actual numbers/percentages.\n"
        "0 = Completely incorrect, hallucinates, or completely ignores the prompt formatting.\n\n"
        "Question: {question}\n"
        "Agent Answer: {agent_answer}\n"
        "Ground Truth: {ground_truth}\n\n"
        "Provide your evaluation in JSON format with two keys: 'score' (an integer from 0 to 5) and 'reasoning' (a string explaining why).\n"
    )
    chain = prompt | llm
    try:
        response = chain.invoke(
            {
                "question": question,
                "agent_answer": agent_answer,
                "ground_truth": ground_truth,
            }
        )
        # Parse the JSON response
        result_str = response.content.strip()
        if result_str.startswith("```json"):
            result_str = result_str[7:]
        if result_str.endswith("```"):
            result_str = result_str[:-3]
        result_str = result_str.strip()

        result_dict = json.loads(result_str)
        return result_dict.get("score", 0), result_dict.get(
            "reasoning", "Failed to parse reasoning"
        )
    except Exception as e:
        print(f"Error grading response: {e}")
        return 0, str(e)


def run_evaluation():
    # 1. Setup Data
    scraper = Scraper()
    df_net = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO)
    df_ipc = scraper.get_ipc_indec()
    df_poverty = scraper.get_cba_cbt()

    dfs_dict = {
        "net_salaries": df_net,
        "inflation_ipc": df_ipc,
        "poverty_lines": df_poverty,
    }

    # 2. Load Evaluation Cases
    eval_cases = []
    dataset_path = os.path.join(
        os.path.dirname(__file__), "..", "tests", "eval_dataset.jsonl"
    )
    with open(dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                eval_cases.append(json.loads(line))

    # 3. Models to Evaluate
    models = [
        {"model": "openai/gpt-4o-mini"},
        # Removing ollama model for speed during automated evaluation if needed, or keep it:
        {"model": "ollama/llama3.1:8b", "base_url": "http://localhost:11434"},
    ]

    mlflow.set_experiment("Agent_Comparison_March_2026")

    for m_params in models:
        print(f"\n>>> Evaluating Model: {m_params['model']}")
        m_params["temperature"] = 0

        agent = DataJournalistAgent(dfs_dict, model_params=m_params)

        # Start a single run for the entire model evaluation
        with mlflow.start_run(run_name=f"Model_{m_params['model'].split('/')[-1]}"):
            mlflow.log_params(m_params)

            total_score = 0

            for i, case in enumerate(eval_cases):
                print(f"[{i + 1}/{len(eval_cases)}] Question: {case['q']}")
                try:
                    chat_history = case.get("history", [])
                    out = agent.query_and_log(
                        case["q"], ground_truth=case["gt"], chat_history=chat_history
                    )

                    # Grade the response
                    score, reasoning = grade_response(case["q"], out, case["gt"])
                    total_score += score

                    print(f"Answer: {out}")
                    print(f"Score: {score}/5. Reasoning: {reasoning}\n")

                    mlflow.log_metric(f"score_case_{i}", score)

                except Exception as e:
                    print(f"Error in query: {e}")
                    continue

            avg_score = total_score / len(eval_cases) if eval_cases else 0
            mlflow.log_metric("average_score", avg_score)
            print(f"Model Average Score: {avg_score:.2f}/5")

    print("\n--- Evaluation Complete ---")
    print("Run 'mlflow ui' to see results.")


if __name__ == "__main__":
    run_evaluation()
