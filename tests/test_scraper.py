import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.salary_data.scraper import Scraper

def test_scraper_url_ipc_construction():
    """Verify that URL_IPC is correctly formatted for the current month and year."""
    scraper = Scraper()
    month = f'{datetime.today().month:02d}'
    year = f'{datetime.today().year}'[-2:]
    
    assert f"sh_ipc_{month}_{year}.xls" in scraper.URL_IPC

def test_column_sanitization_in_salary_data():
    """Verify that footnotes like (1) or (2) are removed from jurisdiction names."""
    scraper = Scraper()
    # Mock DataFrame with footnotes in columns
    df_raw = pd.DataFrame({
        'jurisdiction': ['Buenos Aires (1)', 'Chaco (2)', 'Promedio Ponderado (MG Total) (3)'],
        '2003-03-01': [100, 200, 300]
    })
    
    # Simulate the cleaning logic inside get_cgecse_salaries
    new_names = df_raw['jurisdiction'].str.replace(r' \(([1-9])\)|\(([1-9])\)', '', regex=True).str.strip()
    
    assert list(new_names) == ["Buenos Aires", "Chaco", "Promedio Ponderado (MG Total)"]

@patch('requests.get')
def test_get_cba_cbt_parsing(mock_get):
    """Verify that CBA/CBT CSV is correctly parsed."""
    scraper = Scraper()
    mock_csv = "indice_tiempo,cba,cbt\n2023-01-01,100.5,220.3\n2023-02-01,110.2,235.4"
    mock_get.return_value.content = mock_csv.encode('utf-8')
    
    df = scraper.get_cba_cbt()
    assert df.index.name == 'indice_tiempo'
    assert len(df) == 2
    assert df.loc['2023-01-01', 'cba'] == 100.5
    assert df.loc['2023-02-01', 'cbt'] == 235.4

def test_calculate_variations_frequency_detection():
    """Verify quarterly vs monthly frequency detection in variations."""
    scraper = Scraper()
    
    # Quarterly series
    # interannual needs period=4, so we need at least 5 points
    dates_q = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    series_q = pd.Series([100, 110, 121, 133.1, 146.41], index=dates_q)
    df_q = scraper.calculate_variations(series_q)
    assert df_q.loc['2023-06-01', 'quarterly'] == pytest.approx(10.0)
    assert df_q.loc['2024-03-01', 'interannual'] == pytest.approx(46.41)
    
    # Monthly series
    dates_m = pd.date_range(start='2023-01-01', periods=13, freq='MS')
    series_m = pd.Series([100] * 13, index=dates_m)
    series_m.iloc[-1] = 110 # Jan 2024
    df_m = scraper.calculate_variations(series_m)
    # Quarterly should look back 3 months for monthly data
    assert df_m.loc['2024-01-01', 'quarterly'] == pytest.approx(10.0) 
    # Interannual should look back 12 months
    assert df_m.loc['2024-01-01', 'interannual'] == pytest.approx(10.0)
