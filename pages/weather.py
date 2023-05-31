# ===============================================================================
# Copyright 2023 Jake Ross
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
import os
from pprint import pprint

import dash
import requests
from dash import html, dcc, callback, Input, Output, State
import plotly.graph_objects as go

dash.register_page(__name__)

air_temp_graph = dcc.Graph(id="air_temp_graph")
rel_hum_graph = dcc.Graph(id="rel_hum_graph")

SERIAL = {
    "Poe Corn": "A4100127",
    "Shop": "A4100062",
    "Orchard Park": "A4100132",
    "Cottonwood": "A4100114",
    "Artesia": "A4100130",
}

layout = html.Div(
    children=[
        # html.H1(children='This is our Analytics page'),
        html.Div(
            [
                "Select a station: ",
                dcc.Dropdown(
                    ["Poe Corn", "Shop", "Orchard Park", "Cottonwood", "Artesia"],
                    "Poe Corn",
                    id="station-input",
                ),
            ]
        ),
        html.Br(),
        html.H2("Air Temperature"),
        air_temp_graph,
        html.H2("Relative Humidity"),
        rel_hum_graph
        # html.Div(id='analytics-output'),
    ]
)


@callback(
    [
        # Output("loading-output", "children"),
        # Output("selected_table", "data"),
        Output("air_temp_graph", "figure"),
        Output("rel_hum_graph", "figure"),
        # Output("progress-div", "children")
    ],
    [
        Input(component_id="station-input", component_property="value"),
        State("air_temp_graph", "figure"),
        State("rel_hum_graph", "figure"),
    ]
    # Input("map", "clickData"),
)
def display_graphs(station_name, air_temp, rel_hum):
    layout = dict(
        height=350,
        margin=dict(t=50, b=50, l=50, r=25),
        # xaxis=xaxis,
        # yaxis=yaxis,
        # title=location["name"] if location else "",
        # paper_bgcolor=chart_bgcolor,
    )
    # xs = [1, 2, 3]
    # ys = [1, 2, 3]

    resp = get_sensor_data(SERIAL[station_name])

    try:
        data = resp["data"]
        # pprint(data)

        fs = []
        for name in ["Air Temperature", "Min Air Temperature", "Max Air Temperature"]:
            xs, ys = extract_xy(data[name][0]["readings"])
            fs.append(go.Scatter(x=xs, y=ys, name=name, mode="markers+lines"))

        fig = go.Figure(data=fs, layout=layout)
        fig.layout.yaxis.title = "Air Temperature (F)"
        figs = [fig]

        for sname, ytitle in [
            ("Relative Humidity", "Relative Humidity (%)"),
        ]:
            xs, ys = extract_xy(data[sname][0]["readings"])
            fig = go.Figure(
                data=[go.Scatter(x=xs, y=ys, mode="markers+lines")], layout=layout
            )
            fig.layout.yaxis.title = ytitle
            figs.append(fig)

    except KeyError as e:
        print(e, resp)
        figs = air_temp, rel_hum

    return figs


def get_sensor_data(device_sn):
    token = os.environ.get("ZENTRA_TOKEN", "")

    # device_sn = "your_ZENTRAcloud_device_serial_number"
    url = "https://zentracloud.com/api/v3/get_readings/"
    token = "Token {TOKEN}".format(TOKEN=token)
    headers = {"content-type": "application/json", "Authorization": token}
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=30)
    page_num = 1
    per_page = 500
    params = {
        "device_sn": device_sn,
        "start_date": start_date,
        "end_date": end_date,
        "page_num": page_num,
        "per_page": per_page,
    }
    response = requests.get(url, params=params, headers=headers)
    # content = json.loads(response.content)
    js = response.json()
    # pprint(js)
    return js
    # stream = data['Air Temperature'][0]
    # return extract_xy(stream['readings'])


def extract_xy(readings):
    xs, ys = [], []
    for ri in readings:
        xs.append(ri["datetime"])
        ys.append(ri["value"])
    return xs, ys


# @callback(
# Output(component_id='analytics-output', component_property='children'),
# Input(component_id='analytics-input', component_property='value')
# )
# def update_city_selected(input_value):
#     return f'You selected: {input_value}'


# ============= EOF =============================================
