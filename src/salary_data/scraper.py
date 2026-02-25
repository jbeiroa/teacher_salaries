"""
Module for scraping and processing Argentine teacher salary and economic data.

This module provides the Scraper class, which handles data retrieval from various 
government sources, including teacher salaries, inflation (IPC), and poverty lines 
(CBA/CBT).
"""

import pandas as pd
import numpy as np
import requests as req
import re
from datetime import datetime
from io import BytesIO


class Scraper():
    """A class to scrape and process Argentine teacher salary and economic data.

    This class handles downloading Excel and CSV files from government portals,
    cleaning the data, and formatting it into Pandas DataFrames for analysis.

    Attributes:
        URL_TESTIGO_BRUTO (str): URL for gross witness salary data.
        URL_TESTIGO_NETO (str): URL for net witness salary data.
        URL_BASICO (str): URL for basic salary data.
        URL_REMUNERATIVOS (str): URL for remunerative components data.
        URL_SUMAS_ADICIONALES (str): URL for additional sums data.
        URL_IPC (str): Dynamically constructed URL for INDEC inflation data.
        URL_CBA_CBT (str): URL for CBA and CBT data from datos.gob.ar.
    """

    def __init__(self):
        """Initializes the Scraper with default URLs and constructs the IPC URL."""
        self.URL_TESTIGO_BRUTO = "https://www.argentina.gob.ar/sites/default/files/2022/07/1._salario_bruto_mg10_25.xlsx"
        self.URL_TESTIGO_NETO = "https://www.argentina.gob.ar/sites/default/files/2022/07/2._salario_de_bolsillo_mg10_25.xlsx"
        self.URL_BASICO = "https://www.argentina.gob.ar/sites/default/files/2022/07/3._sueldo_basico_25.xlsx"
        self.URL_REMUNERATIVOS = "https://www.argentina.gob.ar/sites/default/files/2022/07/4._porcentaje_de_componentes_remunerativos_sobre_el_salario_bruto_provincial_del_mg10_25.xlsx"
        self.URL_SUMAS_ADICIONALES = "https://www.argentina.gob.ar/sites/default/files/2022/07/5._sumas_adicionales_25.xlsx"
        
        # IPC URL construction
        base_ipc_url = 'https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_'
        month = f'{datetime.today().month:02d}'
        year = f'{datetime.today().year}'[-2:]
        self.URL_IPC = base_ipc_url + month + '_' + year + '.xls'
        
        # CBA/CBT URL from datos.gob.ar
        self.URL_CBA_CBT = 'https://infra.datos.gob.ar/catalog/sspm/dataset/150/distribution/150.1/download/valores-canasta-basica-alimentos-canasta-basica-total-mensual-2016.csv'

    def _replace_with_underscore(self, match):
        """Helper to sanitize column names.

        Args:
            match (re.Match): A regex match object.

        Returns:
            str: An underscore if the match is a separator, otherwise an empty string.
        """
        return '_' if match.group() in [' ', ', ', ' y '] else ''

    def get_cgecse_salaries(self, url):
        """Scrapes and cleans teacher salary data from CGECSE Excel files.

        Processes the Excel file from the given URL, handles quarterly column 
        transformation to datetime, cleans province names, and removes footnotes.

        Args:
            url (str): The URL of the CGECSE Excel file.

        Returns:
            pd.DataFrame: A DataFrame with dates as index and provinces as columns.
                The values are cast to 'float32'.
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

        # drops notes columns
        df.drop(df.columns[-5:], axis=1, inplace=True)
            
        return df.astype('float32') #convert to numeric
    
    def get_ipc_indec(self):
        """Retrieves inflation data from INDEC.

        Fetches the IPC (Consumer Price Index) from the INDEC portal, cleans 
        column names, and prefixes them with 'infl_'.

        Returns:
            pd.DataFrame: A DataFrame with inflation indices by category.
                The index is the date and columns are prefixed with 'infl_'.
        """        
        r = req.get(self.URL_IPC, timeout=10)
        df = pd.read_excel(BytesIO(r.content), 
                        sheet_name='Índices IPC Cobertura Nacional',
                        header=5, 
                        nrows=26)
        df.dropna(inplace=True)
        df = df.T
        df.columns = df.iloc[0]
        df.drop(df.index[0], inplace=True)
        df.index = pd.to_datetime(df.index)
        new_col_names = df.columns.str.replace(r'[\s,y]+', self._replace_with_underscore, regex=True)
        col_names = dict(zip(df.columns, new_col_names))
        df.rename(col_names, axis=1, inplace=True)
        
        return df.add_prefix('infl_', axis=1).astype('float32')

    def get_cba_cbt(self):
        """Fetches CBA (Indigency Line) and CBT (Poverty Line) data from datos.gob.ar.

        Retrieves monthly values for the Basic Food Basket (CBA) and Total Basic 
        Basket (CBT) for the GBA region.

        Returns:
            pd.DataFrame: A DataFrame with 'indice_tiempo' as index, 'cba', and 'cbt'.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = req.get(self.URL_CBA_CBT, headers=headers, timeout=10)
        df = pd.read_csv(BytesIO(r.content))
        df['indice_tiempo'] = pd.to_datetime(df['indice_tiempo'])
        df.set_index('indice_tiempo', inplace=True)
        return df

    def calculate_real_salary(self, df_nominal, df_ipc, base_date=None):
        """Calculates inflation-adjusted (real) salaries.

        Adjusts nominal salary values using a price index (IPC) to a specific 
        base date.

        Args:
            df_nominal (pd.DataFrame): Nominal salary DataFrame.
            df_ipc (pd.Series or pd.DataFrame): IPC index Series or DataFrame 
                containing 'infl_Nivel_general'.
            base_date (str or datetime, optional): The date to use as base (value=100). 
                If None, uses the last available date in the IPC series.

        Returns:
            pd.DataFrame: Real salary DataFrame.
        """
        if isinstance(df_ipc, pd.DataFrame):
            ipc_series = df_ipc['infl_Nivel_general']
        else:
            ipc_series = df_ipc
            
        if base_date is None:
            base_date = ipc_series.index[-1]
        
        base_value = ipc_series.loc[base_date]
        
        # Align IPC to salary dates
        common_index = df_nominal.index.intersection(ipc_series.index)
        df_nom_aligned = df_nominal.loc[common_index]
        ipc_aligned = ipc_series.loc[common_index]
        
        df_real = df_nom_aligned.divide(ipc_aligned, axis=0) * base_value
        return df_real

    def calculate_variations(self, series):
        """Calculates quarterly, annual (accumulated), and inter-annual variations.

        Computes percentage changes for different time horizons. 
        Detects series frequency (monthly vs quarterly) to adjust periods.

        Args:
            series (pd.Series): A time series of values.

        Returns:
            pd.DataFrame: A DataFrame with 'quarterly', 'annual_acc', and 
                'interannual' variation columns.
        """
        df_var = pd.DataFrame(index=series.index)
        
        # Detect frequency
        # We check the gap between the last two indices
        if len(series) < 2:
            return pd.DataFrame(columns=['quarterly', 'annual_acc', 'interannual'], index=series.index)
            
        months_gap = (series.index[-1].year - series.index[-2].year) * 12 + (series.index[-1].month - series.index[-2].month)
        
        is_quarterly = months_gap >= 3
        q_periods = 1 if is_quarterly else 3
        ia_periods = 4 if is_quarterly else 12
        
        # 1. Quarterly Variation (Last 3 months)
        df_var['quarterly'] = series.pct_change(periods=q_periods) * 100
        
        # 2. Inter-annual (Same month/quarter previous year)
        df_var['interannual'] = series.pct_change(periods=ia_periods) * 100
        
        # 3. Annual accumulated (Since Dec of previous year)
        # We need the value of the previous Dec for each year
        annual_acc = []
        for date in series.index:
            try:
                # Value at latest Dec before this date
                prev_dec_date = datetime(date.year - 1, 12, 1)
                # Find the value in the series closest to or at that Dec
                # If it's quarterly, it might be 12-01
                if prev_dec_date in series.index:
                    base_val = series.loc[prev_dec_date]
                else:
                    # Fallback: find the last available value from previous years
                    prev_year_data = series[series.index.year < date.year]
                    if not prev_year_data.empty:
                        base_val = prev_year_data.iloc[-1]
                    else:
                        base_val = series.iloc[0] # Fallback to first ever
                
                acc = (series.loc[date] / base_val - 1) * 100
                annual_acc.append(acc)
            except:
                annual_acc.append(np.nan)
                
        df_var['annual_acc'] = annual_acc
        
        return df_var