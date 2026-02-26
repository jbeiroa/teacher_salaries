import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, callback, Output, Input, State, no_update, callback_context
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from salary_data.scraper import Scraper
from salary_data.analytics import AnalyticsPipeline
from datetime import datetime
import os
import re

# --- Data Loading ---
scraper = Scraper()

# Load analytics artifacts
pipeline = AnalyticsPipeline()
df_clusters, df_anomalies = pipeline.load_latest_artifacts()
HAS_ANALYTICS = df_clusters is not None

# Load and Parse Reports
REPORT_SECTIONS = {
    "es": {"intro": "", "clusters": [], "synthesis": ""},
    "en": {"intro": "", "clusters": [], "synthesis": ""}
}

def process_citations(text):
    """Converts citation numbers in [[N]] format to superscript links."""
    # 1. Citations in text: Match [[N]] and convert to <sup><a href="#refN">N</a></sup>
    text = re.sub(r'\[\[(\d{1,2})\]\]', r'<sup><a href="#ref\1">\1</a></sup>', text)
    
    # 2. Reference list anchors:
    # Match a line starting with 1. or 24. in the References section
    text = re.sub(r'^(\d{1,2})\.', r'<a id="ref\1"></a>\1.', text, flags=re.MULTILINE)
    return text

def parse_report(path, lang):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        content = f.read()
        sections = re.split(r'\n(?=## \*\*)', content)
        intro_parts = []
        cluster_start_idx = -1
        for idx, s in enumerate(sections):
            if "## **Cluster 1:" in s:
                cluster_start_idx = idx
                break
            intro_parts.append(s)
        
        REPORT_SECTIONS[lang]["intro"] = process_citations("\n\n".join(intro_parts).strip())
        
        if cluster_start_idx != -1:
            synthesis_parts = []
            for s in sections[cluster_start_idx:]:
                if "## **Cluster" in s:
                    REPORT_SECTIONS[lang]["clusters"].append(process_citations(s.strip()))
                else:
                    synthesis_parts.append(s.strip())
            
            if synthesis_parts:
                REPORT_SECTIONS[lang]["synthesis"] = process_citations("\n\n".join(synthesis_parts).strip())

parse_report("reports/cluster_analysis_report.md", "en")
parse_report("reports/cluster_analysis_report_es.md", "es")

# Pre-load and align data to start from Dec 2016 (INDEC IPC start)
START_LIMIT = '2016-12-01'

df_net_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO).loc[START_LIMIT:]
df_gross_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_BRUTO).loc[START_LIMIT:]
df_basic_salary = scraper.get_cgecse_salaries(scraper.URL_BASICO).loc[START_LIMIT:]

df_ipc = scraper.get_ipc_indec().loc[START_LIMIT:]

df_cba_cbt = scraper.get_cba_cbt().loc[START_LIMIT:]

# --- Translations ---
TRANSLATIONS = {
    'es': {
        'title': "Tablero de Salarios Docentes - Argentina",
        'filters': "Filtros",
        'province': "Provincia:",
        'salary_type': "Tipo de Salario:",
        'adjustment': "Ajuste:",
        'ref_line': "Línea de Referencia:",
        'inf_cat': "Categoría de Inflación:",
        'base_date': "Fecha Base (Ajuste Inflación):",
        'date_range': "Rango de Fechas Histórico:",
        'net': "Neto",
        'gross': "Bruto",
        'basic': "Básico",
        'nominal': "Mostrar Nominal",
        'real': "Mostrar Real (Ajustado)",
        'cbt': "Mostrar Línea de Ref.",
        'hist_trend': "Tendencia Histórica (salarios en AR$)",
        'hist_trend_base100': "Tendencia Histórica (Base 100 Índice)",
        'base100_toggle': "Mostrar como Índice (Base 100)",
        'prov_comp': "Comparación Provincial",
        'latest': "Último",
        'q_var': "Var. Trimestral",
        'a_var': "Acum. Anual",
        'i_var': "Var. Interanual",
        'real_var_prefix': "Var. Real:",
        'comp_header_prefix': "Comparación Provincial",
        'xaxis_salary': "Monto Salarial ($)",
        'xaxis_index': "Índice (Base 100)",
        'nom_trace': "Nominal",
        'instr_btn': "Instrucciones",
        'instr_title': "Acerca de este Tablero",
        'instr_body': [
            html.P("Este tablero permite analizar la evolución del poder adquisitivo de los docentes en Argentina."),
            html.B("Filtros Principales:"),
            html.Ul([
                html.Li("Provincia y Tipo de Salario: Seleccione la jurisdicción y si desea ver el Neto (bolsillo), Bruto o Básico."),
                html.Li("Mostrar Real: Activa el ajuste por inflación. Si está desactivado, verá valores nominales."),
                html.Li("Mostrar Línea de Ref: Muestra canastas básicas (CBA/CBT) o líneas de pobreza/indigencia para comparar el salario frente al costo de vida."),
                html.Li("Mostrar como Índice: Transforma los gráficos en porcentaje de crecimiento relativo a la 'Fecha Base' seleccionada. Útil para comparar quién ganó o perdió más desde un momento específico."),
            ]),
            html.B("Analítica y Anomalías:"),
            html.Ul([
                html.Li("Icono ⚠️: Indica una caída anómala en el salario real (pérdida brusca de poder adquisitivo)."),
                html.Li("Icono ✨: Indica un aumento anómalo (generalmente bonos extraordinarios o retroactivos)."),
                html.Li("Pestaña Analítica Avanzada: Muestra grupos de provincias (Clusters) con comportamientos similares identificados mediante Machine Learning."),
            ])
        ],
        'cba_adult': "CBA (Adulto Equivalente)",
        'cbt_adult': "CBT (Adulto Equivalente)",
        'indigency_fam': "Línea Indigencia (Familia)",
        'poverty_fam': "Línea Pobreza (Familia)",
        'tab_general': "Tablero Principal",
        'tab_analytics': "Analítica Avanzada",
        'analytics_cluster_title': "Análisis de Clusters (Comportamiento Salarial)",
        'analytics_cluster_desc': "Las provincias han sido agrupadas por un modelo de Machine Learning (K-Shape) según cómo sus salarios reales reaccionan a lo largo del tiempo frente a la inflación y las políticas locales.",
        'cluster_label': "Cluster",
        'no_analytics': "Datos analíticos no disponibles. Ejecute el pipeline de entrenamiento.",
        'ipc_label': "IPC"
    },
    'en': {
        'title': "Teacher Salaries Dashboard - Argentina",
        'filters': "Filters",
        'province': "Province:",
        'salary_type': "Salary Type:",
        'adjustment': "Adjustment:",
        'ref_line': "Reference Line:",
        'inf_cat': "Inflation Category:",
        'base_date': "Base Date (Inflation Adj.):",
        'date_range': "Historical Date Range:",
        'net': "Net",
        'gross': "Gross",
        'basic': "Basic",
        'nominal': "Show Nominal",
        'real': "Show Real (Adjusted)",
        'cbt': "Show Ref. Line",
        'hist_trend': "Historical Trend (salaries in AR$)",
        'hist_trend_base100': "Historical Trend (Base 100 Index)",
        'base100_toggle': "Show as Index (Base 100)",
        'prov_comp': "Provincial Comparison",
        'latest': "Latest",
        'q_var': "Var. Trimestral",
        'a_var': "Acum. Anual",
        'i_var': "Var. Interanual",
        'real_var_prefix': "Var. Real:",
        'comp_header_prefix': "Provincial Comparison",
        'xaxis_salary': "Salary Amount ($)",
        'xaxis_index': "Index (Base 100)",
        'nom_trace': "Nominal",
        'instr_btn': "Instructions",
        'instr_title': "About this Dashboard",
        'instr_body': [
            html.P("This dashboard analyzes the evolution of teacher purchasing power in Argentina."),
            html.B("Main Filters:"),
            html.Ul([
                html.Li("Province & Salary Type: Select the jurisdiction and whether to see Net (take-home), Gross, or Basic salary."),
                html.Li("Show Real: Enables inflation adjustment. If off, you see nominal values."),
                html.Li("Show Ref. Line: Displays basic baskets (CBA/CBT) or poverty/indigency lines to compare salary against cost of living."),
                html.Li("Show as Index: Transforms charts into percentage growth relative to the selected 'Base Date'. Useful for comparing relative gains or losses from a specific point in time."),
            ]),
            html.B("Analytics & Anomalies:"),
            html.Ul([
                html.Li("⚠️ Icon: Indicates an anomalous drop in real salary (sharp loss of purchasing power)."),
                html.Li("✨ Icon: Indicates an anomalous increase (usually extraordinary bonuses or back-pay)."),
                html.Li("Advanced Analytics Tab: Displays groups of provinces (Clusters) with similar behaviors identified through Machine Learning."),
            ])
        ],
        'cba_adult': "CBA (Adult Equivalent)",
        'cbt_adult': "CBT (Adult Equivalent)",
        'indigency_fam': "Indigency Line (Family)",
        'poverty_fam': "Poverty Line (Family)",
        'tab_general': "Main Dashboard",
        'tab_analytics': "Advanced Analytics",
        'analytics_cluster_title': "Cluster Analysis (Salary Behavior)",
        'analytics_cluster_desc': "Provinces have been grouped by a Machine Learning model (K-Shape) based on how their real salaries react over time to inflation and local policies.",
        'cluster_label': "Cluster",
        'no_analytics': "Analytics data not available. Please run the training pipeline.",
        'ipc_label': "CPI"
    }
}

# --- Helper Functions ---
def format_localized(value, lang='es', decimals=0):
    """Formats a number according to the language's locale (thousands and decimal separators)."""
    if value is None or pd.isna(value):
        return "-"
    
    # Standard python formatting first
    try:
        if decimals == 0:
            formatted = f"{int(round(value)):,}"
        else:
            formatted = f"{value:,.{decimals}f}"
    except (ValueError, OverflowError):
        return "-"
        
    if lang == 'es':
        # Swap , and . for Spanish
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return formatted

def create_kpi_card(title, nominal_value, nom_variation=None, ipc_variation=None, real_variation=None, lang='es'):
    """Creates a Bootstrap card showing nominal value, nominal variation vs inflation, and real variation."""
    color_real = "text-dark"
    var_real_text = "\u00A0" # Use non-breaking space to preserve layout
    prefix_real = TRANSLATIONS[lang]['real_var_prefix']
    
    # 1. Real Variation Subtext
    if real_variation is not None and not pd.isna(real_variation):
        color_real = "text-success" if real_variation >= 0 else "text-danger"
        var_real_val = format_localized(real_variation, lang=lang, decimals=1)
        var_real_text = f"{prefix_real} {var_real_val}%"

    # 2. Nominal vs Inflation Subtext
    var_comp_text = "\u00A0" # Use non-breaking space
    if nom_variation is not None and not pd.isna(nom_variation) and ipc_variation is not None:
        nom_fmt = format_localized(nom_variation, lang=lang, decimals=1)
        ipc_fmt = format_localized(ipc_variation, lang=lang, decimals=1)
        ipc_lbl = TRANSLATIONS[lang]['ipc_label']
        var_comp_text = f"Nom: {nom_fmt}% | {ipc_lbl}: {ipc_fmt}%"

    return dbc.Card(
        dbc.CardBody([
            html.H6(title, className="card-subtitle text-muted mb-1 text-center", style={'fontSize': '0.85rem'}),
            html.H4(nominal_value, className="card-title text-dark mb-1 text-center", style={'fontSize': '1.8rem', 'fontWeight': 'bold'}),
            html.Div([
                html.Small(var_comp_text, className="text-muted d-block text-center", style={'fontSize': '0.75rem', 'minHeight': '1rem'}),
                html.Small(var_real_text, className=f"{color_real} fw-bold d-block text-center", style={'fontSize': '0.85rem', 'minHeight': '1.2rem'})
            ])
        ], className="d-flex flex-column justify-content-center p-3"),
        className="shadow-sm h-100" # Ensure cards in a row have same height
    )

def get_variation_metrics(nom_series, real_series, ipc_series):
    """Calculates variation metrics for nominal, real, and inflation series."""
    if nom_series.empty or real_series.empty or ipc_series.empty:
        return {
            "latest_nom": 0, 
            "q_nom": 0, "a_nom": 0, "i_nom": 0,
            "q_real": 0, "a_real": 0, "i_real": 0,
            "q_ipc": 0, "a_ipc": 0, "i_ipc": 0
        }
    
    # CRITICAL FIX: Align IPC to the same frequency as salaries (Quarterly)
    # This ensures "Quarterly" for IPC is also 3 months, matching salaries.
    ipc_aligned = ipc_series.reindex(nom_series.index, method='ffill')
    
    v_nom = scraper.calculate_variations(nom_series)
    v_real = scraper.calculate_variations(real_series)
    v_ipc = scraper.calculate_variations(ipc_aligned)
    
    return {
        "latest_nom": nom_series.iloc[-1],
        "q_nom": v_nom['quarterly'].iloc[-1] if not v_nom.empty else 0,
        "a_nom": v_nom['annual_acc'].iloc[-1] if not v_nom.empty else 0,
        "i_nom": v_nom['interannual'].iloc[-1] if not v_nom.empty else 0,
        "q_real": v_real['quarterly'].iloc[-1] if not v_real.empty else 0,
        "a_real": v_real['annual_acc'].iloc[-1] if not v_real.empty else 0,
        "i_real": v_real['interannual'].iloc[-1] if not v_real.empty else 0,
        "q_ipc": v_ipc['quarterly'].iloc[-1] if not v_ipc.empty else 0,
        "a_ipc": v_ipc['annual_acc'].iloc[-1] if not v_ipc.empty else 0,
        "i_ipc": v_ipc['interannual'].iloc[-1] if not v_ipc.empty else 0,
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
                        value=['real', 'cbt'],
                        switch=True,
                        className="mb-3"
                    ),
                    html.Label(id='label-ref-line'),
                    dcc.Dropdown(
                        id='ref-line-dropdown',
                        options=[], # Loaded via callback
                        value='linea_pobreza',
                        clearable=False,
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
                        value=df_net_salary.index[-1].strftime("%Y-%m-%d"),
                        clearable=False,
                        className="mb-3"
                    ),
                    html.Label(id='label-date-range'),
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        min_date_allowed=df_net_salary.index[0],
                        max_date_allowed=df_net_salary.index[-1],
                        start_date=df_net_salary.index[0], # Dec 2016
                        end_date=df_net_salary.index[-1],
                        display_format='YYYY-MM',
                        className="mb-3"
                    )
                ])
            ], className="shadow-sm mb-4")
        ], width=12, lg=3),

        # Main Content
        dbc.Col([
            dbc.Tabs([
                dbc.Tab(label="Dashboard", tab_id="tab-general", id="tab-general", children=[
                    # KPIs Row
                    dbc.Row([
                        dbc.Col(id='kpi-latest', width=12, md=3),
                        dbc.Col(id='kpi-quarterly', width=12, md=3),
                        dbc.Col(id='kpi-annual', width=12, md=3),
                        dbc.Col(id='kpi-interannual', width=12, md=3),
                    ], className="mt-3 mb-4"),

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
                ]),
                dbc.Tab(label="Analytics", tab_id="tab-analytics", id="tab-analytics", children=[
                    dcc.Store(id='analytics-carousel-index', data=0),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='analytics-report-container', className="mt-3"),
                            html.Div([
                                dbc.ButtonGroup([
                                    dbc.Button("←", id="analytics-prev", color="secondary", outline=True, size="sm"),
                                    dbc.Button(id="analytics-progress", color="secondary", outline=True, size="sm", disabled=True, style={"minWidth": "100px"}),
                                    dbc.Button("→", id="analytics-next", color="secondary", outline=True, size="sm"),
                                ], className="shadow-sm")
                            ], className="d-flex justify-content-center mt-3 mb-5")
                        ], width=12)
                    ])
                ])
            ], id="main-tabs", active_tab="tab-general")
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
    Output('label-ref-line', 'children'),
    Output('label-infl-cat', 'children'),
    Output('label-base-date', 'children'),
    Output('label-date-range', 'children'),
    Output('salary-type-radio', 'options'),
    Output('adjustment-toggle', 'options'),
    Output('ref-line-dropdown', 'options'),
    Output('offcanvas-usage', 'title'),
    Output('offcanvas-usage', 'children'),
    Output('open-offcanvas', 'children'),
    Output('tab-general', 'label'),
    Output('tab-analytics', 'label'),
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
        {'label': ' ' + t['real'], 'value': 'real'},
        {'label': ' ' + t['cbt'], 'value': 'cbt'},
        {'label': ' ' + t['base100_toggle'], 'value': 'index'},
    ]
    ref_options = [
        {'label': t['cba_adult'], 'value': 'canasta_basica_alimentaria'},
        {'label': t['cbt_adult'], 'value': 'canasta_basica_total'},
        {'label': t['indigency_fam'], 'value': 'linea_indigencia'},
        {'label': t['poverty_fam'], 'value': 'linea_pobreza'},
    ]
    return (
        t['title'], t['filters'], t['province'], t['salary_type'], 
        t['adjustment'], t['ref_line'], t['inf_cat'], t['base_date'], 
        t['date_range'], salary_options, adj_options, 
        ref_options, t['instr_title'], t['instr_body'], "?",
        t['tab_general'], t['tab_analytics']
    )

@app.callback(
    Output('analytics-carousel-index', 'data'),
    Input('analytics-prev', 'n_clicks'),
    Input('analytics-next', 'n_clicks'),
    State('analytics-carousel-index', 'data'),
    prevent_initial_call=True
)
def navigate_carousel(prev_clicks, next_clicks, current_index):
    ctx = callback_context.triggered[0]['prop_id']
    # Total slides: 1 (Intro) + 6 (Clusters) + 1 (Synthesis) = 8
    total_slides = 8
    
    if 'analytics-prev' in ctx:
        return (current_index - 1) % total_slides
    elif 'analytics-next' in ctx:
        return (current_index + 1) % total_slides
    return current_index

@app.callback(
    Output('kpi-latest', 'children'),
    Output('kpi-quarterly', 'children'),
    Output('kpi-annual', 'children'),
    Output('kpi-interannual', 'children'),
    Output('historical-trend-chart', 'figure'),
    Output('provincial-comparison-chart', 'figure'),
    Output('comparison-header', 'children'),
    Output('trend-header', 'children'),
    Output('analytics-report-container', 'children'),
    Output('analytics-progress', 'children'),
    Input('province-dropdown', 'value'),
    Input('salary-type-radio', 'value'),
    Input('adjustment-toggle', 'value'),
    Input('ref-line-dropdown', 'value'),
    Input('inflation-category-dropdown', 'value'),
    Input('base-date-dropdown', 'value'),
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('comparison-month-dropdown', 'value'),
    Input('analytics-carousel-index', 'data'),
    Input('lang-store', 'data')
)
def update_dashboard(selected_province, salary_type, adjustments, ref_line_col, infl_cat, base_date, start_date, end_date, comp_month_idx, carousel_idx, lang):
    t = TRANSLATIONS[lang]
    
    # 0. Guards for None values
    if any(v is None for v in [selected_province, salary_type, adjustments, infl_cat, base_date, start_date, end_date, comp_month_idx, carousel_idx]):
        return no_update
    
    # Fallback for ref_line_col if it's missing but needed
    if ref_line_col is None:
        ref_line_col = 'linea_pobreza'

    is_base100 = 'index' in adjustments
    show_real = 'real' in adjustments
    show_nominal = not show_real
    show_ref = 'cbt' in adjustments
    
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
    
    # Variations calculation
    metrics = get_variation_metrics(df_nom[selected_province], df_real[selected_province], ipc_series)
    
    # KPI components
    latest_nom_fmt = f"${format_localized(metrics['latest_nom'], lang=lang)}"
    kpi_latest = create_kpi_card(f"{t['latest']} {t[salary_type]}", latest_nom_fmt, lang=lang)
    kpi_q = create_kpi_card(t['q_var'], f"{format_localized(metrics['q_nom'], lang=lang, decimals=1)}%", 
                            nom_variation=metrics['q_nom'], ipc_variation=metrics['q_ipc'], 
                            real_variation=metrics['q_real'], lang=lang)
    kpi_a = create_kpi_card(t['a_var'], f"{format_localized(metrics['a_nom'], lang=lang, decimals=1)}%", 
                            nom_variation=metrics['a_nom'], ipc_variation=metrics['a_ipc'], 
                            real_variation=metrics['a_real'], lang=lang)
    kpi_i = create_kpi_card(t['i_var'], f"{format_localized(metrics['i_nom'], lang=lang, decimals=1)}%", 
                            nom_variation=metrics['i_nom'], ipc_variation=metrics['i_ipc'], 
                            real_variation=metrics['i_real'], lang=lang)

    # Historical Trend Chart
    fig_hist = go.Figure()
    y_axis_title = t['xaxis_salary']
    trend_title = t['hist_trend']
    
    # Reference Line Data (Nominal)
    if show_ref and not df_cba_cbt.empty:
        df_ref_nom = df_cba_cbt[ref_line_col].reindex(df_nom.index, method='ffill')
        # Reference Line Data (Real)
        df_ref_real_full = scraper.calculate_real_salary(pd.DataFrame({'ref': df_ref_nom}), ipc_series, base_date=base_date)
        df_ref_real = df_ref_real_full['ref']
    
    if is_base100:
        try:
            b_date_dt = pd.to_datetime(base_date)
            y_axis_title = t['xaxis_index']
            trend_title = t['hist_trend_base100']
            
            if show_nominal:
                val_nom_base = df_nom.loc[b_date_dt, selected_province]
                df_nom_idx = (df_nom_filt[selected_province] / val_nom_base) * 100
                fig_hist.add_trace(go.Scatter(x=df_nom_idx.index, y=df_nom_idx, name=f"{t['nom_trace']} (Index)", line=dict(color='#2c3e50', width=3)))
                
                if show_ref:
                    # Normalize Ref Line using Salary Base Value
                    df_ref_idx = (df_ref_nom.loc[mask] / val_nom_base) * 100
                    fig_hist.add_trace(go.Scatter(x=df_ref_idx.index, y=df_ref_idx, name="Ref. Index", line=dict(color='#e74c3c', dash='dash')))
            
            elif show_real:
                val_real_base = df_real.loc[b_date_dt, selected_province]
                df_real_idx = (df_real_filt[selected_province] / val_real_base) * 100
                fig_hist.add_trace(go.Scatter(x=df_real_idx.index, y=df_real_idx, name="Real Index", line=dict(color='#18bc9c', width=3)))
                
                if show_ref:
                    # Normalize Real Ref Line using Real Salary Base Value
                    df_ref_real_idx = (df_ref_real.loc[mask] / val_real_base) * 100
                    fig_hist.add_trace(go.Scatter(x=df_ref_real_idx.index, y=df_ref_real_idx, name="Ref. Real Index", line=dict(color='#e74c3c', dash='dash')))
                    
        except Exception:
            is_base100 = False

    if not is_base100:
        if show_nominal:
            fig_hist.add_trace(go.Scatter(x=df_nom_filt.index, y=df_nom_filt[selected_province], name=t['nom_trace'], line=dict(color='#2c3e50', width=3)))
            if show_ref:
                fig_hist.add_trace(go.Scatter(x=df_ref_nom.loc[mask].index, y=df_ref_nom.loc[mask], name="Ref. (Nominal)", line=dict(color='#e74c3c', dash='dash')))
        
        elif show_real:
            fig_hist.add_trace(go.Scatter(x=df_real_filt.index, y=df_real_filt[selected_province], name="Real", line=dict(color='#18bc9c', width=3)))
            if show_ref:
                fig_hist.add_trace(go.Scatter(x=df_ref_real.loc[mask].index, y=df_ref_real.loc[mask], name="Ref. (Real)", line=dict(color='#e74c3c', dash='dash')))

    fig_hist.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        template="plotly_white",
        yaxis_title=y_axis_title
    )

    # Provincial Comparison Chart
    comp_date = df_nom.index[comp_month_idx]
    comp_data = df_nom.loc[comp_date].sort_values(ascending=True)
    
    y_labels = list(comp_data.index)
    if HAS_ANALYTICS:
        date_anomalies = df_anomalies[df_anomalies['date'] == comp_date]
        if not date_anomalies.empty:
            for i, prov in enumerate(y_labels):
                prov_anomaly = date_anomalies[date_anomalies['province'] == prov]
                if not prov_anomaly.empty and prov_anomaly.iloc[0]['anomaly'] == -1:
                    try:
                        idx_current = df_real.index.get_loc(comp_date)
                        if idx_current >= 3:
                            val_curr = df_real.iloc[idx_current][prov]
                            val_prev = df_real.iloc[idx_current-3][prov]
                            pct_diff = (val_curr - val_prev) / val_prev
                            icon = "✨" if pct_diff > 0 else "⚠️"
                            y_labels[i] = f"{icon} {prov}"
                    except:
                        y_labels[i] = f"⚠️ {prov}"
    
    colors = ['#bdc3c7'] * len(comp_data)
    if selected_province in comp_data.index:
        idx = comp_data.index.get_loc(selected_province)
        colors[idx] = '#2c3e50'

    fig_comp = go.Figure(go.Bar(
        x=comp_data.values,
        y=y_labels,
        orientation='h',
        marker_color=colors,
        text=[f"${format_localized(x, lang=lang)}" if not pd.isna(x) else "-" for x in comp_data.values],
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
    
    # Cluster Analysis Carousel Logic
    all_slides = []
    
    if HAS_ANALYTICS:
        df_long_c = df_real_filt.T.reset_index().rename(columns={df_real_filt.T.reset_index().columns[0]: 'province'})
        df_long_c = df_long_c.merge(df_clusters, on='province').melt(id_vars=['province', 'cluster'], var_name='date', value_name='real_salary')
        df_long_c['date'] = pd.to_datetime(df_long_c['date'])
        df_long_c['cluster'] = df_long_c['cluster'].astype(str)

        lang_report = REPORT_SECTIONS.get(lang, REPORT_SECTIONS["en"])

        # Slide 0: Introduction
        if lang_report["intro"]:
            all_slides.append(dbc.Card([
                dbc.CardHeader("Introduction" if lang == 'en' else "Introducción", className="fw-bold bg-light"),
                dbc.CardBody(dcc.Markdown(lang_report["intro"], dangerously_allow_html=True, className="markdown-report"))
            ], className="mb-4 shadow-sm"))
            
        # Slides 1-6: Clusters
        for i, section_text in enumerate(lang_report["clusters"]):
            title_match = re.search(r'## \*\*Cluster \d: (.*?)\*\*', section_text)
            display_idx = i + 1
            if title_match:
                card_title = f"Cluster {display_idx}: {title_match.group(1)}"
                body_text = re.sub(r'## \*\*Cluster \d:.*?\*\*', '', section_text).strip()
            else:
                card_title = f"Deep Dive: Cluster {display_idx}" if lang == 'en' else f"Análisis: Cluster {display_idx}"
                body_text = section_text

            df_cls = df_long_c[df_long_c['cluster'] == str(i)]
            
            # --- Analytics Plot Filter Logic ---
            y_val_col = 'real_salary'
            y_axis_title = "Salario Real" if lang == 'es' else "Real Salary"
            
            if is_base100:
                # Calculate index relative to 2016-12 for this cluster
                base_vals = df_cls[df_cls['date'] == START_LIMIT].set_index('province')['real_salary']
                df_cls = df_cls.copy()
                df_cls['index_val'] = df_cls.apply(lambda row: (row['real_salary'] / base_vals.get(row['province'], 1)) * 100, axis=1)
                y_val_col = 'index_val'
                y_axis_title = t['xaxis_index']
            elif not show_real:
                # Nominal: we need to join back with nominal data
                df_nom_long = df_nom_filt.reset_index().melt(id_vars='date', var_name='province', value_name='nom_salary')
                df_cls = df_cls.merge(df_nom_long, on=['date', 'province'])
                y_val_col = 'nom_salary'
                y_axis_title = t['xaxis_salary']

            fig_cls_small = px.line(df_cls, x='date', y=y_val_col, color='province',
                                   title=f"{card_title} - {t['tab_analytics']}", template='plotly_white', height=400)
            
            fig_cls_small.update_layout(
                legend_title_text=None,
                margin=dict(l=40, r=20, t=40, b=40),
                xaxis_title=t['date_range'].replace(':', ''),
                yaxis_title=y_axis_title
            )
            
            all_slides.append(html.Div([
                dbc.Card([
                    dbc.CardHeader(card_title, className="fw-bold bg-light"),
                    dbc.CardBody(dcc.Markdown(body_text, dangerously_allow_html=True, className="markdown-report"))
                ], className="mb-3 shadow-sm"),
                dbc.Card([
                    dbc.CardBody(dcc.Graph(figure=fig_cls_small, config={'displayModeBar': False}))
                ], className="mb-4 shadow-sm")
            ]))
        
        # Final Slide: Synthesis
        if lang_report["synthesis"]:
            s_text = lang_report["synthesis"]
            s_title_match = re.search(r'## \*\*Synthesis and Future Outlook: (.*?)\*\*', s_text)
            if not s_title_match:
                # Try Spanish header
                s_title_match = re.search(r'## \*\*Síntesis y Perspectivas Futuras: (.*?)\*\*', s_text)

            if s_title_match:
                s_card_title = f"{'Synthesis' if lang == 'en' else 'Síntesis'}: {s_title_match.group(1)}"
                s_body_text = re.sub(r'## \*\*(Synthesis and Future Outlook|Síntesis y Perspectivas Futuras):.*?\*\*', '', s_text).strip()
            else:
                s_card_title = "Synthesis & Future Outlook" if lang == 'en' else "Síntesis y Perspectivas Futuras"
                s_body_text = s_text

            all_slides.append(dbc.Card([
                dbc.CardHeader(s_card_title, className="fw-bold bg-dark text-white"),
                dbc.CardBody(dcc.Markdown(s_body_text, dangerously_allow_html=True, className="markdown-report"))
            ], className="mb-4 shadow-sm"))
    else:
        all_slides = [html.P(t['no_analytics'], className="text-center mt-5")]

    # Select the current slide based on index
    active_idx = min(max(0, carousel_idx), len(all_slides) - 1)
    report_content = all_slides[active_idx]
    progress_label = f"{active_idx + 1} / {len(all_slides)}"

    return kpi_latest, kpi_q, kpi_a, kpi_i, fig_hist, fig_comp, comp_header, trend_title, report_content, progress_label

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
