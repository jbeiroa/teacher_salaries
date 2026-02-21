# Scraper Class Documentation

The `Scraper` class, located in `src/salary_data/scraper.py`, is responsible for fetching, cleaning, and processing teacher salary, inflation (IPC), and poverty line (CBA/CBT) data from various Argentine government sources.

## Data Sources

*   **Salaries:** [CGECSE](https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/series-salario-docente) (Excel files).
*   **IPC (Inflation):** [INDEC](https://www.indec.gob.ar/) (Excel file).
*   **CBA/CBT (Poverty/Indigency Lines):** [datos.gob.ar](https://www.datos.gob.ar/) (CSV file).

## Class: `Scraper`

### `__init__(self)`
Initializes the scraper with the URLs for different data sources.
*   Note: The `URL_IPC` is dynamically constructed based on the current date to fetch the latest available INDEC report.

### `get_cgecse_salaries(self, url: str) -> pd.DataFrame`
Scrapes and cleans teacher salary data from a CGECSE Excel file.
*   **Args:** `url` (str): The URL of the CGECSE Excel file.
*   **Returns:** `pd.DataFrame`: A DataFrame where index is `date` (datetime) and columns are Argentine provinces.

### `get_ipc_indec(self) -> pd.DataFrame`
Scrapes and processes national 'Nivel general' IPC data from INDEC Excel file.
*   **Returns:** `pd.DataFrame`: A DataFrame with dates as index, 'Nivel_general' IPC values, and a 'Region' column (set to 'Nacional').
*   **Implementation Detail:** This function uses a robust parsing logic that dynamically locates 'Total Nacional' and 'Nivel general' rows within the INDEC report. It handles both direct `datetime` objects and string-formatted dates (`dd/mm/yyyy`).

### `get_cba_cbt(self) -> pd.DataFrame`
Fetches CBA (Indigency Line) and CBT (Poverty Line) data from `datos.gob.ar`.
*   **Returns:** `pd.DataFrame`: A DataFrame with `indice_tiempo` (date index), `cba`, and `cbt`.
*   **Note:** This feature is currently disabled in the main application due to `HTTP 403 Forbidden` errors from the data provider.

### `calculate_real_salary(self, df_nominal: pd.DataFrame, df_ipc: pd.Series, base_date: datetime = None) -> pd.DataFrame`
Adjusts nominal salaries for inflation to represent "real" purchasing power.
*   **Args:**
    *   `df_nominal` (pd.DataFrame): Nominal salary DataFrame.
    *   `df_ipc` (pd.Series/pd.DataFrame): IPC index Series or DataFrame with 'Nivel\_general'.
    *   `base_date` (str/datetime, optional): The date used as a base (100). If `None`, defaults to the most recent date available in the IPC data.
*   **Returns:** `pd.DataFrame`: Real salary DataFrame.

### `calculate_variations(self, series: pd.Series) -> pd.DataFrame`
Computes key financial growth metrics for a given time series.
*   **Args:** `series` (pd.Series): A time series of values.
*   **Returns:** `pd.DataFrame`: A DataFrame with:
    *   `quarterly`: Percentage change from the previous period (1 period back).
    *   `annual_acc`: Percentage change accumulated since January of the current year.
    *   `interannual`: Percentage change compared to the same period in the previous year (4 periods back for quarterly data).
