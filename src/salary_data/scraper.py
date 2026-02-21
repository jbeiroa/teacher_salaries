import pandas as pd
import numpy as np
import requests as req
import re
from datetime import datetime
from io import BytesIO

class Scraper():
    """
    A class to scrape and process teacher salary, inflation (IPC), and 
    poverty line (CBA/CBT) data from Argentine government sources.
    """
    def __init__(self):
        self.URL_TESTIGO_BRUTO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/3._salario_bruto_mg10_5.xlsx'
        self.URL_TESTIGO_NETO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/2._salario_de_bolsillo_mg10_5.xlsx'
        self.URL_BASICO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/1._sueldo_basico_5.xlsx'
        self.URL_REMUNERATIVOS = 'https://www.argentina.gob.ar/sites/default/files/2022/07/4._porcentaje_de_componentes_remunerativos_sobre_el_salario_bruto_provincial_del_mg10_5.xlsx'
        
        # IPC URL construction
        # IPC URL construction
        base_ipc_url = 'https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_'
        month = f'{datetime.today().month:02d}'
        year = f'{datetime.today().year}'[-2:]
        self.URL_IPC = base_ipc_url + month + '_' + year + '.xls'
        
        # CBA/CBT URL from datos.gob.ar
        self.URL_CBA_CBT = 'https://infra.datos.gob.ar/catalog/sspm/dataset/433/resource/a0122f39-122a-450a-827d-40850222627e/download/valores-canasta-basica-alimentos-canasta-basica-total.csv'

    def _replace_with_underscore(self, match):
        """Helper to sanitize column names."""
        return '_' if match.group() in [' ', ', ', ' y '] else ''

    def get_cgecse_salaries(self, url):
        """
        Scrapes and cleans teacher salary data from CGECSE Excel files.

        Args:
            url (str): The URL of the CGECSE Excel file.

        Returns:
            pd.DataFrame: A DataFrame with dates as index and provinces as columns.
        """
        r = req.get(url, timeout=10)
        df = pd.read_excel(BytesIO(r.content), header=6)
        df.drop([df.columns[0]], axis=1, inplace=True)
        df.rename({df.columns[0]: 'jurisdiction'}, axis=1, inplace=True)

        current = pd.to_datetime('2003-03-01')
        dates = [current]
        # The Excel has columns for quarters starting from 2003-03
        for col in df.columns[1:]:
            current = current + pd.DateOffset(months=3)
            dates.append(current)
            
        names = dict(zip(df.columns[1:], dates))
        df.rename(names, axis=1, inplace=True)
        df.dropna(subset=['jurisdiction'], inplace=True)
        
        df = df.T
        df.columns = df.iloc[0]
        df.drop(df.index[0], inplace=True)
        df.index.name = 'date'
        df.index = pd.to_datetime(df.index)
        
        # Clean province names (remove footnotes like (1))
        new_col_names = df.columns.str.replace(r' \(([1-9])\)|\(([1-9])\)', '', regex=True).str.strip()
        col_names = dict(zip(df.columns, new_col_names))
        df.rename(col_names, axis=1, inplace=True)
        
        # Convert values to numeric
        for col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('$', '').str.replace('.', '').str.replace(',', '.').str.strip(), errors='coerce')
            
        return df
    
    def get_ipc_indec(self):
        """
        Scrapes and processes national 'Nivel general' IPC data from INDEC Excel file.
        Dynamically locates 'Total Nacional' and 'Nivel general' based on precise structure.

        Returns:
            pd.DataFrame: A DataFrame with dates as index and 'Nivel_general' IPC values.
                          Includes a 'Region' column set to 'Nacional' for compatibility.
        """
        base_ipc_url = 'https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_'
        month = f'{datetime.today().month:02d}'
        year = f'{datetime.today().year}'[-2:]
        self.URL_IPC = base_ipc_url + month + '_' + year + '.xls' # Dynamic URL
        
        r = req.get(self.URL_IPC, timeout=10)
        # Read the Excel file without a header initially to locate specific rows/columns
        df_raw = pd.read_excel(BytesIO(r.content), sheet_name='Índices IPC Cobertura Nacional', header=None)

        # Find the row containing "Total Nacional" in the first column (case-insensitive)
        total_nacional_row_idx = df_raw[df_raw.iloc[:, 0].astype(str).str.contains('total nacional', case=False, na=False)].index

        if total_nacional_row_idx.empty:
            raise ValueError("Could not find 'Total Nacional' in the IPC Excel file.")
        
        # Based on user feedback: "Nivel general" is in Row 10 (Excel), which is index 9 (Python)
        actual_nivel_general_row = 9
        
        # Verify that row 9 actually contains "nivel general" (case-insensitive)
        if not str(df_raw.iloc[actual_nivel_general_row, 0]).lower().strip() == 'nivel general':
            raise ValueError(f"Expected 'nivel general' in cell A{actual_nivel_general_row + 1}, but found '{df_raw.iloc[actual_nivel_general_row, 0]}'.")

        # Extract values from this row
        ipc_values_raw = df_raw.loc[actual_nivel_general_row]

        # Based on user feedback: Date headers are in Row 6 (Excel), which is index 5 (Python)
        date_header_row_idx = 5
        # Based on user feedback: Dates start from Column B (Excel), which is index 1 (Python)
        date_cols_start_idx = 1
        
        # Extract dates from the identified header row and starting column
        dates = []
        for col_idx in range(date_cols_start_idx, len(df_raw.iloc[date_header_row_idx])):
            cell_value = df_raw.iloc[date_header_row_idx, col_idx]
            
            parsed_date = None
            if isinstance(cell_value, datetime):
                parsed_date = cell_value
            else:
                try:
                    # Attempt to parse as dd/mm/yyyy if it's a string
                    parsed_date = datetime.strptime(str(cell_value).strip(), '%d/%m/%Y')
                except ValueError:
                    pass # Not a date in dd/mm/yyyy format
            
            if parsed_date:
                dates.append(parsed_date)
            else:
                # Stop if we encounter non-date cells after some dates have been found
                if dates:
                    break
                continue # If no dates yet, continue searching
        
        if not dates:
             raise ValueError("Could not find any date headers in 'dd/mm/yyyy' format from the specified row and column, or pandas did not parse them as datetime objects.")

        # Extract IPC values corresponding to these dates, starting from the same column as dates
        ipc_series = pd.Series(dtype=float)
        for i, dt in enumerate(dates):
            col_idx = date_cols_start_idx + i
            value = ipc_values_raw.iloc[col_idx]
            numeric_value = pd.to_numeric(str(value).replace(',', '.'), errors='coerce')
            if pd.notna(numeric_value):
                ipc_series.loc[dt] = numeric_value
        
        ipc_series.name = 'Nivel_general'
        ipc_series.index.name = 'date'
        
        # Ensure index is sorted and unique
        ipc_series = ipc_series.sort_index()
        ipc_series = ipc_series[~ipc_series.index.duplicated(keep='first')]

        # Create a DataFrame for compatibility with salary_app.py
        df_ipc_national = pd.DataFrame(ipc_series)
        df_ipc_national['Region'] = 'Nacional' # Assign 'Nacional' to all rows for filtering compatibility
        
        return df_ipc_national
    def get_cba_cbt(self):
        """
        Fetches CBA (Indigency Line) and CBT (Poverty Line) data from datos.gob.ar.

        Returns:
            pd.DataFrame: A DataFrame with 'indice_tiempo', 'cba', and 'cbt'.
        """
        df = pd.read_csv(self.URL_CBA_CBT)
        df['indice_tiempo'] = pd.to_datetime(df['indice_tiempo'])
        df.set_index('indice_tiempo', inplace=True)
        return df

    def calculate_real_salary(self, df_nominal, df_ipc, base_date=None):
        """
        Calculates inflation-adjusted (real) salaries.

        Args:
            df_nominal (pd.DataFrame): Nominal salary DataFrame.
            df_ipc (pd.Series/pd.DataFrame): IPC index Series or DataFrame with 'Nivel_general'.
            base_date (str/datetime): The date to use as base (100). If None, uses the last available date.

        Returns:
            pd.DataFrame: Real salary DataFrame.
        """
        if isinstance(df_ipc, pd.DataFrame):
            ipc_series = df_ipc['Nivel_general']
        else:
            ipc_series = df_ipc
            
        if base_date is None:
            base_date = ipc_series.index[-1]
        
        base_value = ipc_series.loc[base_date]
        
        # Reindex IPC to match salary dates (usually quarterly)
        ipc_reindexed = ipc_series.reindex(df_nominal.index, method='ffill')
        
        df_real = df_nominal.divide(ipc_reindexed, axis=0) * base_value
        return df_real

    def calculate_variations(self, series):
        """
        Calculates quarterly, annual (accumulated), and inter-annual variations.

        Args:
            series (pd.Series): A time series of values.

        Returns:
            pd.DataFrame: A DataFrame with 'quarterly', 'annual_acc', and 'interannual' variations.
        """
        df_var = pd.DataFrame(index=series.index)
        df_var['quarterly'] = series.pct_change(periods=1) * 100
        
        # Annual accumulated (since Jan of the same year)
        df_var['annual_acc'] = series.groupby(series.index.year).apply(lambda x: (x / x.iloc[0] - 1) * 100).reset_index(level=0, drop=True)
        
        # Inter-annual (same month/quarter previous year)
        # Assuming quarterly data, 4 periods back
        df_var['interannual'] = series.pct_change(periods=4) * 100
        
        return df_var
