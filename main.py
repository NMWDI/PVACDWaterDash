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

dash_app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PVACD Groundwater Dashboard",
)
# dash_app.css.append_css({"external_url": "assets/css/style.css"})

app = dash_app.server

crosswalk = pd.read_csv(
    "https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv"
)
# active_wells = pd.read_csv(
#     'https://raw.githubusercontent.com/NMWDI/HydroViewer/master/static/active_monitoring_wells.csv')
ST2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1"

DTFORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
DEPTH_TO_WATER_FT_BGS = "Depth To Water (ft bgs)"
DEBUG_OBS = False

xaxis = dict(
    title="Time",
    rangeselector=dict(
        buttons=list(
            [
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all"),
            ]
        )
    ),
    rangeslider=dict(visible=True),
    type="date",
)

chart_bgcolor = '#b5aeae'
card_style = {'border': 'solid', 'borderRadius': '10px',
              'marginBlock': '5px',
              "backgroundColor": chart_bgcolor,
              "boxShadow": "2px 2px #8d9ea2",
              "borderColor": "7d777a"
              }

lcol_style = card_style.copy()
rcol_style = card_style.copy()
header_style = card_style.copy()

lcol_style['marginRight'] = '5px'
rcol_style['marginLeft'] = '5px'
header_style['height'] = '90px'


def get_observations(location_iotid, limit=1000):
    url = f"{ST2}/Locations({location_iotid})?$expand=Things/Datastreams"
    resp = requests.get(url)
    if resp.status_code == 200:
        location = resp.json()
        ds = location["Things"][0]["Datastreams"][0]
        if DEBUG_OBS:
            obs = [
                {
                    "phenomenonTime": datetime.datetime.now().strftime(DTFORMAT),
                    "result": 0,
                }
            ]
            return location, obs
        else:
            resp = requests.get(
                f"{ST2}/Datastreams({ds['@iot.id']})/Observations?$orderby=phenomenonTime desc&$top={limit}"
            )

            if resp.status_code == 200:
                obs = resp.json()["value"]
                return location, obs


BGCOLOR = "#d3d3d3"


def init_app():
    layout = go.Layout(
        mapbox_style="open-street-map",
        mapbox_layers=[
            {
                "below": "traces",
                "sourcetype": "raster",
                "sourceattribution": "United States Geological Survey",
                "source": [
                    "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
                ],
            }
        ],
        mapbox={"zoom": 6, "center": {"lat": 33.25, "lon": -104.5}},
        margin={"r": 10, "t": 30, "l": 10, "b": 20},
        height=400,
        paper_bgcolor=chart_bgcolor,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.735,
            bgcolor="#899DBE",
            borderwidth=3,
        ),
    )

    tablecomp = DataTable(
        id="selected_table",
        style_cell={"textAlign": "left"},
        columns=[{"name": "Name", "id": "name"}, {"name": "Value", "id": "value"}],
        style_as_list_view=True,
        style_data={"fontSize": "12px"},
        style_table={"height": "300px", "overflowY": "auto"},
    )
    summarytable = DataTable(
        id="summarytable",
        style_cell={"textAlign": "left"},
        columns=[
            {"name": "Location", "id": "location"},
            {"name": "Last Measurement", "id": "last_measurement"},
            {"name": "Last Time", "id": "last_time"},
            {"name": "Trend", "id": "trend"},
        ],
        # css=[
        #     {"selector": ".dash-spreadsheet tr th", "rule": "height: 15px;"},
        #     # set height of header
        #     {"selector": ".dash-spreadsheet tr td", "rule": "height: 12px;"},
        #     # set height of body rows
        # ],
        style_as_list_view=True,
        style_data={"fontSize": "12px"},
        style_data_conditional=[
            {
                "if": {
                    "column_id": "trend",
                    "filter_query": "{trendvalue} > 0",
                },
                "backgroundColor": "red",
                "color": "white",
            },
            {
                "if": {
                    "column_id": "trend",
                    "filter_query": "{trendvalue} < 0",
                },
                "backgroundColor": "green",
                "color": "white",
            },
        ],
        style_table={
            # "border": "solid",
            # "border-color": "red",
            # "border-radius": "15px",
            # "height": "300px",
            "padding_top": "10px",
            "overflowY": "auto",
        },
    )

    hydrocomp = dcc.Graph(id="hydrograph")

    sdata = []
    data = []
    trends = {}
    charts = []
    for i, row in crosswalk.iterrows():
        iotid = row["PVACD"]
        print(iotid, row)
        location, obs = get_observations(location_iotid=iotid)
        # nm_aquifer_location, manual_obs = get_observations(location_iotid=row['NM_AQUIFER'], limit=100)
        scatter = px.scatter(obs, x="phenomenonTime", y="result", height=350)
        # mxs = [xi['phenomenonTime'] for xi in manual_obs]
        # mys = [xi['result'] for xi in manual_obs]
        # scatter.add_scatter(x=mxs, y=mys)
        fobs = obs[:50]
        x = [
            datetime.datetime.strptime(o["phenomenonTime"], DTFORMAT).timestamp()
            for o in fobs
        ]
        y = [o["result"] for o in fobs]

        coeffs = polyfit(x, y, 1)
        xs = linspace(x[0], x[-1])
        ys = polyval(coeffs, xs)
        trends[iotid] = trend = coeffs[0]

        scatter.add_scatter(
            x=[datetime.datetime.fromtimestamp(xi) for xi in xs], y=ys, mode="lines"
        )

        scatter.update_layout(
            margin=dict(t=75, b=50, l=50, r=25),
            title=location["name"],
            showlegend=False,
            yaxis_autorange="reversed",
            yaxis_title=DEPTH_TO_WATER_FT_BGS,
            xaxis=xaxis,
            paper_bgcolor=chart_bgcolor,
        )

        comp = dcc.Graph(id=f"hydrograph{i}", style=card_style, figure=scatter)

        charts.append(comp)
        lt = obs[-1]["phenomenonTime"]
        lm = obs[-1]["result"]

        srow = {
            "location": location["name"],
            "trend": "increase" if trend > 0 else "decrease",
            "trendvalue": trend,
            "last_measurement": f"{lm:0.2f}",
            "last_time": datetime.datetime.strptime(lt, DTFORMAT).isoformat(),
        }
        sdata.append(srow)

    summarytable.data = sdata
    for a, tag, colors in (
        ("ISC Seven Rivers", "isc_seven_rivers", "blue"),
        ("OSE Roswell", 'ose_roswell', "orange"),
        ("PVACD Monitoring Wells", "pvacd_hydrovu", ""),
    ):
        locations = pd.read_json(
            f"https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/{tag}.json"
        )
        locations = locations["locations"]

        lats = [l["location"]["coordinates"][1] for l in locations]
        lons = [l["location"]["coordinates"][0] for l in locations]
        ids = [l["name"] for l in locations]
        size = 10
        if tag == "pvacd_hydrovu":
            colors = [
                "green" if trends.get(l["@iot.id"], 1) < 0 else "red" for l in locations
            ]
            size = 15

        data.append(
            go.Scattermapbox(
                lat=lats,
                lon=lons,
                text=ids,
                name=a,
                marker=go.scattermapbox.Marker(color=colors, size=size),
            )
        )

    figmap = go.Figure(layout=layout, data=data)
    mapcomp = dcc.Graph(id="map", figure=figmap)

    dash_app.layout = dbc.Container(
        [
            dbc.Row([html.Img(style={'height': '25%', 'width': '25%'},
                              src='assets/newmexicowaterdatalogo.png'),
                     # html.Img(style={'height': '10%', 'width': '10%'},
                     #          src='assets/img/newmexicobureauofgeologyandmineralresources.jpeg')
                     ],
                    style=card_style),
            dbc.Row(html.H1("PVACD Monitoring Locations"),
                    style=card_style),
            dbc.Row([dbc.Col(summarytable,
                             style=lcol_style),
                     dbc.Col(mapcomp,
                             style=rcol_style)]),
            dbc.Row([dbc.Col([html.H2('Selection'), tablecomp],
                             style=lcol_style),
                     dbc.Col([hydrocomp],
                             style=rcol_style)],
                    ),
            dbc.Row(children=charts,
                    # style=card_style
                    ),
            dbc.Row([html.Footer('Developed By Jake Ross (2022)')])
        ],
        style={"backgroundColor": BGCOLOR},
    )


@dash_app.callback(
    Output("selected_table", "data"),
    Output("hydrograph", "figure"),
    Input("map", "clickData"),
)
def display_click_data(clickData):
    data = [
        {"name": "Location", "value": ""},
        {"name": "Latitude", "value": ""},
        {"name": "Longitude", "value": ""},
        {"name": "ST ID", "value": ""},
        {"name": "aST ID", "value": ""},
        {"name": "PointID", "value": ""},
        {"name": "Elevation (ft)", "value": ""},
        {"name": "Well Depth (ft)", "value": ""},
    ]
    obs = [{"phenomenonTime": 0, "result": 0}]
    mxs = []
    mys = []
    if clickData:
        point = clickData["points"][0]
        name = point["text"]
        url = f"{ST2}/Locations?$filter=name eq '{name}'&$expand=Things/Datastreams"
        resp = requests.get(url)
        data = [
            {"name": "Location", "value": name},
            {"name": "Latitude", "value": point["lat"]},
            {"name": "Longitude", "value": point["lon"]},
        ]

        if resp.status_code == 200:
            try:
                location = resp.json()["value"][0]
                iotid = location["@iot.id"]
                data.append({"name": "ST ID", "value": iotid})
                # data.append({"name": 'Elevation (ft)',
                #              "value": f"{location['properties']['Altitude']:0.2f}"})
            except IndexError:
                pass
            ds = location["Things"][0]["Datastreams"][0]
            resp = requests.get(
                f"{ST2}/Datastreams({ds['@iot.id']})/Observations?$orderby=phenomenonTime desc"
            )

            if resp.status_code == 200:
                obs = resp.json()["value"]

            # get the data from NM_Aquifer (via ST2 for these wells)
            try:
                aiotid = crosswalk[crosswalk["PVACD"] == iotid].iloc[0]["NM_AQUIFER"]
            except BaseException:
                aiotid = None

            if aiotid:
                data.append({"name": "aST ID", "value": aiotid})
                resp = requests.get(f"{ST2}/Locations({aiotid})?$expand=Things")
                if resp.status_code == 200:
                    alocation = resp.json()
                    thing = alocation["Things"][0]
                    data.append({"name": "PointID", "value": alocation["name"]})
                    data.append(
                        {
                            "name": "Elevation (ft)",
                            "value": alocation["properties"]["Altitude"],
                        }
                    )
                    data.append(
                        {
                            "name": "Well Depth",
                            "value": thing["properties"].get("WellDepth"),
                        }
                    )

                nm_aquifer_location, manual_obs = get_observations(
                    location_iotid=aiotid, limit=100
                )
                mxs = [xi["phenomenonTime"] for xi in manual_obs]
                mys = [xi["result"] for xi in manual_obs]

    fig = go.Figure()
    xs = [xi["phenomenonTime"] for xi in obs]
    ys = [xi["result"] for xi in obs]
    fig.add_trace(go.Scatter(x=xs, y=ys, name="PVACD"))
    fig.add_trace(go.Scatter(x=mxs, y=mys, name="NMBGMR"))

    fig.update_layout(
        height=350,
        margin=dict(t=50, b=50, l=50, r=25),
        yaxis_autorange="reversed",
        yaxis_title=DEPTH_TO_WATER_FT_BGS,
        xaxis=xaxis,
        # yaxis={"rangeslider": dict(visible=True)},
        paper_bgcolor=chart_bgcolor,
    )
    return data, fig


init_app()

if __name__ == "__main__":
    dash_app.run_server(debug=True, port=8051)
# ============= EOF =============================================
