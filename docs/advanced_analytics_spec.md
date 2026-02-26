# Technical Specification: Advanced Analytics Module (v1.1)

## 1. Objective
Enhance the dashboard with data science insights to identify provincial salary archetypes and detect critical purchasing power losses or exceptional gains using Machine Learning.

## 2. Analytical Core
### A. Behavioral Clustering (KShape)
*   **Goal:** Group provinces by the "shape" of their real salary signal, identifying shared rhythms of adjustment.
*   **Algorithm:** **KShape** (via `tslearn`). Chosen for its scale-invariance and effectiveness at capturing temporal patterns in economic series.
*   **Number of Clusters:** $K=6$ (determined via elbow method on inertia).
*   **Archetypes:**
    *   Cluster 0: Bono Dependency (Sawtooth pattern).
    *   Cluster 1: Eroded Center (Permanent step-down).
    *   Cluster 5: Resource-Based Recovery (Oil/Mining/Services).

### B. Anomaly Detection (Isolation Forest)
*   **Goal:** Flag "Anomalous Real Salary Changes."
*   **Algorithm:** **Isolation Forest**.
*   **Input Features:** 3-month rolling real salary percentage change.
*   **Output:** Binary flag (-1 for anomaly). Dash app interprets as ⚠️ (Drop) or ✨ (Spike) based on the sign of the variation.

## 3. Infrastructure & MLOps
*   **Experiment Tracking:** **MLflow** with a local SQLite backend (`mlflow.db`).
*   **Model Registry:** Best models are registered as `KShape_TeacherSalaries_Prod`.
*   **Artifacts:** Dashboard loads `clusters.parquet` and `anomalies.parquet` from the latest production run.

## 4. Architecture
*   `src/salary_data/analytics.py`: `AnalyticsPipeline` class for training, artifact generation, and loading.
*   **Data Flow:** `Scraper` -> `AnalyticsPipeline` -> `MLflow` -> `Dash App`.

## 5. UI/UX Integration (Multi-page App)
*   **Main Dashboard:**
    *   **Bar Chart:** Highlights anomalous provinces with icons (⚠️/✨) directly on the Y-axis labels.
    *   **KPI Cards:** Display nominal vs. inflation context alongside real results.
*   **Advanced Analytics Tab:**
    *   **Deep Dive Report:** Narrative analysis intercalated with cluster-specific line plots.
    *   **Automatic Parsing:** Report dynamically loaded from `reports/cluster_analysis_report.md`.

## 6. Workflow & Testing
*   `test_ground.ipynb`: Reserved for scraper and data source testing.
*   `test_analytics.ipynb` (New): Dedicated for prototyping the ML pipeline, tuning DTW windows, and Isolation Forest contamination parameters.
*   `train_analytics.py`: CLI script to run the pipeline and update the "Production" model in MLflow.
