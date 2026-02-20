import pandas as pd
import numpy as np
import requests as req
import re
from datetime import datetime
from io import BytesIO

class Scraper():
    def __init__(self):
        self.URL_TESTIGO_BRUTO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/3._salario_bruto_mg10_5.xlsx'
        self.URL_TESTIGO_NETO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/2._salario_de_bolsillo_mg10_5.xlsx'
        self.URL_BASICO = 'https://www.argentina.gob.ar/sites/default/files/2022/07/1._sueldo_basico_5.xlsx'
        self.URL_REMUNERATIVOS = 'https://www.argentina.gob.ar/sites/default/files/2022/07/4._porcentaje_de_componentes_remunerativos_sobre_el_salario_bruto_provincial_del_mg10_5.xlsx'
        base_ipc_url = 'https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_'
        month = f'{datetime.today().month:02d}'
        year = f'{datetime.today().year}'[-2:]
        self.URL_IPC = base_ipc_url + month + '_' + year + '.xls'

    def replace_with_underscore(self, match):
        return '_' if match.group() in [' ', ', ', ' y '] else ''

    def get_cgecse_salaries(self, url):
        r = req.get(url, timeout=10)
        df = pd.read_excel(BytesIO(r.content), header=6)
        df.drop([df.columns[0]], axis=1, inplace=True)
        df.rename({df.columns[0]: 'jurisdiction'}, axis=1, inplace=True)

        current = pd.to_datetime('2003-03-01')
        dates = [current]
        for col in df.columns:
            current = current + pd.DateOffset(months=3)
            dates.append(current)
        names = dict(zip(df.columns[1:], dates))
        df.rename(names, axis=1, inplace=True)
        df.dropna(inplace=True)
        df = df.T
        df.columns = df.iloc[0]
        df.drop(df.index[0], inplace=True)
        df.index.name = 'date'
        new_col_names = df.columns.str.replace(r' \(([1-9])\)|\(([1-9])\)', '', regex=True)
        col_names = dict(zip(df.columns, new_col_names))
        df.rename(col_names, axis=1, inplace=True)
        return df
    
    def get_ipc_indec(self):
        r = req.get(self.URL_IPC)
        df = pd.read_excel(BytesIO(r.content), 
                        sheet_name='Índices IPC Cobertura Nacional',
                        header=5, 
                        nrows=26)
        df.dropna(inplace=True)
        df = df.T
        df.columns = df.iloc[0]
        df.drop(df.index[0], inplace=True)
        new_col_names = df.columns.str.replace(r'[\s,y]+', self.replace_with_underscore, regex=True)
        col_names = dict(zip(df.columns, new_col_names))
        df.rename(col_names, axis=1, inplace=True)
        return df
