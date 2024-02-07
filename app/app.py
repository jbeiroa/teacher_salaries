from dash import Dash, html, dash_table, dcc, callback, Output, Input
import pandas as pd
import requests as re
import plotly.express as px


def get_cgecse_salaries():
    url = 'https://www.argentina.gob.ar/sites/default/files/2022/07/2._salario_de_bolsillo_mg10_1_act.xlsx'
    r = re.get(url)
    df = pd.read_excel(r.content, header=6)
    df.drop([df.columns[0]], axis=1, inplace=True)
    df.rename({df.columns[0]: 'jurisdiccion'}, axis=1, inplace=True)

    current = pd.to_datetime('2003-03-01')
    dates = [current]
    for col in df.columns:
        current = current + pd.DateOffset(months=3)
        dates.append(current)
    names = dict(zip(df.columns[1:], dates))
    df.rename(names, axis=1, inplace=True)
    df.dropna(inplace=True)
    df = df.T
    df.columns = df.iloc[0]
    df.drop(df.index[0], inplace=True)
    df.index.name = 'date'
    new_col_names = df.columns.str.replace(r' \(([1-9])\)|\(([1-9])\)', '', regex=True)
    col_names = dict(zip(df.columns, new_col_names))
    df.rename(col_names, axis=1, inplace=True)

    return df

# Incorporate data
df = get_cgecse_salaries()

# Initialize the app - incorporate css
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)

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
    app.run(host='0.0.0.0', debug=True)