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
import dash_bootstrap_components as dbc

import dash
import pandas as pd
import requests
from dash import html, dcc, callback, Input, Output, State
import plotly.graph_objects as go
from dash.dash_table import DataTable

from styles import chart_bgcolor, header_style, data_style

dash.register_page(__name__)

air_temp_graph = dcc.Graph(id="air_temp_graph")
rel_hum_graph = dcc.Graph(id="rel_hum_graph")
windspeed_graph = dcc.Graph(id="windspeed_graph")
solar_radiation_graph = dcc.Graph(id="solar_radiation_graph")
precipitation_graph = dcc.Graph(id="precipitation_graph")
atmos_pressure_graph = dcc.Graph(id="atmos_pressure_graph")

SERIAL = {
    "Poe Corn": "A4100127",
    "Shop": "A4100062",
    "Orchard Park": "A4100132",
    "Cottonwood": "A4100114",
    "Artesia": "A4100130",
}

layout = go.Layout(
    mapbox_style="open-street-map",
    # mapbox_layers=[USGS_BM],
    mapbox={"zoom": 6, "center": {"lat": 33.25, "lon": -104.5}},
    margin={"r": 10, "t": 30, "l": 10, "b": 20},
    height=450,
    paper_bgcolor=chart_bgcolor,
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.66,
        bgcolor="#899DBE",
        borderwidth=3,
    ),
)

locations = pd.read_json(f"./data/weather_stations.json")
locations = locations["locations"]

lats = [f'{l["location"]["coordinates"][1]:0.3f}' for l in locations]
lons = [f'{l["location"]["coordinates"][0]:0.3f}' for l in locations]
ids = [l["name"] for l in locations]

data = [
    go.Scattermapbox(
        lat=lats, lon=lons, text=ids, marker=go.scattermapbox.Marker(size=14)
    )
]

mapcomp = dcc.Graph(id="map", figure=go.Figure(layout=layout, data=data))

header_style["fontSize"] = "16px"

data_style["fontSize"] = "12px"

current_table = DataTable(
    id="current_table",
    columns=[{"name": "Name", "id": "name"}, {"name": "Value", "id": "value"}],
    # columns=[{"name": i, "id": i.lower().replace(' ', '_')}
    #          for i in ["Station", "Relative Humidity"]]
    style_header=header_style,
    style_as_list_view=True,
    style_data=data_style,
)

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
        dbc.Row(
            children=[
                dbc.Col(mapcomp),
                dbc.Col(
                    children=[
                        html.H2("Current Conditions"),
                        dbc.Spinner([html.Div(id="loading-weather"), current_table]),
                    ]
                ),
            ]
        ),
        # html.Div(current_table),
        html.Br(),
        html.P("If graphs do not display please wait 1 minute before refreshing."),
        html.H2(id="station-name", style={"text-align": "center"}),
        html.H2("Air Temperature"),
        air_temp_graph,
        html.H2("Relative Humidity"),
        rel_hum_graph,
        html.H2("Wind Speed"),
        windspeed_graph,
        html.H2("Solar Radiation"),
        solar_radiation_graph,
        html.H2("Precipitation"),
        precipitation_graph,
        html.H2("Atmospheric Pressure"),
        atmos_pressure_graph
        # html.Div(id='analytics-output'),
    ]
)


@callback(
    [
        Output("air_temp_graph", "figure"),
        Output("rel_hum_graph", "figure"),
        Output("solar_radiation_graph", "figure"),
        Output("precipitation_graph", "figure"),
        Output("atmos_pressure_graph", "figure"),
        Output("windspeed_graph", "figure"),
        Output("station-name", "children"),
        Output("current_table", "data"),
        Output("loading-weather", "children"),
        # Output("progress-div", "children")
    ],
    [
        Input(component_id="station-input", component_property="value"),
        State("air_temp_graph", "figure"),
        State("rel_hum_graph", "figure"),
        State("windspeed_graph", "figure"),
        State("solar_radiation_graph", "figure"),
        State("precipitation_graph", "figure"),
        State("atmos_pressure_graph", "figure"),
    ]
    # Input("map", "clickData"),
)
def display_graphs(
    station_name, air_temp, rel_hum, windspeed, solar_rad, precip, atmos_pressure
):
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

    current_values = [
        {"name": "Station", "value": station_name},
    ]
    try:
        data = resp["data"]
        # pprint(data)

        fs = []
        for name in ["Air Temperature", "Min Air Temperature", "Max Air Temperature"]:
            xs, ys = extract_xy(data[name][0]["readings"])
            current_values.append({"name": name, "value": f"{ys[0]:0.1f} F"})
            fs.append(go.Scatter(x=xs, y=ys, name=name, mode="markers+lines"))

        fig = go.Figure(data=fs, layout=layout)
        fig.layout.yaxis.title = "Air Temperature (F)"
        figs = [fig]

        for sname, ytitle, units in [
            ("Relative Humidity", "Relative Humidity", "%"),
            ("Solar Radiation", "Solar Radiation", "W/m2"),
            ("Precipitation", "Precipitation", "in"),
            ("Atmospheric Pressure", "Atmospheric Pressure", "kPa"),
        ]:
            xs, ys = extract_xy(data[sname][0]["readings"])
            current_values.append({"name": sname, "value": f"{ys[0]:0.1f} {units}"})
            fig = go.Figure(
                data=[go.Scatter(x=xs, y=ys, mode="markers+lines")], layout=layout
            )
            fig.layout.yaxis.title = f"{ytitle} ({units})"
            figs.append(fig)

        xs, ys = extract_xy(data["Wind Speed"][0]["readings"])
        gxs, gys = extract_xy(data["Gust Speed"][0]["readings"])

        current_values.append({"name": "Wind Speed", "value": f"{ys[0]:0.1f} mph"})
        current_values.append({"name": "Gust Speed", "value": f"{gys[0]:0.1f} mph"})
        current_values.append(
            {
                "name": "Battery Percent",
                "value": f'{data["Battery Percent"][0]["readings"][0]["value"]:0.1f} %',
            }
        )
        current_values.append(
            {
                "name": "Battery Voltage",
                "value": f'{data["Battery Voltage"][0]["readings"][0]["value"]/1000:0.1f} V',
            }
        )

        fig = go.Figure(
            data=[
                go.Scatter(x=xs, y=ys, name="Wind Speed", mode="markers+lines"),
                go.Scatter(x=gxs, y=gys, name="Gust Speed", mode="markers"),
            ],
            layout=layout,
        )
        fig.layout.yaxis.title = "Wind Speed (mph)"
        figs.append(fig)

    except KeyError as e:
        print(e, resp)
        figs = [air_temp, rel_hum, solar_rad, precip, atmos_pressure, windspeed]

    return figs + [station_name, current_values, ""]


def get_sensor_data(device_sn):
    token = os.environ.get("ZENTRA_TOKEN", "")

    # device_sn = "your_ZENTRAcloud_device_serial_number"
    url = "https://zentracloud.com/api/v3/get_readings/"
    token = "Token {TOKEN}".format(TOKEN=token)
    headers = {"content-type": "application/json", "Authorization": token}
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=14)
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
