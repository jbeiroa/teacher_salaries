import pytest
import pandas as pd
import numpy as np
from dash import html
import dash_bootstrap_components as dbc
from unittest.mock import patch, MagicMock

# Import the updated callback
from salary_app import update_dashboard

@pytest.fixture
def mock_data_dfs():
    dates = pd.to_datetime(['2023-03-01', '2023-06-01', '2023-09-01', '2023-12-01', '2024-03-01'])
    provinces = ["Chaco", "Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Promedio Ponderado (MG Total)"]
    
    # Salaries
    df_nom = pd.DataFrame({p: [100000.0 * (1.1**i) for i in range(5)] for p in provinces}, index=dates)
    
    # IPC with multiple categories
    df_ipc = pd.DataFrame({
        'infl_Nivel_general': [100, 110, 121, 133.1, 146.41],
        'infl_Alimentos_bebidas': [100, 115, 132, 152, 175]
    }, index=dates)
    
    return df_nom, df_ipc

def test_kpi_card_structure():
    """Verify that create_kpi_card produces the Nominal (Big) / Real (Small) structure."""
    from salary_app import create_kpi_card
    
    card = create_kpi_card("Test KPI", "$100,000", -5.2)
    
    # Card is dbc.Card(dbc.CardBody([H6, H4, Small]))
    # card.children is the CardBody
    body = card.children
    # body.children is the list [H6, H4, Small]
    assert body.children[1].children == "$100,000"
    assert body.children[2].children == "Real Var: -5.2%"
    assert "text-danger" in body.children[2].className

def test_update_dashboard_logic(mock_data_dfs):
    df_nom, df_ipc = mock_data_dfs
    
    with patch('salary_app.df_net_salary', df_nom), \
         patch('salary_app.df_ipc', df_ipc), \
         patch('salary_app.df_cba_cbt', pd.DataFrame(columns=['cbt'])):
        
        outputs = update_dashboard(
            "Chaco", "net", ["nominal", "real"], "infl_Alimentos_bebidas", 
            "2023-03-01", "2024-03-01", 4
        )
        
        kpi_latest, kpi_q, kpi_a, kpi_i, fig_hist, fig_comp, comp_header = outputs
        
        # Verify trace name for dynamic inflation
        assert fig_hist.data[1].name == "Real (Alimentos bebidas)"
        
        # Verify Quarterly Real Var
        # Nominal: +10%
        # Category: +15.13%
        # Real: -4.5% approx
        body_q = kpi_q.children
        assert "Real Var: -4.5%" in body_q.children[2].children

def test_comparison_chart_sorting(mock_data_dfs):
    df_nom, df_ipc = mock_data_dfs
    df_nom.iloc[4] = [100000, 400000, 200000, 300000]
    
    with patch('salary_app.df_net_salary', df_nom), \
         patch('salary_app.df_ipc', df_ipc), \
         patch('salary_app.df_cba_cbt', pd.DataFrame()):
        
        outputs = update_dashboard(
            "Chaco", "net", ["nominal"], "infl_Nivel_general", 
            "2023-03-01", "2024-03-01", 4
        )
        fig_comp = outputs[5]
        
        assert list(fig_comp.data[0].x) == [100000, 200000, 300000, 400000]
        assert list(fig_comp.data[0].y) == ["Chaco", "Ciudad Autónoma de Buenos Aires", "Promedio Ponderado (MG Total)", "Buenos Aires"]
