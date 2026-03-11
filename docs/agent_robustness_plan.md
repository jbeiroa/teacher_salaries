# Implementation Plan: Agent Robustness, Evals, and Guardrails - STATUS REPORT

## 1. Objective
Harden the Data Journalist Agent against adversarial inputs, improve response reliability for complex conversational context, and establish an automated evaluation pipeline to measure progress.

## 2. Phase 1: Input Guardrails & UI Race Conditions (COMPLETED ✅)
- **Input Sanitization:** Created `src/salary_data/guardrails.py` with an `InputValidator` class. ✅
- **Heuristic Checks:** Regex-based blocking of common prompt injection patterns and keyword-based relevance "fast pass" for Argentinian economics/provinces. ✅
- **Relevance Filtering:** Using a small local model (e.g., `llama3.2:1b`) via Ollama as a fallback for the heuristic check. ✅
- **UI Locking:** Updated Dash callbacks in `src/salary_app.py` with a clientside/server-side bridge to disable inputs during processing. ✅

## 3. Phase 2: Tool Hardening (COMPLETED ✅)
- **Schema Validation:** Refactored `src/salary_data/agent.py` tools to use LangChain's `args_schema` with Pydantic `BaseModel`. ✅
- **Agent Type Upgrade:** Migrated from legacy ReAct to native `tool-calling` agent for better JSON/parameter handling. ✅
- **Robustness Layer:** Implemented `_parse_input` helper to gracefully handle stringified JSON inputs from LLMs. ✅
- **Feature Extension:** Enhanced `calculate_purchasing_power_loss` to support ranking by change (loss/gain) directly within the tool. ✅
- **Deterministic Tests:** Verified tool and guardrail logic with temporary test scripts. ✅

## 4. Phase 3: Automated Evals (COMPLETED ✅)
- **Dataset Creation:** Build `tests/eval_dataset.jsonl` covering edge cases and context retention. ✅
- **LLM-as-a-Judge:** Update `scripts/run_evaluation.py` to use GPT-4o for grading results on a 0-5 scale. ✅

## 5. Phase 4: Prompt Refinement (COMPLETED ✅)
- **Iterative Tuning:** Adjusted system prompt for identity ("Lia"), multilingual support, and strict date reference handling. ✅
- **Instruction weighting:** Enforced "RECENT CONVERSATION" and "Latest Data Point Available" context. ✅
- **Output Formatting:** Mandated complete-sentence responses including actual data/percentages. ✅
- **Tool Preference & New Tool:** Added `calculate_inflation_change` and explicitly instructed to avoid writing Python code, preferring prewritten tools. ✅
- **Local Model Stability:** Replaced default local testing model with `ollama/llama3.1:8b` to bypass output parsing errors with Qwen tool lists. ✅
