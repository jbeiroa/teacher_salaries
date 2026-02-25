# Project Overview

The **Teacher Salaries Dashboard** is a Python-based web application designed to visualize and analyze teacher salary data in Argentina. The project fetches data directly from the [Coordinación General de Estudio de Costos del Sistema Educativo (CGECSE)](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/series-salario-docente) and [INDEC](https://www.indec.gob.ar/).

## Main Technologies
- **Framework:** [Dash](https://dash.plotly.com/) (React-based Python framework for analytical web apps)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Machine Learning:** [tslearn](https://tslearn.readthedocs.io/) (KShape), [scikit-learn](https://scikit-learn.org/) (Isolation Forest)
- **Experiment Tracking:** [MLflow](https://mlflow.org/) (Local SQLite backend)
- **Visualization:** [Plotly Express](https://plotly.com/python/plotly-express/)
- **Dependency Management:** [Poetry](https://python-poetry.org/)
- **Scraping/Data Fetching:** [Requests](https://requests.readthedocs.io/), [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/), [Openpyxl](https://openpyxl.readthedocs.io/)

## Architecture
- `src/salary_app.py`: The main entry point of the Dash application. It defines the layout, callbacks, and server configuration. Now features a tabbed interface with Advanced Analytics.
- `src/salary_data/scraper.py`: Contains the `Scraper` class responsible for downloading data from government portals.
- `src/salary_data/analytics.py`: Contains the `AnalyticsPipeline` class for KShape clustering and Isolation Forest anomaly detection.
- `train_analytics.py`: CLI script to run the ML pipeline and register models in MLflow.
- `reports/`: Markdown research reports integrated into the dashboard.
- `src/salary_data/__init__.py`: Makes the `salary_data` directory a Python package.

---

# Building and Running

## Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

## Setup
1. Install dependencies:
   ```bash
   poetry install
   ```

## Running the Application
1. (Optional) Run the ML training pipeline:
   ```bash
   poetry run python train_analytics.py
   ```
2. Start the Dash server:
   ```bash
   poetry run python src/salary_app.py
   ```
3. Access the dashboard at `http://0.0.0.0:8050`.

## Testing
- `test_ground.ipynb`: Notebook for experimental scraper testing.
- `test_analytics.ipynb`: Notebook for ML prototyping and hyperparameter tuning.
- TODO: Implement automated unit tests (e.g., using `pytest`).

---

# Development Conventions

- **Code Location:** All source code resides in the `src/` directory.
- **Data Logic:** Data fetching and transformation should be kept within `src/salary_data/` to keep the UI logic in `salary_app.py` clean.
- **Styling:** Currently uses a basic external CSS stylesheet (`codepen.io/chriddyp/pen/bWLwgP.css`). Future improvements might involve migrating to `dash-bootstrap-components`.
- **Environment:** The `pyproject.toml` file manages all dependencies and project metadata.
