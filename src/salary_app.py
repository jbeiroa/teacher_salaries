from dash import Dash, html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
from salary_data.scraper import Scraper
from datetime import datetime

# Initialize the scraper
scraper = Scraper()

# --- Fetch Data ---
# Teacher Salaries (Net, Gross, Basic, Remunerative Share)
df_net_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO)
df_gross_salary = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_BRUTO)
df_basic_salary = scraper.get_cgecse_salaries(scraper.URL_BASICO)
df_remunerative_share = scraper.get_cgecse_salaries(scraper.URL_REMUNERATIVOS)

# IPC data (inflation)
df_ipc = scraper.get_ipc_indec()
ipc_national = df_ipc['Nivel_general']

# CBA/CBT data (poverty lines) - Temporarily disabled due to HTTP Error 403
# df_cba_cbt = scraper.get_cba_cbt()
df_cba_cbt = pd.DataFrame({'cbt': []}) # Provide an empty DataFrame to avoid errors

# --- Data Preparation ---
# Calculate Real Salaries (using national IPC for simplicity across provinces)
df_net_salary_real = scraper.calculate_real_salary(df_net_salary, ipc_national)
df_gross_salary_real = scraper.calculate_real_salary(df_gross_salary, ipc_national)
df_basic_salary_real = scraper.calculate_real_salary(df_basic_salary, ipc_national)

# --- App Initialization ---
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

# --- Layout ---
app.layout = html.Div([
    html.H1("Teacher Salaries Dashboard - Argentina", style={'textAlign': 'center'}),

    # Controls Row
    html.Div([
        html.Div([
            html.Label("Select Province:"),
            dcc.Dropdown(
                id='province-dropdown',
                options=[{'label': col, 'value': col} for col in df_net_salary.columns],
                value='Chaco',  # Default value
                clearable=False
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Select Salary Type:"),
            dcc.RadioItems(
                id='salary-type-radio',
                options=[
                    {'label': 'Net Salary', 'value': 'net'},
                    {'label': 'Gross Salary', 'value': 'gross'},
                    {'label': 'Basic Salary', 'value': 'basic'},
                ],
                value='net',  # Default value
                inline=True,
                style={'margin-top': '10px'}
            )
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Select Date Range:"),
            dcc.RangeSlider(
                id='date-range-slider',
                min=0,
                max=len(df_net_salary.index) - 1,
                value=[0, len(df_net_salary.index) - 1],
                marks={i: {'label': str(df_net_salary.index[i].year)} for i in range(0, len(df_net_salary.index), 4)}, # Mark every 4th quarter
                step=1
            )
        ], style={'width': '35%', 'display': 'inline-block', 'padding': '10px'})
    ], className='row'),

    # KPIs Row
    html.Div(className='row', children=[
        html.Div(id='kpi-output', className='twelve columns', style={'textAlign': 'center', 'margin-top': '20px'}),
    ]),

    # Charts Row
    html.Div(className='row', children=[
        html.Div(className='six columns', children=[
            dcc.Graph(id='historical-trend-chart', style={'height': '500px'})
        ]),
        html.Div(className='six columns', children=[
            dcc.Graph(id='provincial-comparison-chart', style={'height': '500px'})
        ])
    ])
])

# --- Callbacks ---
@app.callback(
    Output('kpi-output', 'children'),
    Output('historical-trend-chart', 'figure'),
    Output('provincial-comparison-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('salary-type-radio', 'value'),
    Input('date-range-slider', 'value')
)
def update_dashboard(selected_province, selected_salary_type, date_range_indices):
    """
    Updates the dashboard elements (KPIs, historical trend chart, provincial comparison chart)
    based on user selections.
    """
    # Access the global dataframes
    global df_net_salary, df_gross_salary, df_basic_salary, \
           ipc_national, df_cba_cbt, \
           df_net_salary_real, df_gross_salary_real, df_basic_salary_real

    start_date_idx, end_date_idx = date_range_indices
    start_date = df_net_salary.index[start_date_idx]
    end_date = df_net_salary.index[end_date_idx]

    # Select appropriate DataFrame based on salary type
    if selected_salary_type == 'net':
        df_selected_salary = df_net_salary
        df_selected_salary_real = df_net_salary_real
    elif selected_salary_type == 'gross':
        df_selected_salary = df_gross_salary
        df_selected_salary_real = df_gross_salary_real
    else: # basic
        df_selected_salary = df_basic_salary
        df_selected_salary_real = df_basic_salary_real

    # Filter data by date range
    filtered_df = df_selected_salary.loc[start_date:end_date]
    filtered_df_real = df_selected_salary_real.loc[start_date:end_date]
    filtered_ipc = ipc_national.loc[start_date:end_date]
    filtered_cbt = df_cba_cbt['cbt'].loc[start_date:end_date] if not df_cba_cbt.empty else pd.Series()

    # --- KPI Calculation ---
    latest_salary = filtered_df[selected_province].iloc[-1] if not filtered_df.empty else 0
    latest_ipc = filtered_ipc.iloc[-1] if not filtered_ipc.empty else 0
    # latest_cbt = filtered_cbt.iloc[-1] if not filtered_cbt.empty else 0
    latest_cbt = 0 # Set to 0 since CBT data is disabled

    # Calculate variations for KPIs (using latest year for interannual)
    salary_variations = scraper.calculate_variations(df_selected_salary[selected_province])
    ipc_variations = scraper.calculate_variations(ipc_national)
    # cbt_variations = scraper.calculate_variations(df_cba_cbt['cbt']) if not df_cba_cbt.empty else None

    kpi_elements = [
        html.Div(f"Latest {selected_salary_type.capitalize()} for {selected_province}: ${latest_salary:,.2f}", style={'margin': '5px'}),
        html.Div(f"Latest National IPC: {latest_ipc:,.2f}", style={'margin': '5px'}),
        # html.Div(f"Latest CBT: ${latest_cbt:,.2f}", style={'margin': '5px'}), # Temporarily disabled
    ]
    if not salary_variations.empty and 'interannual' in salary_variations.columns:
        kpi_elements.append(html.Div(f"Inter-annual Salary Variation: {salary_variations['interannual'].iloc[-1]:.2f}%", style={'margin': '5px'}))
    if not ipc_variations.empty and 'interannual' in ipc_variations.columns:
        kpi_elements.append(html.Div(f"Inter-annual IPC Variation: {ipc_variations['interannual'].iloc[-1]:.2f}%", style={'margin': '5px'}))
    # if cbt_variations is not None and not cbt_variations.empty and 'interannual' in cbt_variations.columns: # Temporarily disabled
    #     kpi_elements.append(html.Div(f"Inter-annual CBT Variation: {cbt_variations['interannual'].iloc[-1]:.2f}%", style={'margin': '5px'}))
    
    # --- Historical Trend Chart ---
    historical_fig = px.line(
        x=filtered_df.index,
        y=filtered_df[selected_province],
        title=f'{selected_province} {selected_salary_type.capitalize()} Trend (Nominal vs. Real)',
        labels={'value': 'Amount ($)', 'date': 'Date'}
    )
    historical_fig.data[0].name = f'{selected_salary_type.capitalize()} (Nominal)' # Explicitly set name

    # Add real salary to historical trend
    historical_fig.add_scatter(
        x=filtered_df_real.index,
        y=filtered_df_real[selected_province],
        mode='lines',
        name=f'{selected_salary_type.capitalize()} (Real)'
    )
    # Add CBT to historical trend
    # if not filtered_cbt.empty:
    #     historical_fig.add_scatter(
    #         x=filtered_cbt.index,
    #         y=filtered_cbt,
    #         mode='lines',
    #         name='Canasta Básica Total (CBT)'
    #     )

    # --- Provincial Comparison Chart (Latest Date) ---
    latest_date_data = df_selected_salary.loc[end_date]
    provincial_fig = px.bar(
        latest_date_data,
        x=latest_date_data.index,
        y=latest_date_data.values,
        title=f'{selected_salary_type.capitalize()} Comparison by Province ({end_date.strftime("%Y-%m")})',
        labels={'index': 'Province', 'y': 'Amount ($)'}
    )
    
    return html.Div(kpi_elements), historical_fig, provincial_fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
