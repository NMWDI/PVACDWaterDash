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
from asyncio import Event

import dash_bootstrap_components as dbc
import datetime as datetime
import requests as requests
from numpy import polyfit, linspace, polyval

from dash import Dash, html, dcc, Output, Input
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dash_table import DataTable

from util import (
    floatfmt,
    get_formation_name,
    get_observations,
    get_usgs,
    extract_usgs_timeseries,
)
from constants import DEPTH_TO_WATER_FT_BGS, DTFORMAT, ST2, TITLE

dash_app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PVACD Groundwater Dashboard",
)

app = dash_app.server

crosswalk = pd.read_csv(
    "https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv"
)
# crosswalk = crosswalk[1:4]
# active_wells = pd.read_csv(
#     'https://raw.githubusercontent.com/NMWDI/HydroViewer/master/static/active_monitoring_wells.csv')


yaxis = dict(autorange="reversed", title=DEPTH_TO_WATER_FT_BGS, fixedrange=False)

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

chart_bgcolor = "#b5aeae"
card_style = {
    "border": "solid",
    "borderRadius": "10px",
    "marginBlock": "5px",
    "backgroundColor": chart_bgcolor,
    "boxShadow": "2px 2px #8d9ea2",
    "borderColor": "7d777a",
}

lcol_style = card_style.copy()
rcol_style = card_style.copy()
header_style = card_style.copy()

lcol_style["marginRight"] = "5px"
rcol_style["marginLeft"] = "5px"
header_style["height"] = "90px"

BGCOLOR = "#d3d3d3"
COLOR_MAP = {"isc_seven_rivers":"blue",
        "ose_roswell":"orange",
        "pvacd_hydrovu":"",
        "healy_collaborative":"purple"}
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
        style_header={'font-family': "verdana"},
        style_data={"fontSize": "12px", "font-family": "verdana"},
        style_table={"height": "300px", "overflowY": "auto"},
    )
    summarytable = DataTable(
        id="summarytable",
        style_cell={"textAlign": "left"},
        columns=[
            {"name": "Location", "id": "location"},
            {"name": "Last Depth to Water (ft)", "id": "last_measurement"},
            {"name": "Measurement Time", "id": "last_time"},
            {"name": "Trend", "id": "trend"},
        ],
        # css=[
        #     {"selector": ".dash-spreadsheet tr th", "rule": "height: 15px;"},
        #     # set height of header
        #     {"selector": ".dash-spreadsheet tr td", "rule": "height: 12px;"},
        #     # set height of body rows
        # ],
        style_header={'font-family': "verdana"},
        style_as_list_view=True,
        style_data={"fontSize": "12px",
                    "font-family": "verdana"},
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
        obs = []
        # iotid = iotid.split('|')
        # for ii in iotid:
        location, obs = get_observations(location_iotid=iotid)
        # obs.extend(iobs)
        # obs = sorted(obs, key=lambda o: o['phenomenonTime'], reverse=True)

        # iotid = iotid[0]
        # print(obs)
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
            yaxis=yaxis,
            xaxis=xaxis,
            paper_bgcolor=chart_bgcolor,
        )

        comp = dcc.Graph(id=f"hydrograph{i}", style=card_style, figure=scatter)

        charts.append(comp)
        lt = obs[0]["phenomenonTime"]
        lm = obs[0]["result"]

        name = location["name"]
        for level in ("Level", "level"):
            if level in name:
                name = name.split(level)[0].strip()
                break

        srow = {
            "location": name,
            "trend": "Falling" if trend > 0 else "Rising",
            "trendvalue": trend,
            "last_measurement": f"{lm:0.2f}",
            "last_time": datetime.datetime.strptime(lt, DTFORMAT).strftime("%c"),
        }
        sdata.append(srow)

    summarytable.data = sdata
    for a, tag in (
        ("ISC Seven Rivers", "isc_seven_rivers"),
        ("OSE Roswell", "ose_roswell"),
        ("Healy Collaborative", "healy_collaborative"),
        ("PVACD Monitoring Wells", "pvacd_hydrovu"),
    ):
        locations = pd.read_json(
            f"https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/{tag}.json"
        )
        locations = locations["locations"]

        lats = [f'{l["location"]["coordinates"][1]:0.3f}' for l in locations]
        lons = [f'{l["location"]["coordinates"][0]:0.3f}' for l in locations]
        ids = [l["name"] for l in locations]
        size = 10
        colors = COLOR_MAP[tag]
        if tag == "pvacd_hydrovu":
            colors = [
                "green" if trends.get(l["@iot.id"], 1) < 0 else "red" for l in locations
            ]
            size = 15


        # data.append(
        #     go.Scattermapbox(
        #         lat=lats,
        #         lon=lons,
        #         showlegend=False,
        #         hoverinfo='none',
        #         marker=dict(size=size+3,
        #                     color='black'
        #                     )
        #     )
        # )
        data.append(
            go.Scattermapbox(
                lat=lats,
                lon=lons,
                text=ids,
                name=a,
                hovertemplate='<b>%{text}</b>',
                # hovertext='',
                # fill='none',
                # line=dict(color='black', width=1),
                marker=dict(size=size,
                            color=colors,
                            # opacity=0.25,
                            )
            )
        )

    figmap = go.Figure(layout=layout, data=data)
    mapcomp = dcc.Graph(id="map", figure=figmap)
    progress = html.Div(
        [
            dcc.Interval(id="progress-interval", n_intervals=0, interval=1000),
            dbc.Progress(id="progress", striped=True, animated=True),
        ],
        id="progress_div",
    )

    dash_app.layout = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Img(
                            # style={"height": "100%", "width": "50%"},
                            src="assets/newmexicowaterdatalogo.png",
                        ),
                        width=3,
                    ),
                    dbc.Col(
                        html.H1(
                            TITLE,
                        ),
                        width=6,
                    ),
                    dbc.Col(width=3)
                    # html.Img(style={'height': '10%', 'width': '10%'},
                    #          src='assets/img/newmexicobureauofgeologyandmineralresources.jpeg')
                ],
                style=card_style,
            ),
            # dbc.Row(html.H1("PVACD Monitoring Locations"), style=card_style),
            dbc.Row(
                [
                    dbc.Col(summarytable, style=lcol_style),
                    dbc.Col(mapcomp, style=rcol_style),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([html.H2("Selection"), tablecomp], style=lcol_style),
                    dbc.Col([progress, hydrocomp], style=rcol_style),
                ],
            ),
            dbc.Row(
                children=charts,
                # style=card_style
            ),
            dbc.Row([html.Footer("Developed By Jake Ross (2022)")]),
        ],
        style={"backgroundColor": BGCOLOR},
    )


def make_additional_selection(location, thing, formation=None):
    data = []
    if not formation:
        gf = thing["properties"].get("GeologicFormation")
        formation = ""
        if gf:
            gfname = get_formation_name(gf)
            formation = f"{gfname} ({gf})"

    data.append(
        {
            "name": "Elevation (ft)",
            "value": floatfmt(location["properties"].get("Altitude")),
        }
    )
    data.append(
        {
            "name": "Well Depth (ft)",
            "value": floatfmt(thing["properties"].get("WellDepth")),
        }
    )

    data.append({"name": "Formation", "value": formation})
    return data


progress_event = Event()


@dash_app.callback(
    [
        Output("progress", "value"),
        Output("progress", "label"),
        Output("progress_div", "style"),
    ],
    [Input("progress-interval", "n_intervals")],
)
def update_progress(n):
    progress_value = 100
    progress_label = ""

    style = {"display": "none"}
    if progress_event.is_set():
        style = {"display": "block"}
    return progress_value, progress_label, style


@dash_app.callback(
    [
        Output("selected_table", "data"),
        Output("hydrograph", "figure"),
    ],
    Input("map", "clickData"),
    # running=[
    #     (Output("progress-interval", "disabled"), False, True),
    # ],
)
def display_click_data(clickData):
    progress_event.set()
    data = [
        {"name": "Location", "value": ""},
        {"name": "Latitude", "value": ""},
        {"name": "Longitude", "value": ""},
        {"name": "PointID", "value": ""},
        {"name": "Elevation (ft)", "value": ""},
        {"name": "Well Depth (ft)", "value": ""},
        {"name": "Formation", "value": ""},
    ]
    # obs = [{"phenomenonTime": 0, "result": 0}]
    # mxs = []
    # mys = []

    fig = go.Figure()
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
                osewellid = ""
                data.append({"name": "OSE Well ID", "value": osewellid})

            except IndexError:
                pass

            thing = location["Things"][0]
            ds = thing["Datastreams"][0]

            _, obs = get_observations(datastream_id=ds["@iot.id"], limit=2000)
            # get the data from NM_Aquifer (via ST2 for these wells)
            try:
                aiotid = crosswalk[crosswalk["PVACD"] == iotid].iloc[0]["NM_AQUIFER"]
            except BaseException:
                aiotid = None

            if aiotid:
                # data.append({"name": "aST ID", "value": aiotid})
                resp = requests.get(f"{ST2}/Locations({aiotid})?$expand=Things")
                if resp.status_code == 200:
                    alocation = resp.json()
                    thing = alocation["Things"][0]
                    data.append({"name": "PointID", "value": alocation["name"]})
                    vs = make_additional_selection(
                        alocation, thing, formation="Artesia (313ARTS)"
                    )
                    data.extend(vs)

                nm_aquifer_location, manual_obs = get_observations(
                    location_iotid=aiotid, limit=100
                )
                mxs = [xi["phenomenonTime"] for xi in manual_obs]
                mys = [xi["result"] for xi in manual_obs]
                # xs = [xi["phenomenonTime"] for xi in obs]
                # ys = [xi["result"] for xi in obs]
                name = "PVACD Continuous"
                fig.add_trace(go.Scatter(x=mxs, y=mys, name="PVACD Historical"))
            else:
                # get the data from USGS
                usgs = get_usgs(location)
                if usgs:
                    name = "OSE-Roswell"

                    uxs, uys = extract_usgs_timeseries(usgs)
                    fig.add_trace(go.Scatter(x=uxs, y=uys, name="USGS NWIS"))
                else:
                    name = "NMBGMR"
                    vs = make_additional_selection(location, thing)
                    data.extend(vs)

        xs = [xi["phenomenonTime"] for xi in obs]
        ys = [xi["result"] for xi in obs]
        fig.add_trace(go.Scatter(x=xs, y=ys, name=name))

    fig.update_layout(
        height=350,
        margin=dict(t=50, b=50, l=50, r=25),
        xaxis=xaxis,
        yaxis=yaxis,
        paper_bgcolor=chart_bgcolor,
    )
    progress_event.clear()
    return data, fig


# usgslocation = '333149104170801'
# usgs = get_usgs(siteid =usgslocation)
# print(extract_usgs_timeseries(usgs))
init_app()

if __name__ == "__main__":
    dash_app.run_server(debug=True, port=8051)
# ============= EOF =============================================
