# Teacher Salaries Dashboard - Argentina

An interactive web application built with **Dash** to visualize and analyze teacher salary data across different provinces in Argentina, with context provided by inflation (IPC) and poverty line (CBT) data.

## Features

- **Interactive Province Selection:** Analyze salary trends for any specific province.
- **Salary Type Comparison:** Switch between Net, Gross, and Basic salary views.
- **Historical Trend Analysis:** View nominal vs. inflation-adjusted (real) salaries over time.
- **National Comparison:** Compare latest salary data across all provinces.
- **Key Metrics:** Real-time display of latest salaries and annual variations.

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
Start the Dash server:
```bash
poetry run python src/salary_app.py
```
Access the dashboard at `http://127.0.0.1:8050`.

### Running Tests
Execute the test suite with:
```bash
PYTHONPATH=src poetry run pytest
```

## Project Structure

- `src/salary_app.py`: Main entry point and dashboard UI logic.
- `src/salary_data/scraper.py`: Data fetching and cleaning module.
- `docs/`: Detailed documentation for the scraper and application.
- `tests/`: Automated unit tests using `pytest`.

## Data Sources
- **Salaries:** CGECSE (Ministerio de Educación).
- **Inflation:** INDEC (Instituto Nacional de Estadística y Censos).
- **Poverty Line:** datos.gob.ar (Optional/Temporarily Disabled).

## License
MIT
