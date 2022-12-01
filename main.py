# ===============================================================================
# Copyright 2022 ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================
import datetime
import json
import dash_bootstrap_components as dbc
import datetime as datetime
import requests as requests
from numpy import polyfit, linspace, polyval

from dash import Dash, html, dcc, Output, Input
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dash_table import DataTable

dash_app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                title='PVACD Groundwater Dashboard')

app = dash_app.server

crosswalk = pd.read_csv(
    'https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv')
# active_wells = pd.read_csv(
#     'https://raw.githubusercontent.com/NMWDI/HydroViewer/master/static/active_monitoring_wells.csv')
ST2 = 'https://st2.newmexicowaterdata.org/FROST-Server/v1.1'


def get_observations(location_iotid):
    url = f'{ST2}/Locations({location_iotid})?$expand=Things/Datastreams'
    resp = requests.get(url)
    if resp.status_code == 200:
        location = resp.json()
        ds = location['Things'][0]['Datastreams'][0]
        resp = requests.get(f"{ST2}/Datastreams({ds['@iot.id']})/Observations?$orderby=phenomenonTime desc&$top=500")

        if resp.status_code == 200:
            obs = resp.json()['value']
            return location, obs


layout = go.Layout(mapbox_style='open-street-map',
                   mapbox={'zoom': 6,
                           'center': {"lat": 33.25, 'lon': -106.4}},
                   margin={"r": 0, "t": 30, "l": 0, "b": 20},
                   height=400,
                   paper_bgcolor='#eeffcd'
                   )

tablecomp = DataTable(id='selected_table',
                      style_cell={'textAlign': 'left'},
                      columns=[{'name': 'Name', 'id': 'name'},
                               {"name": 'Value', 'id': 'value'}],
                      style_table={'height': '300px', 'overflowY': 'auto'},
                      )

hydrocomp = dcc.Graph(id='hydrograph')

data = []
trends = {}
col2 = []
for i, row in crosswalk.iterrows():
    iotid = row['PVACD']
    print(iotid, row)
    location, obs = get_observations(location_iotid=iotid)
    scatter = px.scatter(obs, x='phenomenonTime', y='result',
                         height=200)

    x = [datetime.datetime.strptime(o['phenomenonTime'], '%Y-%m-%dT%H:%M:%S.000Z').timestamp() for o in obs]
    y = [o['result'] for o in obs]

    coeffs = polyfit(x, y, 1)
    xs = linspace(x[0], x[-1])
    ys = polyval(coeffs, xs)
    trends[iotid] = coeffs[0]
    # fitline = [{'x':xi, 'y':yi} for xi, yi in zip(xs, ys)]
    # regline = px.line(fitline, x='x', y='y')
    scatter.add_scatter(x=[datetime.datetime.fromtimestamp(xi) for xi in xs],
                        y=ys, mode='lines')

    scatter.update_layout(margin=dict(t=25, b=10, l=10, r=0),
                          title=location['name'],
                          showlegend=False,
                          xaxis_title='Time',
                          yaxis_autorange="reversed",
                          yaxis_title='Depth To Water (bgs ft)')

    comp = dcc.Graph(
        id=f'hydrograph{i}',
        figure=scatter)

    col2.append(comp)

for a, tag in (('PVACD', 'pvacd_hydrovu'),):
    locations = pd.read_json(
        f'https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/{tag}.json')
    locations = locations['locations']

    lats = [l['location']['coordinates'][1] for l in locations]
    lons = [l['location']['coordinates'][0] for l in locations]
    ids = [l['name'] for l in locations]
    colors = ['red' if trends[l['@iot.id']] > 0 else 'green' for l in locations]

    data.append(go.Scattermapbox(lat=lats, lon=lons,
                                 text=ids,
                                 name=a,
                                 marker=go.scattermapbox.Marker(
                                     color=colors,
                                     size=10
                                 )))

figmap = go.Figure(layout=layout, data=data)
mapcomp = dcc.Graph(
    id='map',
    figure=figmap)
col2.insert(0, mapcomp)

dash_app.layout = dbc.Container([dbc.Row(html.H1('PVACD Monitoring Locations')),
                                 dbc.Row([dbc.Col([tablecomp, hydrocomp], width=5),
                                          dbc.Col(col2)])],
                                style={'background-color': '#eeffcd'}
                                )


# @dash_app.callback(
#     Output(component_id='map', component_property='figure'),
#     Input(component_id='slider', component_property='value')
# )
# def update_output_div(input_value):
#     fig.layout.mapbox.pitch = input_value
#
#     return fig


@dash_app.callback(
    Output("selected_table", "data"),
    Output("hydrograph", "figure"),
    Input('map', 'clickData')
)
def display_click_data(clickData):
    data = [{"name": 'Location', "value": ''},
            {"name": 'Latitude', "value": ''},
            {"name": 'Longitude', "value": ''},
            {"name": 'ST ID', "value": ''},
            {"name": 'aST ID', "value": ''},
            {"name": 'PointID', "value": ''},
            {"name": 'Elevation (ft)', "value": ''},
            {"name": 'Well Depth (ft)', "value": ''},
            ]
    obs = [{'phenomenonTime': 0, 'result': 0}]

    if clickData:
        point = clickData['points'][0]
        name = point['text']
        url = f"{ST2}/Locations?$filter=name eq '{name}'&$expand=Things/Datastreams"
        resp = requests.get(url)
        data = [{"name": "Location", "value": name},
                {'name': "Latitude", "value": point['lat']},
                {'name': "Longitude", "value": point['lon']}, ]

        if resp.status_code == 200:
            try:
                location = resp.json()['value'][0]
                iotid = location['@iot.id']
                data.append({"name": 'ST ID', "value": iotid})
                # data.append({"name": 'Elevation (ft)',
                #              "value": f"{location['properties']['Altitude']:0.2f}"})
            except IndexError:
                pass
            # get the data from NM_Aquifer (via ST2 for these wells)
            aiotid = crosswalk[crosswalk['PVACD'] == iotid].iloc[0]['NM_AQUIFER']

            data.append({"name": 'aST ID', "value": aiotid})
            resp = requests.get(f'{ST2}/Locations({aiotid})?$expand=Things')
            if resp.status_code == 200:
                alocation = resp.json()
                thing = alocation['Things'][0]
                data.append({'name': 'PointID', 'value': alocation['name']})
                data.append({'name': 'Elevation (ft)', 'value': alocation['properties']['Altitude']})
                data.append({'name': 'Well Depth', 'value': thing['properties'].get('WellDepth')})

            ds = location['Things'][0]['Datastreams'][0]
            resp = requests.get(f"{ST2}/Datastreams({ds['@iot.id']})/Observations?$orderby=phenomenonTime desc")

            if resp.status_code == 200:
                obs = resp.json()['value']

    line = px.line(obs, x='phenomenonTime', y='result',
                   height=500)
    line.update_layout(margin=dict(t=20, b=10, l=10, r=0),
                       xaxis_title='Time',
                       yaxis_autorange="reversed",
                       yaxis_title='Depth To Water Below Ground Surface (ft)')
    return data, line


if __name__ == '__main__':
    dash_app.run_server(debug=True)
# ============= EOF =============================================
