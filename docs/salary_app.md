# Teacher Salaries Dashboard Application

The `salary_app.py` file contains the main Dash application for visualizing and analyzing teacher salary data in Argentina.

## Architecture Overview

The application is built using a modular Dash architecture:
*   **Bilingual Support:** Uses a `TRANSLATIONS` dictionary and a `lang-store` to manage all UI strings in Spanish and English.
*   **Dynamic Calculations:** Adjusts nominal salaries to "real" terms on-the-fly based on user-selected inflation indices and base dates.
*   **Grid Layout:** Utilizes `dash-bootstrap-components` for a responsive, modern interface.

## Interactive Components

### Multi-page Navigation
*   **Dashboard Tab:** The primary analytical interface for salary trends and comparisons.
*   **Analytics Tab:** A research portal featuring a narrative deep dive into provincial clusters, supported by specialized visualizations.

### Control Sidebar
*   **Province Selector:** Choose any of the 24 Argentine jurisdictions or the weighted average.
*   **Salary Type:** Toggle between Net, Gross, and Basic salaries.
*   **Adjustment Switches:**
    *   **Show Real:** Toggles between inflation-adjusted (Real) and Nominal values.
    *   **Show Ref. Line:** Displays CBA/CBT adult baskets or family poverty lines.
    *   **Show as Index (Base 100):** Normalizes charts to percentage growth relative to the selected **Base Date**.
*   **Inflation Category:** Select specific INDEC indices (General, Food, Housing, etc.) for adjustment.
*   **Base Date Selector:** Defines the reference month ($Base=100$) for real salary and index calculations.

## Visualizations

### 1. Key Performance Indicators (KPIs)
Displays the latest salary in nominal terms alongside:
*   **Context:** Nominal growth vs. Inflation growth (e.g., `Nom: +20% | IPC: +22%`).
*   **Net Result:** Real variation subtext (e.g., `Var. Real: -2.0%`) color-coded by performance.

### 2. Historical Trend Chart
Visualizes purchasing power over time.
*   **Real Mode:** Shows salary and baskets in constant currency.
*   **Index Mode:** Plots the growth trajectory of salaries relative to the poverty line.

### 3. Provincial Comparison
A ranked bar chart showing:
*   **Anomalies:** Jurisdictions with significant 3-month shocks are marked with **⚠️ (Drop)** or **✨ (Gain)**.
*   **Month Selection:** Interactive dropdown to compare any point in the historical series.

### 4. Advanced Analytics Report
Dynamic deep-dive intercalating expert research text with specific cluster line plots to explain jurisdictional economic behaviors.

## Running the Application

```bash
poetry run python src/salary_app.py
```
Access the dashboard at `http://127.0.0.1:8050/`.
