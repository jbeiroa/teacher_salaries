# Teacher Salaries Dashboard - Argentina

An interactive web application built with **Dash** to visualize and analyze teacher salary data (category MG10) across Argentina, featuring dynamic inflation adjustment and provincial benchmarking.

## Key Features

- **MG10 Benchmark:** Analyzes data for the "Maestro de Grado" position with 10 years of seniority.
- **Advanced Inflation Adjustment:** Select specific inflation categories (Food, Housing, etc.) and a custom **Base Date** for real salary calculations.
- **Reference Lines:** Overlay Poverty and Indigency lines (CBA/CBT) for both individual adults and standard families.
- **Advanced Analytics (Machine Learning):**
    - **Behavioral Clustering:** Provinces grouped into 6 archetypes using the **KShape** algorithm to identify patterns of resilience, erosion, and volatility.
    - **Anomaly Detection:** Automatic flagging of sharp purchasing power drops (⚠️) or exceptional gains (✨) using **Isolation Forest**.
    - **Research Deep Dive:** Interactive tab featuring a comprehensive fiscal analysis report integrated with cluster-specific visualizations.
- **Bilingual Support:** Full interface available in **Spanish** (default) and **English** with localized number formatting.
- **Interactive Visualizations:** Historical trends (Nominal vs. Real), **Base 100 Indexing**, and ranked provincial comparisons.

## Quick Start

### Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/)

### Setup
1. Clone the repository.
2. Install dependencies:
   ```bash
   poetry install
   ```

### Running the Application
1. **Train the Analytics Module:** (Optional but recommended to generate latest insights)
   ```bash
   poetry run python train_analytics.py
   ```
2. **Start the Dash server:**
   ```bash
   poetry run python src/salary_app.py
   ```
Access the dashboard at `http://127.0.0.1:8050`.

### Running Tests
Execute the test suite with:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
poetry run pytest
```

## Project Structure

- `src/salary_app.py`: Main entry point and dashboard UI logic.
- `src/salary_data/scraper.py`: Data fetching and cleaning module.
- `src/salary_data/analytics.py`: ML Pipeline for clustering and anomaly detection.
- `train_analytics.py`: CLI script to execute the ML training and register models.
- `reports/`: Narrative research reports consumed by the dashboard.
- `docs/`: Detailed documentation for the scraper and application.
- `tests/`: Automated unit tests using `pytest`.

## Tech Stack
- **MLOps:** MLflow (Experiment tracking and Model Registry).
- **Time Series ML:** `tslearn` (KShape), `scikit-learn` (Isolation Forest).
- **Dashboard:** Plotly Dash, Bootstrap Components.

## Data Sources
- **Salaries:** CGECSE (Ministerio de Educación).
- **Inflation:** INDEC (Instituto Nacional de Estadística y Censos).
- **Poverty Lines:** datos.gob.ar.

## License
MIT
