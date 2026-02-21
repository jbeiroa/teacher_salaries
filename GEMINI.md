# Project Overview

The **Teacher Salaries Dashboard** is a Python-based web application designed to visualize and analyze teacher salary data in Argentina. The project fetches data directly from the [Coordinación General de Estudio de Costos del Sistema Educativo (CGECSE)](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/series-salario-docente) and [INDEC](https://www.indec.gob.ar/).

## Main Technologies
- **Framework:** [Dash](https://dash.plotly.com/) (React-based Python framework for analytical web apps)
- **Data Manipulation:** [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/)
- **Visualization:** [Plotly Express](https://plotly.com/python/plotly-express/)
- **Dependency Management:** [Poetry](https://python-poetry.org/)
- **Scraping/Data Fetching:** [Requests](https://requests.readthedocs.io/), [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/), [Openpyxl](https://openpyxl.readthedocs.io/)

## Architecture
- `src/salary_app.py`: The main entry point of the Dash application. It defines the layout, callbacks, and server configuration.
- `src/salary_data/scraper.py`: Contains the `Scraper` class responsible for downloading Excel files from government portals, cleaning the data, and formatting it into Pandas DataFrames.
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
1. Start the Dash server:
   ```bash
   python src/salary_app.py
   ```
   Or using Poetry:
   ```bash
   poetry run python src/salary_app.py
   ```
2. Access the dashboard at `http://0.0.0.0:8050` (or `localhost:8050`).

## Testing
- There is a `test_ground.ipynb` notebook for experimental data analysis and testing scraper logic.
- TODO: Implement automated unit tests (e.g., using `pytest`).

---

# Development Conventions

- **Code Location:** All source code resides in the `src/` directory.
- **Data Logic:** Data fetching and transformation should be kept within `src/salary_data/` to keep the UI logic in `salary_app.py` clean.
- **Styling:** Currently uses a basic external CSS stylesheet (`codepen.io/chriddyp/pen/bWLwgP.css`). Future improvements might involve migrating to `dash-bootstrap-components`.
- **Environment:** The `pyproject.toml` file manages all dependencies and project metadata.
