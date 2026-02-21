# Teacher Salaries Dashboard - TODO List

## Priority 1: Data Parsing & Cleaning
- [ ] **Fix Salary Data Parsing:** Investigate and resolve potential decimal point/comma conversion errors (English vs. Spanish conventions) in the CGECSE Excel files.
- [ ] **Cleanup Provincial Comparison:** Filter out non-province entries (e.g., comments, reference notes, national averages) from the salary DataFrames to ensure the bar chart only shows valid jurisdictions.
- [ ] **Restore CBT Integration:** Resolve the `HTTP Error 403: Forbidden` issue when fetching data from `datos.gob.ar`. Explore using custom `User-Agent` headers or alternative data mirrors.

## Priority 2: UI/UX Enhancements
- [ ] **Migrate to Bootstrap:** Transition from the current `codepen.io` CSS to `dash-bootstrap-components` for a more modern, responsive layout.
- [ ] **Implement KPI Cards:** Use Bootstrap Cards to display Key Performance Indicators at the top of the dashboard.
- [ ] **Redesign Date Range Selector:** Replace the current `dcc.RangeSlider` with a more intuitive and visually appealing component (e.g., `dcc.DatePickerRange` or a refined slider).
- [ ] **Improve Charts Layout:** Optimize chart sizing and responsiveness within the Bootstrap grid.

## Priority 3: Functionality & Analysis
- [ ] **Add Inflation Details:** Include options to view IPC breakdown by category (Alimentos, etc.).
- [ ] **Export Data:** Add a button to export the currently filtered data to a CSV or Excel file.
- [ ] **Multi-Province Comparison:** Update the line chart to allow selecting and comparing multiple provinces simultaneously.
