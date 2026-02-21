# Teacher Salaries Dashboard Application

The `salary_app.py` file contains the main Dash application for visualizing and analyzing teacher salary data in Argentina. It leverages the `Scraper` class (from `src/salary_data/scraper.py`) to fetch and process data from various government sources.

## Architecture Overview

The application follows a standard Dash architecture:
*   **Data Fetching & Preparation:** Uses the `Scraper` to get raw salary, IPC, and CBA/CBT data. It performs calculations like real salary adjustments and percentage variations.
*   **Layout:** Defines the visual structure of the dashboard, including interactive components (dropdowns, radio buttons, sliders) and placeholders for visualizations (KPIs, charts).
*   **Callbacks:** Implements the logic that connects user interactions with data updates and chart rendering.

## Data Sources Utilized

The application integrates data from:
*   **CGECSE:** Teacher salaries (Net, Gross, Basic, Remunerative Share).
*   **INDEC:** Consumer Price Index (IPC) for inflation adjustment.
*   **datos.gob.ar (Optional):** Canasta Básica Alimentaria (CBA) and Canasta Básica Total (CBT) for poverty lines. *Note: Currently disabled due to provider access issues.*

## Interactive Components

The dashboard features the following interactive controls:

### 1. Province Dropdown (`province-dropdown`)
*   **Type:** `dcc.Dropdown`
*   **Purpose:** Allows the user to select a single province for detailed analysis.

### 2. Salary Type Radio Buttons (`salary-type-radio`)
*   **Type:** `dcc.RadioItems`
*   **Purpose:** Enables switching between different types of salary data (Net, Gross, Basic).

### 3. Date Range Slider (`date-range-slider`)
*   **Type:** `dcc.RangeSlider`
*   **Purpose:** Filters the displayed data to a specific time period.

## Visualizations

The dashboard presents information through Key Performance Indicators (KPIs) and two main charts:

### 1. Key Performance Indicators (KPIs) (`kpi-output`)
*   **Purpose:** Displays critical summary metrics at the top of the dashboard.
*   **Content:** Shows the latest selected salary and national IPC values, including inter-annual percentage variations.

### 2. Historical Trend Chart (`historical-trend-chart`)
*   **Type:** `dcc.Graph` (Line Chart)
*   **Purpose:** Visualizes the evolution of the selected salary over time for the chosen province.
*   **Content:** Shows both the nominal and inflation-adjusted ("real") salary.

### 3. Provincial Comparison Chart (`provincial-comparison-chart`)
*   **Type:** `dcc.Graph` (Bar Chart)
*   **Purpose:** Compares the selected salary type across all provinces for the latest date in the selected range.

## Running the Application

To run the application, navigate to the project root directory and execute:
```bash
poetry run python src/salary_app.py
```
Then, access the dashboard in your web browser at `http://127.0.0.1:8050/`.
