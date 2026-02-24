import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, callback, Output, Input, State, no_update, callback_context
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from salary_data.scraper import Scraper
from datetime import datetime

# --- Data Loading ---
scraper = Scraper()

# Pre-load and align data to start from Dec 2016 (INDEC IPC start)
START_LIMIT = '2016-12-01'

df_net_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO).loc[START_LIMIT:]
df_gross_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_BRUTO).loc[START_LIMIT:]
df_basic_salary = scraper.get_cgecse_salaries(scraper.URL_BASICO).loc[START_LIMIT:]

df_ipc = scraper.get_ipc_indec().loc[START_LIMIT:]

df_cba_cbt = scraper.get_cba_cbt().loc[START_LIMIT:]
if not df_cba_cbt.empty:
    df_cba_cbt.rename(columns={
        'canasta_basica_total': 'cbt',
        'canasta_basica_alimentaria': 'cba'
    }, inplace=True)

# --- Translations ---
TRANSLATIONS = {
    'es': {
        'title': "Tablero de Salarios Docentes - Argentina",
        'filters': "Filtros",
        'province': "Provincia:",
        'salary_type': "Tipo de Salario:",
        'adjustment': "Ajuste:",
        'inf_cat': "Categoría de Inflación:",
        'base_date': "Fecha Base (Ajuste Inflación):",
        'date_range': "Rango de Fechas Histórico:",
        'net': "Neto",
        'gross': "Bruto",
        'basic': "Básico",
        'nominal': "Mostrar Nominal",
        'real': "Mostrar Real (Ajustado)",
        'cbt': "Mostrar Línea de Pobreza (CBT)",
        'hist_trend': "Tendencia Histórica",
        'prov_comp': "Comparación Provincial",
        'latest': "Último",
        'q_var': "Var. Trimestral",
        'a_var': "Acum. Anual",
        'i_var': "Var. Interanual",
        'real_var_prefix': "Var. Real:",
        'comp_header_prefix': "Comparación Provincial",
        'xaxis_salary': "Monto Salarial ($)",
        'nom_trace': "Nominal",
        'cbt_trace': "Línea de Pobreza (CBT)",
        'instr_btn': "Instrucciones",
        'instr_title': "Acerca de este Tablero",
        'instr_body': [
            "Este tablero muestra datos para el cargo de Maestro de Grado con 10 años de antigüedad (MG10), una categoría de referencia para las negociaciones salariales en Argentina. Los datos son recolectados de la ",
            html.A("CGECSE", href="https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/cgecse", target="_blank"),
            " e ",
            html.A("INDEC", href="https://www.indec.gob.ar/", target="_blank"),
            "."
        ]
    },
    'en': {
        'title': "Teacher Salaries Dashboard - Argentina",
        'filters': "Filters",
        'province': "Province:",
        'salary_type': "Salary Type:",
        'adjustment': "Adjustment:",
        'inf_cat': "Inflation Category:",
        'base_date': "Base Date (Inflation Adj.):",
        'date_range': "Historical Date Range:",
        'net': "Net",
        'gross': "Gross",
        'basic': "Basic",
        'nominal': "Show Nominal",
        'real': "Show Real (Adjusted)",
        'cbt': "Show Poverty Line (CBT)",
        'hist_trend': "Historical Trend",
        'prov_comp': "Provincial Comparison",
        'latest': "Latest",
        'q_var': "Quarterly Var.",
        'a_var': "Annual Acc.",
        'i_var': "Inter-annual Var.",
        'real_var_prefix': "Real Var:",
        'comp_header_prefix': "Provincial Comparison",
        'xaxis_salary': "Salary Amount ($)",
        'nom_trace': "Nominal",
        'cbt_trace': "Poverty Line (CBT)",
        'instr_btn': "Instructions",
        'instr_title': "About this Dashboard",
        'instr_body': [
            "This dashboard displays data for the 'Maestro de Grado' (Primary School Teacher) position with 10 years of seniority (MG10), a benchmark category for salary negotiations in Argentina. Data is sourced from ",
            html.A("CGECSE", href="https://www.argentina.gob.ar/educacion/evaluacion-e-informacion-educativa/cgecse", target="_blank"),
            " and ",
            html.A("INDEC", href="https://www.indec.gob.ar/", target="_blank"),
            "."
        ]
    }
}

# --- Helper Functions ---
def create_kpi_card(title, nominal_value, real_variation=None, lang='es'):
    """Creates a Bootstrap card showing nominal value and real variation subtext."""
    color = "text-dark"
    var_text = ""
    prefix = TRANSLATIONS[lang]['real_var_prefix']
    
    if real_variation is not None:
        color = "text-success" if real_variation >= 0 else "text-danger"
        var_text = f"{prefix} {real_variation:+.1f}%"

    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-subtitle text-muted mb-2"),
            html.H4(nominal_value, className="card-title text-dark"),
            html.Small(var_text, className=f"{color} fw-bold")
        ]),
        className="shadow-sm mb-4"
    )

def get_variation_metrics(nom_series, real_series):
    """Calculates variation metrics for both nominal and real series."""
    if nom_series.empty or real_series.empty:
        return {
            "latest_nom": 0, 
            "q_nom": 0, "a_nom": 0, "i_nom": 0,
            "q_real": 0, "a_real": 0, "i_real": 0
        }
    
    # We calculate variations on the full series but report the latest
    v_nom = scraper.calculate_variations(nom_series)
    v_real = scraper.calculate_variations(real_series)
    
    return {
        "latest_nom": nom_series.iloc[-1],
        "q_nom": v_nom['quarterly'].iloc[-1] if not v_nom.empty else 0,
        "a_nom": v_nom['annual_acc'].iloc[-1] if not v_nom.empty else 0,
        "i_nom": v_nom['interannual'].iloc[-1] if not v_nom.empty else 0,
        "q_real": v_real['quarterly'].iloc[-1] if not v_real.empty else 0,
        "a_real": v_real['annual_acc'].iloc[-1] if not v_real.empty else 0,
        "i_real": v_real['interannual'].iloc[-1] if not v_real.empty else 0
    }

# --- App Initialization ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

# --- Layout ---
app.layout = dbc.Container([
    dcc.Store(id='lang-store', data='es'),
    dbc.Row([
        dbc.Col([
            dbc.Button("?", id="open-offcanvas", n_clicks=0, color="info", outline=True, size="sm", className="mt-4")
        ], width=1, className="text-start"),
        dbc.Col([
            html.H1(id='app-title', className="text-center mt-4")
        ], width=10),
        dbc.Col([
            html.Div([
                dbc.Button("ES", id="btn-es", size="sm", color="primary", outline=True, className="me-1"),
                dbc.Button("EN", id="btn-en", size="sm", color="primary", outline=True)
            ], className="text-end mt-4")
        ], width=1, className="text-end")
    ], align="center", className="mb-4"),

    dbc.Offcanvas(
        id="offcanvas-usage",
        is_open=False,
    ),

    dbc.Row([
        # Sidebar/Controls
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(id='sidebar-header', className="fw-bold"),
                dbc.CardBody([
                    html.Label(id='label-province', className="mt-2"),
                    dcc.Dropdown(
                        id='province-dropdown',
                        options=[{'label': col, 'value': col} for col in df_net_salary.columns],
                        value='Chaco',
                        clearable=False,
                        className="mb-3"
                    ),
                    html.Label(id='label-salary-type'),
                    dcc.RadioItems(
                        id='salary-type-radio',
                        options=[], # Loaded via callback
                        value='net',
                        inline=True,
                        className="mb-3",
                        inputStyle={"margin-right": "5px", "margin-left": "15px"}
                    ),
                    html.Label(id='label-adjustment'),
                    dbc.Checklist(
                        id='adjustment-toggle',
                        options=[], # Loaded via callback
                        value=['nominal', 'real'],
                        switch=True,
                        className="mb-3"
                    ),
                    html.Label(id='label-infl-cat'),
                    dcc.Dropdown(
                        id='inflation-category-dropdown',
                        options=[{'label': col.replace('infl_', '').replace('_', ' '), 'value': col} for col in df_ipc.columns],
                        value='infl_Nivel_general',
                        clearable=False,
                        className="mb-3"
                    ),
                    html.Label(id='label-base-date'),
                    dcc.Dropdown(
                        id='base-date-dropdown',
                        options=[{'label': d.strftime("%Y-%m"), 'value': d.strftime("%Y-%m-%d")} for d in df_ipc.index],
                        value=df_ipc.index[-1].strftime("%Y-%m-%d"),
                        clearable=False,
                        className="mb-3"
                    ),
                    html.Label(id='label-date-range'),
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        min_date_allowed=df_net_salary.index[0],
                        max_date_allowed=df_net_salary.index[-1],
                        start_date=df_net_salary.index[-13], # ~3 years
                        end_date=df_net_salary.index[-1],
                        display_format='YYYY-MM',
                        className="mb-3"
                    )
                ])
            ], className="shadow-sm mb-4")
        ], width=12, lg=3),

        # Main Content
        dbc.Col([
            # KPIs Row
            dbc.Row([
                dbc.Col(id='kpi-latest', width=12, md=3),
                dbc.Col(id='kpi-quarterly', width=12, md=3),
                dbc.Col(id='kpi-annual', width=12, md=3),
                dbc.Col(id='kpi-interannual', width=12, md=3),
            ]),

            # Charts Row
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(id='trend-header', className="fw-bold"),
                        dbc.CardBody(dcc.Graph(id='historical-trend-chart', config={'displayModeBar': False}))
                    ], className="shadow-sm mb-4")
                ], width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            dbc.Row([
                                dbc.Col(id="comparison-header", className="fw-bold", width=8),
                                dbc.Col(
                                    dcc.Dropdown(
                                        id='comparison-month-dropdown',
                                        options=[{'label': d.strftime("%Y-%m"), 'value': i} for i, d in enumerate(df_net_salary.index)],
                                        value=len(df_net_salary.index) - 1,
                                        clearable=False,
                                        style={'fontSize': '0.9rem'}
                                    ), width=4
                                )
                            ], align="center")
                        ]),
                        dbc.CardBody(dcc.Graph(id='provincial-comparison-chart', config={'displayModeBar': False}, style={'height': '600px'}))
                    ], className="shadow-sm mb-4")
                ], width=12),
            ])
        ], width=12, lg=9)
    ])
], fluid=True)

# --- Callbacks ---
@app.callback(
    Output("offcanvas-usage", "is_open"),
    Input("open-offcanvas", "n_clicks"),
    [State("offcanvas-usage", "is_open")],
)
def toggle_offcanvas(n1, is_open):
    if n1:
        return not is_open
    return is_open

@app.callback(
    Output('lang-store', 'data'),
    Input('btn-es', 'n_clicks'),
    Input('btn-en', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_language(btn_es, btn_en):
    ctx = callback_context.triggered[0]['prop_id']
    if 'btn-es' in ctx:
        return 'es'
    return 'en'

@app.callback(
    Output('app-title', 'children'),
    Output('sidebar-header', 'children'),
    Output('label-province', 'children'),
    Output('label-salary-type', 'children'),
    Output('label-adjustment', 'children'),
    Output('label-infl-cat', 'children'),
    Output('label-base-date', 'children'),
    Output('label-date-range', 'children'),
    Output('trend-header', 'children'),
    Output('salary-type-radio', 'options'),
    Output('adjustment-toggle', 'options'),
    Output('offcanvas-usage', 'title'),
    Output('offcanvas-usage', 'children'),
    Output('open-offcanvas', 'children'),
    Input('lang-store', 'data')
)
def update_ui_language(lang):
    t = TRANSLATIONS[lang]
    salary_options = [
        {'label': ' ' + t['net'], 'value': 'net'},
        {'label': ' ' + t['gross'], 'value': 'gross'},
        {'label': ' ' + t['basic'], 'value': 'basic'},
    ]
    adj_options = [
        {'label': ' ' + t['nominal'], 'value': 'nominal'},
        {'label': ' ' + t['real'], 'value': 'real'},
        {'label': ' ' + t['cbt'], 'value': 'cbt'},
    ]
    return (
        t['title'], t['filters'], t['province'], t['salary_type'], 
        t['adjustment'], t['inf_cat'], t['base_date'], t['date_range'],
        t['hist_trend'], salary_options, adj_options, t['instr_title'], 
        t['instr_body'], "?"
    )

@app.callback(
    Output('kpi-latest', 'children'),
    Output('kpi-quarterly', 'children'),
    Output('kpi-annual', 'children'),
    Output('kpi-interannual', 'children'),
    Output('historical-trend-chart', 'figure'),
    Output('provincial-comparison-chart', 'figure'),
    Output('comparison-header', 'children'),
    Input('province-dropdown', 'value'),
    Input('salary-type-radio', 'value'),
    Input('adjustment-toggle', 'value'),
    Input('inflation-category-dropdown', 'value'),
    Input('base-date-dropdown', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('comparison-month-dropdown', 'value'),
    Input('lang-store', 'data')
)
def update_dashboard(selected_province, salary_type, adjustments, infl_cat, base_date, start_date, end_date, comp_month_idx, lang):
    t = TRANSLATIONS[lang]
    
    # Data selection
    if salary_type == 'net':
        df_nom = df_net_salary
    elif salary_type == 'gross':
        df_nom = df_gross_salary
    else:
        df_nom = df_basic_salary

    # Dynamic real salary calculation
    ipc_series = df_ipc[infl_cat]
    df_real = scraper.calculate_real_salary(df_nom, ipc_series, base_date=base_date)

    # Date filtering
    mask = (df_nom.index >= start_date) & (df_nom.index <= end_date)
    df_nom_filt = df_nom.loc[mask]
    df_real_filt = df_real.loc[mask]
    
    # Variations calculation based on full series for accuracy
    metrics = get_variation_metrics(df_nom[selected_province], df_real[selected_province])
    
    # KPI components
    kpi_latest = create_kpi_card(f"{t['latest']} {t[salary_type]}", f"${metrics['latest_nom']:,.0f}", lang=lang)
    kpi_q = create_kpi_card(t['q_var'], f"{metrics['q_nom']:+.1f}%", metrics['q_real'], lang=lang)
    kpi_a = create_kpi_card(t['a_var'], f"{metrics['a_nom']:+.1f}%", metrics['a_real'], lang=lang)
    kpi_i = create_kpi_card(t['i_var'], f"{metrics['i_nom']:+.1f}%", metrics['i_real'], lang=lang)

    # Historical Trend Chart
    fig_hist = go.Figure()
    
    if 'nominal' in adjustments:
        fig_hist.add_trace(go.Scatter(
            x=df_nom_filt.index, y=df_nom_filt[selected_province],
            name=t['nom_trace'], line=dict(color='#2c3e50', width=3)
        ))
    
    if 'real' in adjustments:
        cat_name = infl_cat.replace('infl_', '').replace('_', ' ')
        real_label = "Real" if lang == 'en' else "Real"
        fig_hist.add_trace(go.Scatter(
            x=df_real_filt.index, y=df_real_filt[selected_province],
            name=f"{real_label} ({cat_name})", line=dict(color='#18bc9c', width=3)
        ))
        
    if 'cbt' in adjustments and not df_cba_cbt.empty:
        cbt_filtered = df_cba_cbt['cbt'].reindex(df_nom.index, method='ffill').loc[start_date:end_date]
        fig_hist.add_trace(go.Scatter(
            x=cbt_filtered.index, y=cbt_filtered,
            name=t['cbt_trace'], line=dict(color='#e74c3c', dash='dash')
        ))

    fig_hist.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        template="plotly_white"
    )

    # Provincial Comparison Chart
    comp_date = df_nom.index[comp_month_idx]
    comp_data = df_nom.loc[comp_date].sort_values(ascending=True)
    
    colors = ['#bdc3c7'] * len(comp_data)
    if selected_province in comp_data.index:
        idx = comp_data.index.get_loc(selected_province)
        colors[idx] = '#2c3e50'

    fig_comp = go.Figure(go.Bar(
        x=comp_data.values,
        y=comp_data.index,
        orientation='h',
        marker_color=colors,
        text=[f"${x:,.0f}" for x in comp_data.values],
        textposition='outside',
        cliponaxis=False
    ))
    
    fig_comp.update_layout(
        margin=dict(l=150, r=50, t=20, b=20),
        template="plotly_white",
        xaxis_title=t['xaxis_salary'],
        bargap=0.15,
        yaxis=dict(tickfont=dict(size=11))
    )

    comp_header = f"{t['comp_header_prefix']} ({comp_date.strftime('%Y-%m')})"

    return kpi_latest, kpi_q, kpi_a, kpi_i, fig_hist, fig_comp, comp_header

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
