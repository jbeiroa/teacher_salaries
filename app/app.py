from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import requests as re
import plotly.express as px
from salary_data.scraper import Scraper

scraper = Scraper()
df = scraper.get_cgecse_salaries(scraper.URL_TESTIGO_NETO)

# Initialize the app - incorporate css
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server

# App layout
app.layout = html.Div([
    html.Div(className='row', children='Dashbord Salarios MG10 de bolsillo',
             style={'textAlign': 'center', 'color': 'blue', 'fontSize': 30}),

    html.Div(className='row', children=[
        dcc.Dropdown(options=df.columns,
                       value=df.columns[0],
                       multi=True,
                       id='dropdown-final')
    ]),

    html.Div(className='row', children=[
        html.Div(className='six columns', children=[
            dash_table.DataTable(data=df.to_dict('records'), page_size=11, style_table={'overflowX': 'auto'})
        ]),
        html.Div(className='six columns', children=[
            dcc.Graph(figure={}, id='line-chart-final')
        ])
    ])
])

# Add controls to build the interaction
@callback(
    Output(component_id='line-chart-final', component_property='figure'),
    Input(component_id='dropdown-final', component_property='value')
)
def update_graph(col_chosen):
    fig = px.line(df, x=df.index, y=col_chosen)
    return fig

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)