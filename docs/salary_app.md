# Teacher Salaries Dashboard Application

The `salary_app.py` file contains the main Dash application for visualizing and analyzing teacher salary data in Argentina.

## Architecture Overview

The application is built using a modular Dash architecture:
*   **Bilingual Support:** Uses a `TRANSLATIONS` dictionary and a `lang-store` to manage all UI strings in Spanish and English.
*   **Dynamic Calculations:** Adjusts nominal salaries to "real" terms on-the-fly based on user-selected inflation indices and base dates.
*   **Grid Layout:** Utilizes `dash-bootstrap-components` for a responsive, modern interface.

## Interactive Components

### Control Sidebar
*   **Province Selector:** Choose any of the 24 Argentine jurisdictions or the weighted average.
*   **Salary Type:** Toggle between Net, Gross, and Basic salaries.
*   **Adjustment Switches:** Show/hide Nominal lines, Real (Adjusted) lines, or Reference lines (CBA/CBT).
*   **Reference Line Selector:** Choose between individual baskets (CBA/CBT Adult) or family lines (Poverty/Indigency).
*   **Inflation Category:** Select specific INDEC indices (General, Food, Housing, etc.) for adjustment.
*   **Base Date Selector:** Pick the reference month (Base 100) for real salary calculations.
*   **Historical Date Range:** A `DatePickerRange` to filter the trend chart.

### Header Controls
*   **Language Toggle:** Switch between ES and EN.
*   **Help Button ("?"):** Opens a slide-out menu with links to data sources and category explanations.

## Visualizations

### 1. Key Performance Indicators (KPIs)
Displays the latest salary in nominal terms alongside the **Real Variation** (inflation-adjusted) for Quarterly, Annual, and Inter-annual periods.

### 2. Historical Trend Chart
Visualizes purchasing power over time. It aligns all data sources to start from **December 2016** to maintain consistency with modern INDEC IPC series.

### 3. Provincial Comparison
A ranked horizontal bar chart comparing the selected salary type across all provinces for a specific **Comparison Month**, which can be selected directly within the chart header.

## Running the Application

```bash
poetry run python src/salary_app.py
```
Access the dashboard at `http://127.0.0.1:8050/`.
