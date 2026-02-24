import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, callback, Output, Input, State
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
ipc_national = df_ipc['infl_Nivel_general']

df_cba_cbt = scraper.get_cba_cbt().loc[START_LIMIT:]
if not df_cba_cbt.empty:
    df_cba_cbt.rename(columns={
        'canasta_basica_total': 'cbt',
        'canasta_basica_alimentaria': 'cba'
    }, inplace=True)

# Calculate Real Salaries
df_net_salary_real = scraper.calculate_real_salary(df_net_salary, ipc_national)
df_gross_salary_real = scraper.calculate_real_salary(df_gross_salary, ipc_national)
df_basic_salary_real = scraper.calculate_real_salary(df_basic_salary, ipc_national)

# --- Helper Functions ---
def create_kpi_card(title, nominal_value, real_variation=None):
    """Creates a Bootstrap card showing nominal value and real variation subtext."""
    color = "text-dark"
    var_text = ""
    if real_variation is not None:
        color = "text-success" if real_variation >= 0 else "text-danger"
        var_text = f"Real Var: {real_variation:+.1f}%"

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
    dbc.Row([
        dbc.Col(html.H1("Teacher Salaries Dashboard - Argentina", className="text-center my-4"), width=12)
    ]),

    dbc.Row([
        # Sidebar/Controls
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filters", className="fw-bold"),
                dbc.CardBody([
                    html.Label("Province:", className="mt-2"),
                    dcc.Dropdown(
                        id='province-dropdown',
                        options=[{'label': col, 'value': col} for col in df_net_salary.columns],
                        value='Chaco',
                        clearable=False,
                        className="mb-3"
                    ),
                    html.Label("Salary Type:"),
                    dcc.RadioItems(
                        id='salary-type-radio',
                        options=[
                            {'label': ' Net', 'value': 'net'},
                            {'label': ' Gross', 'value': 'gross'},
                            {'label': ' Basic', 'value': 'basic'},
                        ],
                        value='net',
                        inline=True,
                        className="mb-3",
                        inputStyle={"margin-right": "5px", "margin-left": "15px"}
                    ),
                    html.Label("Adjustment:"),
                    dbc.Checklist(
                        id='adjustment-toggle',
                        options=[
                            {'label': ' Show Nominal', 'value': 'nominal'},
                            {'label': ' Show Real (Adjusted)', 'value': 'real'},
                            {'label': ' Show Poverty Line (CBT)', 'value': 'cbt'},
                        ],
                        value=['nominal', 'real'],
                        switch=True,
                        className="mb-3"
                    ),
                    html.Label("Historical Date Range:"),
                    dcc.DatePickerRange(
                        id='date-picker-range',
                        min_date_allowed=df_net_salary.index[0],
                        max_date_allowed=df_net_salary.index[-1],
                        start_date=df_net_salary.index[-13], # ~3 years
                        end_date=df_net_salary.index[-1],
                        display_format='YYYY-MM',
                        className="mb-3"
                    ),
                    html.Label("Comparison Month:", className="mt-4"),
                    dcc.Dropdown(
                        id='comparison-month-dropdown',
                        options=[{'label': d.strftime("%Y-%m"), 'value': i} for i, d in enumerate(df_net_salary.index)],
                        value=len(df_net_salary.index) - 1,
                        clearable=False
                    )
                ])
            ], className="shadow-sm")
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
                        dbc.CardHeader("Historical Trend", className="fw-bold"),
                        dbc.CardBody(dcc.Graph(id='historical-trend-chart', config={'displayModeBar': False}))
                    ], className="shadow-sm mb-4")
                ], width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Provincial Comparison", id="comparison-header", className="fw-bold"),
                        dbc.CardBody(dcc.Graph(id='provincial-comparison-chart', config={'displayModeBar': False}, style={'height': '600px'}))
                    ], className="shadow-sm mb-4")
                ], width=12),
            ])
        ], width=12, lg=9)
    ])
], fluid=True)

# --- Callbacks ---
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
    Input('date-picker-range', 'start_date'),
    Input('date-picker-range', 'end_date'),
    Input('comparison-month-dropdown', 'value')
)
def update_dashboard(selected_province, salary_type, adjustments, start_date, end_date, comp_month_idx):
    # Data selection
    if salary_type == 'net':
        df_nom, df_real = df_net_salary, df_net_salary_real
    elif salary_type == 'gross':
        df_nom, df_real = df_gross_salary, df_gross_salary_real
    else:
        df_nom, df_real = df_basic_salary, df_basic_salary_real

    # Date filtering
    mask = (df_nom.index >= start_date) & (df_nom.index <= end_date)
    df_nom_filt = df_nom.loc[mask]
    df_real_filt = df_real.loc[mask]
    
    # Variations calculation based on full series for accuracy
    metrics = get_variation_metrics(df_nom[selected_province], df_real[selected_province])
    
    # KPI components
    kpi_latest = create_kpi_card(f"Latest {salary_type.title()}", f"${metrics['latest_nom']:,.0f}")
    kpi_q = create_kpi_card("Quarterly Var.", f"{metrics['q_nom']:+.1f}%", metrics['q_real'])
    kpi_a = create_kpi_card("Annual Acc.", f"{metrics['a_nom']:+.1f}%", metrics['a_real'])
    kpi_i = create_kpi_card("Inter-annual Var.", f"{metrics['i_nom']:+.1f}%", metrics['i_real'])

    # Historical Trend Chart
    fig_hist = go.Figure()
    
    if 'nominal' in adjustments:
        fig_hist.add_trace(go.Scatter(
            x=df_nom_filt.index, y=df_nom_filt[selected_province],
            name="Nominal", line=dict(color='#2c3e50', width=3)
        ))
    
    if 'real' in adjustments:
        fig_hist.add_trace(go.Scatter(
            x=df_real_filt.index, y=df_real_filt[selected_province],
            name="Real (Adj.)", line=dict(color='#18bc9c', width=3)
        ))
        
    if 'cbt' in adjustments and not df_cba_cbt.empty:
        cbt_filtered = df_cba_cbt['cbt'].reindex(df_nom.index, method='ffill').loc[start_date:end_date]
        fig_hist.add_trace(go.Scatter(
            x=cbt_filtered.index, y=cbt_filtered,
            name="Poverty Line (CBT)", line=dict(color='#e74c3c', dash='dash')
        ))

    fig_hist.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        template="plotly_white"
    )

    # Provincial Comparison Chart
    comp_date = df_nom.index[comp_month_idx]
    comp_data = df_nom.loc[comp_date].sort_values(ascending=True) # Ascending for horizontal bar sorted top-down
    
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
        margin=dict(l=150, r=50, t=20, b=20), # More margin for province names
        template="plotly_white",
        xaxis_title="Salary Amount ($)",
        bargap=0.15,
        yaxis=dict(tickfont=dict(size=11))
    )

    comp_header = f"Provincial Comparison ({comp_date.strftime('%Y-%m')})"

    return kpi_latest, kpi_q, kpi_a, kpi_i, fig_hist, fig_comp, comp_header

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
