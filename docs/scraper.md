# Scraper Class Documentation

The `Scraper` class (`src/salary_data/scraper.py`) fetches, cleans, and processes economic data from Argentine government sources.

## Data Sources

*   **Salaries:** [CGECSE](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/series-salario-docente) (Excel).
*   **IPC (Inflation):** [INDEC](https://www.indec.gob.ar/) (Excel).
*   **CBA/CBT (Poverty Lines):** [datos.gob.ar](https://www.datos.gob.ar/) (CSV).

## Key Methods

### `get_cgecse_salaries(url: str)`
Fetches teacher salaries. 
*   **Sanitization:** Automatically removes footnotes (e.g., `(1)`) and trailing notes rows from Excel exports.
*   **Transformation:** Pivots the data into a time-series format with standardized jurisdiction names.

### `get_ipc_indec()`
Retrieves the Consumer Price Index.
*   **Categories:** Returns a DataFrame containing indices for all published categories (Food, Housing, Education, etc.).
*   **Formatting:** Standardizes column names by replacing spaces and separators with underscores.

### `get_cba_cbt()`
Retrieves monthly values for the Basic Food Basket (CBA) and Total Basic Basket (CBT).

### `calculate_real_salary(df_nominal, ipc_series, base_date)`
Adjusts nominal values for inflation.
*   **Alignment:** Performs a strict **inner join** on dates, ensuring results only include periods where both salary and inflation data are available.
*   **Logic:** Multiplies the nominal amount by the ratio of the base month index to the current month index.

### `calculate_variations(series)`
Computes growth metrics:
*   `quarterly`: Percentage change vs. previous period.
*   `annual_acc`: Percentage change since January of the same year.
*   `interannual`: Percentage change vs. the same period last year.

## Data Consistency
To ensure compatibility with the modern INDEC IPC series, the application-level logic aligns all data starting from **December 2016**.
