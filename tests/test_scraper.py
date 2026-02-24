import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock
from salary_data.scraper import Scraper
import requests

@pytest.fixture
def scraper():
    return Scraper()

@pytest.fixture
def mock_salary_data():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    # 25 columns as expected
    provinces = [
        "Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba", "Corrientes", 
        "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", 
        "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", 
        "Santa Cruz", "Santa Fe", "Santiago del Estero", "Tierra del Fuego", "Tucumán",
        "Ciudad Autónoma de Buenos Aires", "Promedio Ponderado (MG Total)"
    ]
    data = {p: [100.0] * 5 for p in provinces}
    return pd.DataFrame(data, index=dates)

@pytest.fixture
def mock_ipc_series():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    return pd.Series([100, 110, 121, 133.1, 146.41], index=dates, name='infl_Nivel_general')

def test_calculate_real_salary_alignment(scraper, mock_salary_data, mock_ipc_series):
    # Test that it only returns the intersection of indices
    ipc_short = mock_ipc_series.iloc[:-1] # Drop 2024-03-01
    df_real = scraper.calculate_real_salary(mock_salary_data, ipc_short, base_date='2023-12-01')
    
    assert len(df_real) == 4
    assert df_real.index[-1] == pd.to_datetime('2023-12-01')
    assert pd.to_datetime('2024-03-01') not in df_real.index

def test_calculate_variations_quarterly(scraper):
    dates = pd.to_datetime(['2022-03-01', '2022-06-01', '2022-09-01', '2022-12-01', 
                            '2023-03-01', '2023-06-01'])
    values = [100, 110, 121, 133.1, 146.41, 161.051]
    series = pd.Series(values, index=dates)
    
    df_var = scraper.calculate_variations(series)
    
    # Quarterly (period 1)
    assert df_var.loc['2023-06-01', 'quarterly'] == pytest.approx(10.0)
    # Inter-annual (period 4)
    assert df_var.loc['2023-03-01', 'interannual'] == pytest.approx(46.41)

def test_replace_with_underscore(scraper):
    assert scraper._replace_with_underscore(MagicMock(group=lambda: ' ')) == '_'
    assert scraper._replace_with_underscore(MagicMock(group=lambda: ' y ')) == '_'

@patch('requests.get')
def test_network_error_handling(mock_get, scraper):
    mock_get.side_effect = requests.exceptions.Timeout()
    with pytest.raises(requests.exceptions.Timeout):
        scraper.get_cgecse_salaries("http://dummy.url")

def test_column_sanitization_and_cleaning(scraper):
    # Mock data with footnotes and trailing notes rows
    data = [
        ['dummy', 'Buenos Aires (1)', 100, 110],
        ['dummy', 'Ciudad Autónoma de Buenos Aires', 120, 130],
        ['dummy', 'Promedio Ponderado (MG Total) (2)', 110, 120],
        ['dummy', 'Notes 1', 0, 0],
        ['dummy', 'Notes 2', 0, 0],
        ['dummy', 'Notes 3', 0, 0],
        ['dummy', 'Notes 4', 0, 0],
        ['dummy', 'Notes 5', 0, 0],
    ]
    
    with patch('pandas.read_excel') as mock_read:
        mock_df = pd.DataFrame(data, columns=['Col0', 'Col1', '2003-I', '2003-II'])
        mock_read.return_value = mock_df
        
        with patch('requests.get') as mock_req:
            mock_req.return_value.content = b"fake content"
            df = scraper.get_cgecse_salaries("http://dummy.url")
            
            # Check jurisdictions are correctly cleaned
            # Note: "Promedio Ponderado (MG Total)" contains parentheses, 
            # but footnotes like (1) or (2) should be gone.
            assert list(df.columns) == ["Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Promedio Ponderado (MG Total)"]
            # Verify no footnotes (digit inside parentheses) remain
            assert not any(pd.Series(df.columns).str.contains(r'\([1-9]\)'))
            assert len(df.columns) == 3 
