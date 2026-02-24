import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from salary_data.scraper import Scraper

@pytest.fixture
def scraper():
    return Scraper()

@pytest.fixture
def mock_salary_data():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    data = {
        'Chaco': [100, 110, 121, 133.1, 146.41],
        'Buenos Aires': [200, 220, 242, 266.2, 292.82]
    }
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def mock_ipc_data():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    # IPC growing at 10% per quarter
    data = {'Nivel_general': [100, 110, 121, 133.1, 146.41]}
    return pd.DataFrame(data, index=dates)

def test_calculate_real_salary(scraper, mock_salary_data, mock_ipc_data):
    # In this case, salary grows exactly at the same rate as IPC
    # So real salary should be constant
    df_real = scraper.calculate_real_salary(mock_salary_data, mock_ipc_data, base_date='2024-03-01')
    
    # All values should be equal to the last nominal value (146.41 and 292.82)
    assert np.allclose(df_real['Chaco'], 146.41)
    assert np.allclose(df_real['Buenos Aires'], 292.82)

def test_calculate_variations(scraper):
    dates = pd.to_datetime(['2022-03-01', '2022-06-01', '2022-09-01', '2022-12-01', 
                            '2023-03-01', '2023-06-01'])
    values = [100, 110, 121, 133.1, 146.41, 161.051]
    series = pd.Series(values, index=dates)
    
    df_var = scraper.calculate_variations(series)
    
    # Quarterly (1 period)
    assert df_var.loc['2023-06-01', 'quarterly'] == pytest.approx(10.0)
    
    # Inter-annual (4 periods for quarterly data)
    # (146.41 / 100 - 1) * 100 = 46.41
    assert df_var.loc['2023-03-01', 'interannual'] == pytest.approx(46.41)
    
    # Annual accumulated (since Jan of the same year)
    # For 2023-06-01, it's (161.051 / 146.41 - 1) * 100 = 10.0
    assert df_var.loc['2023-06-01', 'annual_acc'] == pytest.approx(10.0)
