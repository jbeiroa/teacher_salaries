# Teacher Salaries Dashboard - Argentina

An interactive web application built with **Dash** to visualize and analyze teacher salary data (category MG10) across Argentina, featuring dynamic inflation adjustment and provincial benchmarking.

## Key Features

- **MG10 Benchmark:** Analyzes data for the "Maestro de Grado" position with 10 years of seniority.
- **Advanced Inflation Adjustment:** Select specific inflation categories (Food, Housing, etc.) and a custom **Base Date** for real salary calculations.
- **Reference Lines:** Overlay Poverty and Indigency lines (CBA/CBT) for both individual adults and standard families.
- **Bilingual Support:** Full interface available in **Spanish** (default) and **English**.
- **Interactive Visualizations:** Historical trends (Nominal vs. Real) and ranked provincial comparisons for any chosen month.

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
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
poetry run pytest
```

## Project Structure

- `src/salary_app.py`: Main entry point and dashboard UI logic.
- `src/salary_data/scraper.py`: Data fetching and cleaning module.
- `docs/`: Detailed documentation for the scraper and application.
- `tests/`: Automated unit tests using `pytest`.

## Data Sources
- **Salaries:** CGECSE (Ministerio de Educación).
- **Inflation:** INDEC (Instituto Nacional de Estadística y Censos).
- **Poverty Lines:** datos.gob.ar.

## License
MIT
