import numpy as np
import pytest
import pandas as pd
from datetime import datetime
from dash import Dash, html
from dash._callback_context import context_value
from dash._utils import AttributeDict
from unittest.mock import patch, MagicMock

# Import the app and callback function directly for testing
# from salary_app import app, update_dashboard # THIS WILL BE MOVED


# --- Fixtures for Mock Data ---
@pytest.fixture
def mock_df_net_salary():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    data = {
        'Chaco': [100, 110, 121, 133, 146],
        'Buenos Aires': [200, 220, 242, 266, 292],
        'Cordoba': [150, 165, 181, 199, 219]
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'date'
    return df

@pytest.fixture
def mock_df_net_salary_real():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    data = {
        'Chaco': [100, 100, 100, 100, 100],
        'Buenos Aires': [200, 200, 200, 200, 200],
        'Cordoba': [150, 150, 150, 150, 150]
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'date'
    return df

@pytest.fixture
def mock_ipc_national():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    data = pd.Series([100, 110, 121, 133.1, 146.41], index=dates, name='Nivel_general')
    data.index.name = 'date'
    return data

@pytest.fixture
def mock_df_cba_cbt():
    dates = pd.to_datetime(['2023-03-01', '2023-04-01', '2023-05-01', '2023-06-01', 
                            '2023-07-01', '2023-08-01', '2023-09-01', '2023-10-01', 
                            '2023-11-01', '2023-12-01', '2024-01-01', '2024-02-01', '2024-03-01'])
    data = {'cba': np.random.rand(len(dates)) * 100000, 
            'cbt': np.random.rand(len(dates)) * 200000 + 100000}
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'indice_tiempo'
    return df

@pytest.fixture(autouse=True)
def mock_scraper_data(
    mock_df_net_salary, 
    mock_df_net_salary_real, 
    mock_ipc_national, 
    mock_df_cba_cbt
):
    with patch('salary_data.scraper.Scraper') as MockScraper:
        mock_instance = MockScraper.return_value
        
        mock_instance.get_cgecse_salaries.return_value = mock_df_net_salary
        
        mock_ipc_df = pd.DataFrame({'Nivel_general': mock_ipc_national.values}, index=mock_ipc_national.index)
        mock_instance.get_ipc_indec.return_value = mock_ipc_df
        
        mock_instance.get_cba_cbt.return_value = mock_df_cba_cbt
        
        mock_instance.calculate_real_salary.return_value = mock_df_net_salary_real

        mock_variations_output = pd.DataFrame({
            'quarterly': [10.0, 10.0, 10.0, 10.0, 10.0],
            'annual_acc': [0.0, 0.0, 0.0, 0.0, 10.0],
            'interannual': [0.0, 0.0, 0.0, 0.0, 46.0]
        }, index=mock_df_net_salary.index)
        mock_instance.calculate_variations.return_value = mock_variations_output

        # Patch the global scraper instance in salary_app.py after it's loaded
        with patch('salary_app.scraper', new=mock_instance):
            yield

# Helper to simulate Dash callback context
def setup_callback_context(input_id, input_value):
    context_value.set(
        AttributeDict(
            **{
                "triggered_inputs": [
                    {"prop_id": f"{input_id}.value", "value": input_value}
                ]
            }
        )
    )

def test_dashboard_initial_load(
    mock_df_net_salary, 
    mock_df_net_salary_real, 
    mock_ipc_national, 
    mock_df_cba_cbt
):
    """
    Test the dashboard's initial load with default values.
    """
    from salary_app import app, update_dashboard # Move import here
    setup_callback_context('province-dropdown', 'Chaco') # Simulate initial trigger

    # Default inputs from app.layout
    selected_province = 'Chaco'
    selected_salary_type = 'net'
    date_range_indices = [0, len(mock_df_net_salary.index) - 1]

    kpis, historical_fig, provincial_fig = update_dashboard(
        selected_province, selected_salary_type, date_range_indices
    )

    # --- Test KPIs ---
    assert isinstance(kpis, html.Div)
    kpi_texts = [child.children for child in kpis.children]
    
    latest_salary = mock_df_net_salary['Chaco'].iloc[-1]
    latest_ipc = mock_ipc_national.iloc[-1]
    # latest_cbt = mock_df_cba_cbt['cbt'].iloc[-1] if not mock_df_cba_cbt.empty else 0
    assert f"Latest Net for Chaco: ${latest_salary:,.2f}" in kpi_texts
    assert f"Latest National IPC: {latest_ipc:,.2f}" in kpi_texts
    # assert f"Latest CBT: ${latest_cbt:,.2f}" in kpi_texts
    assert "Inter-annual Salary Variation: 46.00%" in kpi_texts
    assert "Inter-annual IPC Variation: 46.00%" in kpi_texts # Based on mock variations
    # assert "Inter-annual CBT Variation: 46.00%" in kpi_texts # Based on mock variations

    # --- Test Historical Trend Chart ---
    assert historical_fig['data'][0]['name'] == f'{selected_salary_type.capitalize()} (Nominal)'
    assert historical_fig['data'][1]['name'] == f'{selected_salary_type.capitalize()} (Real)'
    # assert historical_fig['data'][2]['name'] == 'Canasta Básica Total (CBT)' # Temporarily disabled
    assert historical_fig['layout']['title']['text'] == f'{selected_province} {selected_salary_type.capitalize()} Trend (Nominal vs. Real)'
    assert len(historical_fig['data'][0]['x']) == len(mock_df_net_salary.index) # All dates in range

    # --- Test Provincial Comparison Chart ---
    assert provincial_fig['layout']['title']['text'].startswith(f'{selected_salary_type.capitalize()} Comparison by Province')
    assert len(provincial_fig['data'][0]['x']) == len(mock_df_net_salary.columns) # All provinces
    assert provincial_fig['data'][0]['y'][0] == mock_df_net_salary['Chaco'].iloc[-1] # Chaco's latest salary

def test_dashboard_province_change(
    mock_df_net_salary, 
    mock_df_net_salary_real, 
    mock_ipc_national, 
    mock_df_cba_cbt
):
    """
    Test dashboard update when province changes.
    """
    from salary_app import app, update_dashboard # Move import here
    setup_callback_context('province-dropdown', 'Buenos Aires')
    
    selected_province = 'Buenos Aires'
    selected_salary_type = 'net'
    date_range_indices = [0, len(mock_df_net_salary.index) - 1]

    kpis, historical_fig, provincial_fig = update_dashboard(
        selected_province, selected_salary_type, date_range_indices
    )
    
    kpi_texts = [child.children for child in kpis.children]
    latest_salary = mock_df_net_salary['Buenos Aires'].iloc[-1]
    # latest_cbt = mock_df_cba_cbt['cbt'].iloc[-1] if not mock_df_cba_cbt.empty else 0

    assert f"Latest Net for Buenos Aires: ${latest_salary:,.2f}" in kpi_texts
    assert historical_fig['layout']['title']['text'] == f'{selected_province} {selected_salary_type.capitalize()} Trend (Nominal vs. Real)'
    assert provincial_fig['data'][0]['y'][1] == latest_salary # Buenos Aires's latest salary (assuming order)

def test_dashboard_salary_type_change(
    mock_df_net_salary, 
    mock_df_net_salary_real, # This will be reused as we mocked calculate_real_salary
    mock_ipc_national, 
    mock_df_cba_cbt
):
    """
    Test dashboard update when salary type changes.
    """
    from salary_app import app, update_dashboard # Move import here
    setup_callback_context('salary-type-radio', 'gross')

    selected_province = 'Chaco'
    selected_salary_type = 'gross' # Changed
    date_range_indices = [0, len(mock_df_net_salary.index) - 1]

    kpis, historical_fig, provincial_fig = update_dashboard(
        selected_province, selected_salary_type, date_range_indices
    )
    
    kpi_texts = [child.children for child in kpis.children]
    # Latest salary for gross will be the same as net in our mock_df_net_salary fixture
    latest_salary = mock_df_net_salary['Chaco'].iloc[-1]
    # latest_cbt = mock_df_cba_cbt['cbt'].iloc[-1] if not mock_df_cba_cbt.empty else 0 

    assert f"Latest Gross for Chaco: ${latest_salary:,.2f}" in kpi_texts
    assert historical_fig['data'][1]['name'] == f'{selected_salary_type.capitalize()} (Real)'
    assert historical_fig['layout']['title']['text'] == f'{selected_province} {selected_salary_type.capitalize()} Trend (Nominal vs. Real)'
    assert provincial_fig['layout']['title']['text'].startswith(f'{selected_salary_type.capitalize()} Comparison by Province')

def test_dashboard_date_range_change(
    mock_df_net_salary, 
    mock_df_net_salary_real, 
    mock_ipc_national, 
    mock_df_cba_cbt
):
    """
    Test dashboard update when date range changes.
    """
    from salary_app import app, update_dashboard # Move import here
    # Select only the last two data points
    setup_callback_context('date-range-slider', [len(mock_df_net_salary.index) - 2, len(mock_df_net_salary.index) - 1])

    selected_province = 'Chaco'
    selected_salary_type = 'net'
    date_range_indices = [len(mock_df_net_salary.index) - 2, len(mock_df_net_salary.index) - 1]

    kpis, historical_fig, provincial_fig = update_dashboard(
        selected_province, selected_salary_type, date_range_indices
    )
    
    kpi_texts = [child.children for child in kpis.children]
    latest_salary = mock_df_net_salary['Chaco'].iloc[-1]
    # latest_cbt = mock_df_cba_cbt['cbt'].iloc[-1] if not mock_df_cba_cbt.empty else 0

    assert f"Latest Net for Chaco: ${latest_salary:,.2f}" in kpi_texts
    assert len(historical_fig['data'][0]['x']) == 2 # Only two dates in range
    # Provincial comparison should still use the last date of the filtered range
    assert provincial_fig['data'][0]['y'][0] == latest_salary
