# Implementation Plan: The "Data Journalist" Agent

This document outlines the architecture and implementation steps for integrating a GenAI-powered "Data Journalist" into the Teacher Salaries Dashboard.

## 1. Objective
Allow users to query teacher salary data using natural language and receive automated insights, including a downloadable executive summary in Markdown format.

## 2. Tech Stack
- **Model Gateway:** [LiteLLM](https://docs.litellm.ai/) (Proxy for Gemini 1.5 Pro).
- **Agent Framework:** [LangChain](https://python.langchain.com/) `create_pandas_dataframe_agent`.
- **LLM:** [Google Gemini 1.5 Pro](https://ai.google.dev/).
- **UI:** [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/) (`dbc.Offcanvas`).

## 3. Dependencies to Add
Run the following command to update `pyproject.toml`:
```bash
poetry add langchain langchain-community litellm python-dotenv google-generativeai
```

## 4. File Structure Changes
- `src/salary_data/agent.py`: (New) Backend logic for the LangChain agent.
- `src/components/chat_interface.py`: (New) Dash UI components for the sidebar.
- `src/salary_app.py`: (Modify) Integration of the sidebar and callbacks.
- `.env`: (New) Storage for `GOOGLE_API_KEY`.

## 5. Backend Agent Logic (`src/salary_data/agent.py`)

### Class: `DataJournalistAgent`

#### Methods:
- `__init__(self, dfs_dict)`: Initializes the agent with a dictionary of dataframes (`df_net_salary`, `df_ipc`, `df_cba_cbt`).
- `_setup_agent(self)`: Configures the `create_pandas_dataframe_agent` using LiteLLM and Gemini 1.5 Pro.
- `query(self, user_prompt, context_metadata)`: 
    - Executes a natural language query.
    - `context_metadata` includes current filters (selected province, salary type, date range) to provide grounded answers.
- `generate_executive_summary(self, lang='es')`:
    - Triggers a specialized prompt to synthesize a full Markdown report based on recent trends and anomalies.

## 6. UI Component Design (`src/components/chat_interface.py`)

### Component: `ChatSidebar`
- **Container:** `dbc.Offcanvas` (placed at the right of the screen).
- **Header:** "Data Journalist / Periodista de Datos".
- **Body:**
    - `html.Div`: Scrollable chat history container.
    - `dbc.InputGroup`: Text input + "Send" button.
    - `dbc.Button`: "Download Executive Summary" with `dcc.Download`.
- **States:** `dcc.Store` to persist chat history during the session.

## 7. Pipeline Flow

1.  **User Input:** User types a question in the Sidebar (e.g., "Which province had the worst loss of purchasing power in 2024?").
2.  **Callback Trigger:** A Dash callback sends the input + current UI state (province, date range) to the `DataJournalistAgent`.
3.  **Agent Execution:**
    - LangChain agent analyzes the local dataframes.
    - Generates Python code internally to calculate statistics if needed.
    - Returns a natural language response.
4.  **UI Update:** The response is appended to the chat history and displayed in the Sidebar.
5.  **Report Generation:** If the user clicks "Download Executive Summary", the agent generates a Markdown file, which is served via `dcc.Download`.

## 8. Execution Order

1.  **Setup Environment:**
    - Install new dependencies.
    - Create `.env` file with `GOOGLE_API_KEY`.
2.  **Implement Backend Agent:**
    - Create `src/salary_data/agent.py`.
    - Test agent logic in new `test_agent.ipynb` using local dataframes.
3.  **Implement UI Components:**
    - Create `src/components/chat_interface.py`.
    - Style with `src/assets/style.css`.
4.  **Integrate Callbacks:**
    - Add chat and download callbacks to `src/salary_app.py`.
    - Ensure dataframes are passed correctly to the agent instance.
5.  **Testing & Refinement:**
    - Verify the agent handles Spanish and English queries.
    - Ensure the "Executive Summary" respects the current user filters.
    - Verify health of downloaded dataframes as .csv or .xlsx files.
