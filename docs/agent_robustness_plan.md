# Implementation Plan: Agent Robustness, Evals, and Guardrails

## 1. Objective
Harden the Data Journalist Agent against adversarial inputs, improve response reliability for complex conversational context, and establish an automated evaluation pipeline to measure progress.

## 2. Phase 1: Input Guardrails & UI Race Conditions
- **Input Sanitization:** Create `src/salary_data/guardrails.py` with an `InputValidator` class.
- **Heuristic Checks:** Regex-based blocking of common prompt injection patterns.
- **Relevance Filtering:** Use a small local model (e.g., `llama3.2:1b` or `3b`) via Ollama to classify if a query is related to Argentinian economics/salaries.
- **UI Locking:** Update Dash callbacks in `src/salary_app.py` to disable the chat input and send button while a query is pending.

## 3. Phase 2: Tool Hardening (Pydantic)
- **Schema Validation:** Refactor `src/salary_data/agent.py` tools to use LangChain's `args_schema` with Pydantic `BaseModel`.
- **Error Feedback:** Ensure validation errors are passed back to the LLM as a tool observation so it can self-correct the input format.
- **Deterministic Tests:** Create `tests/test_agent_tools.py` to verify calculation logic.

## 4. Phase 3: Automated Evals (MLflow)
- **Dataset Creation:** Build `tests/eval_dataset.jsonl` covering:
    - Subject retention (context).
    - Subject switching.
    - Geographic mapping (Rosario -> Santa Fe).
    - Date fuzziness (Jan -> closest prev Dec).
    - Adversarial attempts.
- **LLM-as-a-Judge:** Update `scripts/run_evaluation.py` to use a high-tier model (GPT-4o) to grade the agent's performance on a 0-5 scale based on accuracy, context, and safety.

## 5. Phase 4: Prompt Refinement
- **Iterative Tuning:** Adjust the agent's system prompt based on evaluation results.
- **Instruction weighting:** Ensure "RECENT CONVERSATION" instructions are strictly followed.
