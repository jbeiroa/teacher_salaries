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
        self.URL_TESTIGO_BRUTO = "https://www.argentina.gob.ar/sites/default/files/2022/07/1._salario_bruto_mg10_25.xlsx"
        self.URL_TESTIGO_NETO = "https://www.argentina.gob.ar/sites/default/files/2022/07/2._salario_de_bolsillo_mg10_25.xlsx"
        self.URL_BASICO = "https://www.argentina.gob.ar/sites/default/files/2022/07/3._sueldo_basico_25.xlsx"
        self.URL_REMUNERATIVOS = "https://www.argentina.gob.ar/sites/default/files/2022/07/4._porcentaje_de_componentes_remunerativos_sobre_el_salario_bruto_provincial_del_mg10_25.xlsx"
        self.URL_SUMAS_ADICIONALES = "https://www.argentina.gob.ar/sites/default/files/2022/07/5._sumas_adicionales_25.xlsx"
        
        # IPC URL construction
        # IPC URL construction
        base_ipc_url = 'https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_'
        month = f'{datetime.today().month:02d}'
        year = f'{datetime.today().year}'[-2:]
        self.URL_IPC = base_ipc_url + month + '_' + year + '.xls'
        
        # CBA/CBT URL from datos.gob.ar
        self.URL_CBA_CBT = 'https://infra.datos.gob.ar/catalog/sspm/dataset/150/distribution/150.1/download/valores-canasta-basica-alimentos-canasta-basica-total-mensual-2016.csv'

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

        # drops notes columns
        df.drop(df.columns[-5:], axis=1, inplace=True)
            
        return df.astype('float32') #convert to numeric
    
    def get_ipc_indec(self):
        """Retrieves inflation data from INDEC

        Returns:
            df: Pandas dataframe with inflation data by category
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
        new_col_names = df.columns.str.replace(r'[\s,y]+', self._replace_with_underscore, regex=True)
        col_names = dict(zip(df.columns, new_col_names))
        df.rename(col_names, axis=1, inplace=True)
        
        return df.add_prefix('infl_', axis=1).astype('float32')

    def get_cba_cbt(self):
        """
        Fetches CBA (Indigency Line) and CBT (Poverty Line) data from datos.gob.ar.

        Returns:
            pd.DataFrame: A DataFrame with 'indice_tiempo', 'cba', and 'cbt'.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = req.get(self.URL_CBA_CBT, headers=headers, timeout=10)
        df = pd.read_csv(BytesIO(r.content))
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
            ipc_series = df_ipc['infl_Nivel_general']
        else:
            ipc_series = df_ipc
            
        if base_date is None:
            base_date = ipc_series.index[-1]
        
        base_value = ipc_series.loc[base_date]
        
        # Reindex IPC to match salary dates (usually quarterly)
        ipc_reindexed = ipc_series.reindex(df_nominal.index, method='ffill')
        
        df_real = df_nominal.divide(ipc_reindexed, axis=0) * base_value
        return df_real.dropna()

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