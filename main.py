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
import os
import time
from asyncio import Event
from collections.abc import Collection
from itertools import groupby

import dash_bootstrap_components as dbc
import datetime as datetime
import requests as requests
from numpy import polyfit, linspace, polyval

from dash import (
    Dash,
    html,
    dcc,
    Output,
    Input,
    DiskcacheManager,
    CeleryManager,
    ctx,
    State,
)
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dash_table import DataTable

from util import (
    floatfmt,
    get_formation_name,
    get_usgs,
    extract_usgs_timeseries,
    todatetime,
    make_formations,
)
from constants import (
    DEPTH_TO_WATER_FT_BGS,
    DTFORMAT,
    ST2,
    TITLE,
    DEBUG_N_WELLS,
    DEBUG_OBS,
    DEBUG_LIMIT_OBS,
)

# from celery import Celery
# url = ''
# celery_app = Celery(__name__, broker=url, backend=url)
# background_callback_manager = CeleryManager(celery_app)

# if "REDIS_URL" in os.environ:
#     # Use Redis & Celery if REDIS_URL set as an env variable
#     from celery import Celery
#
#     celery_app = Celery(
#         __name__, broker=os.environ["REDIS_URL"], backend=os.environ["REDIS_URL"]
#     )
#     background_callback_manager = CeleryManager(celery_app)
#
# else:
#
#     # Diskcache for non-production apps when developing locally
#     import diskcache
#
#     cache = diskcache.Cache("/tmp/cache")
#     background_callback_manager = DiskcacheManager(cache)

from flask_caching import Cache

config = {
    "DEBUG": True,  # some Flask specific configs
    "CACHE_TYPE": "FileSystemCache",  # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_DIR": "/tmp/cache",
}

dash_app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="PVACD Groundwater Dashboard",
    # background_callback_manager=background_callback_manager,
)

app = dash_app.server
cache = Cache(app, config=config)

crosswalk = pd.read_csv(
    "https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv"
)
if DEBUG_N_WELLS:
    crosswalk = crosswalk[:DEBUG_N_WELLS]
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
chart_bgcolor = "white"
card_style = {
    "border": "solid",
    "borderRadius": "10px",
    "marginBlock": "3px",
    "backgroundColor": chart_bgcolor,
    "boxShadow": "2px 2px #8d9ea2",
    "borderColor": "7d777a",
}

lcol_style = card_style.copy()
rcol_style = card_style.copy()

lcol_style["marginRight"] = "5px"
# rcol_style["marginLeft"] = "5px"

header_style = {"font-family": "verdana", "font-weight": "bold", "fontSize": "10px"}
data_style = {"fontSize": "10px", "font-family": "verdana"}
BGCOLOR = "#d3d3d3"
COLOR_MAP = {
    "isc_seven_rivers": "orange",
    "ose_roswell": "orange",
    "pvacd_hydrovu": "",
    "healy_collaborative": "orange",
}


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
            x=0.66,
            bgcolor="#899DBE",
            borderwidth=3,
        ),
    )

    tablecomp = DataTable(
        id="selected_table",
        style_cell={"textAlign": "left"},
        columns=[{"name": "Name", "id": "name"}, {"name": "Value", "id": "value"}],
        style_as_list_view=True,
        style_header=header_style,
        style_data=data_style,
        style_table={"height": "300px", "overflowY": "auto"},
    )
    summarytable = DataTable(
        id="summarytable",
        tooltip_header={
            "last_measurement": f"Last depth to water (long term average depth to water for "
            f"{now_month_name}). \nIf current value is > than the longer average "
            f"for "
            f"{now_month_name} highlight row in red"
        },
        css=[
            {
                "selector": ".dash-table-tooltip",
                "rule": "background-color: grey; font-family: monospace; color: white;"
                "width: fit-content; max-width: 440px; min-width: unset; font-size: 10px",
            },
            {"selector": ".dash-tooltip", "rule": "max_width: 500px"},
        ],
        tooltip_duration=None,
        style_cell={"textAlign": "left"},
        columns=[
            {"name": "Location", "id": "location"},
            {"name": "Last Depth to Water (ft)", "id": "last_measurement"},
            {"name": "Measurement Time", "id": "last_time"},
            {"name": "Measurement Interval (hrs)", "id": "measurement_interval"},
            {"name": "Trend", "id": "trend"},
        ],
        style_header=header_style,
        style_as_list_view=True,
        style_data=data_style,
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
            {
                "if": {
                    "column_id": "last_measurement",
                    "filter_query": "{month_average_value}<0",
                },
                "backgroundColor": "red",
                "color": "white",
            },
            {
                "if": {
                    "column_id": "last_measurement",
                    "filter_query": "{month_average_value}>0",
                },
                "backgroundColor": "green",
                "color": "white",
            },
        ],
        style_table={
            # "padding_top": "10px",
            "overflowY": "auto",
        },
    )

    hydrocomp = dcc.Graph(id="hydrograph")

    sdata = []
    data = []
    trends = {}
    stats = {}
    charts = []
    grouped_hydrograph_data = []
    for i, row in crosswalk.iterrows():
        iotid = row["PVACD"]
        print(iotid, row)

        location, obs = get_observations(location_iotid=iotid)

        historic_obs = get_nm_aquifer_obs(iotid)
        if historic_obs:
            obs.extend(historic_obs)

        obs = sorted(obs, key=lambda o: o["phenomenonTime"], reverse=True)
        obs = [o for i, o in enumerate(obs) if not i % 3]

        scatter = px.line(obs, x="phenomenonTime", y="result", height=350)
        xs = [o["phenomenonTime"] for o in obs]
        ys = [o["result"] for o in obs]
        grouped_hydrograph_data.append(go.Scatter(x=xs, y=ys, name=location["name"]))

        stats[iotid] = stat = calculate_stats(obs)
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

        interval = (todatetime(obs[0]) - todatetime(obs[1])).total_seconds()
        name = location["name"]
        for level in ("Level", "level"):
            if level in name:
                name = name.split(level)[0].strip()
                break

        month_average = stat["month_average"]

        srow = {
            "location": name,
            "trend": "Falling" if trend > 0 else "Rising",
            "trendvalue": trend,
            "month_average_value": month_average - lm,
            "last_measurement": f"{lm:0.2f} ({month_average:0.2f})",
            "measurement_interval": floatfmt(interval / 3600.0, 1),
            "last_time": todatetime(lt).strftime("%H:%M %m/%d/%y"),
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

        data.append(
            go.Scattermapbox(
                lat=lats,
                lon=lons,
                text=ids,
                name=a,
                customdata=make_formations(locations, tag),
                hovertemplate="<b>%{text}</b><br>%{customdata}",
                marker=dict(
                    size=size,
                    color=colors,
                ),
            )
        )

    figmap = go.Figure(layout=layout, data=data)
    grouped_hydrograph = go.Figure(
        data=grouped_hydrograph_data,
        layout=dict(
            margin=dict(t=75, b=50, l=50, r=25),
            yaxis=yaxis,
            xaxis=xaxis,
            paper_bgcolor=chart_bgcolor,
        ),
    )
    mapcomp = dcc.Graph(id="map", figure=figmap)
    gchart = dcc.Graph(
        id="grouped_hydrograph", style=card_style, figure=grouped_hydrograph
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
                    dbc.Col(
                        html.Div([html.H3("Monitoring Wells"), summarytable]),
                        style=lcol_style,
                        width=6,
                    ),
                    dbc.Col(mapcomp, style=rcol_style),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col([html.H3("Map Selection"), tablecomp], style=lcol_style),
                    dbc.Col(
                        [
                            dbc.Spinner(
                                [html.Div(id="loading-output"), hydrocomp],
                                # fullscreen=True,
                                color="primary",
                            ),
                        ],
                        style=rcol_style,
                    ),
                ],
            ),
            dbc.Row(
                children=[
                    dbc.ButtonGroup(
                        children=[
                            dbc.Button(
                                "Show Hydrographs",
                                color="primary",
                                id="toggle_show_hydrographs",
                                style={"margin": "10px", "width": "40%"},
                            ),
                            dbc.Button(
                                "Show Grouped Hydrograph",
                                style={"margin": "10px", "width": "40%"},
                                color="primary",
                                id="toggle_show_grouped_hydrograph",
                            ),
                        ]
                    )
                ],
            ),
            dbc.Row(
                [
                    html.Div(children=charts, id="igraph_container"),
                    html.Div(children=gchart, id="ggraph_container"),
                ],
            ),
            dbc.Row([html.Footer("Developed By Jake Ross (2022)")]),
        ],
        # fluid=True,
        # className="container-fluid",
        style={
            "backgroundColor": BGCOLOR,
        },
    )


now = datetime.datetime.now()
now_month = now.month
now_month_name = now.strftime("%B")


def calculate_stats(obs):
    obs = [(todatetime(o), o["result"]) for o in obs]
    obs = [o for o in obs if o[0].month == now_month]
    ys = [o[1] for o in obs]
    month_average = sum(ys) / len(ys)

    return {"month_average": month_average}


def make_additional_selection(location, thing, formation=None, formation_code=None):
    data = []

    if not formation and not formation_code:
        formation_code = thing["properties"].get("GeologicFormation")

    formation = ""
    if formation_code:
        formation = get_formation_name(formation_code)

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


@cache.memoize()
def get_observations(location_iotid=None, datastream_id=None, limit=1000):
    if DEBUG_OBS:
        now = datetime.datetime.now()
        t0 = now - datetime.timedelta(hours=0)
        t1 = now - datetime.timedelta(hours=12)
        t2 = now - datetime.timedelta(hours=24)
        l = {"name": "Foo"}
        obs = [
            {
                "phenomenonTime": t0.strftime(DTFORMAT),
                "result": 0,
            },
            {
                "phenomenonTime": t1.strftime(DTFORMAT),
                "result": 0,
            },
            {
                "phenomenonTime": t2.strftime(DTFORMAT),
                "result": 0,
            },
        ]
        return l, obs

    if datastream_id is None:
        url = f"{ST2}/Locations({location_iotid})?$expand=Things/Datastreams"
        resp = requests.get(url)

        if resp.status_code == 200:
            location = resp.json()
            ds = location["Things"][0]["Datastreams"][0]
            datastream_id = ds["@iot.id"]
    else:
        location = None

    if DEBUG_LIMIT_OBS:
        limit = DEBUG_LIMIT_OBS

    url = (
        f"{ST2}/Datastreams({datastream_id})/Observations?$orderby=phenomenonTime desc&$select=phenomenonTime,"
        f"result&$top={limit}"
    )

    resp = requests.get(url)
    if resp.status_code == 200:
        j = resp.json()
        obs = j["value"]
        nextlink = j.get("@iot.nextLink")

        while len(obs) < limit and nextlink:
            resp = requests.get(nextlink)
            if resp.status_code == 200:
                j = resp.json()
                obs.extend(j["value"])
                nextlink = j.get("@iot.nextLink")

        return location, obs


@cache.memoize()
def get_nm_aquifer_obs(iotid, data=None):
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
            if data is not None:
                data.append({"name": "PointID", "value": alocation["name"]})
                vs = make_additional_selection(
                    alocation, thing, formation_code="313SADR"
                )
                data.extend(vs)

        nm_aquifer_location, manual_obs = get_observations(location_iotid=aiotid)
        return manual_obs


@dash_app.callback(
    [
        Output("igraph_container", "style"),
        Output("ggraph_container", "style"),
        Output("toggle_show_hydrographs", "children"),
        Output("toggle_show_grouped_hydrograph", "children"),
    ],
    [
        Input("toggle_show_hydrographs", "n_clicks"),
        Input("toggle_show_grouped_hydrograph", "n_clicks"),
        State("toggle_show_hydrographs", "children"),
        State("toggle_show_grouped_hydrograph", "children"),
    ],
)
def handle_toggle_grouping(n, n2, tsh, tsgh):
    gstyle = {"display": "none"}
    istyle = {"display": "none"}
    istate = "Show Hydrographs"
    gstate = "Show Grouped Hydrograph"

    if ctx.triggered_id == "toggle_show_hydrographs":
        gstyle = {"display": "none"}
        istyle = {"display": "none"}
        istate = "Show Hydrographs"
        if tsh == "Show Hydrographs":
            istyle = {"display": "block"}
            istate = "Hide Hydrographs"

    if ctx.triggered_id == "toggle_show_grouped_hydrograph":
        istyle = {"display": "none"}
        gstyle = {"display": "none"}
        if tsgh == "Show Grouped Hydrograph":
            gstyle = {"display": "block"}
            gstate = "Hide Grouped Hydrograph"

    return istyle, gstyle, istate, gstate


@dash_app.callback(
    [
        Output("loading-output", "children"),
        Output("selected_table", "data"),
        Output("hydrograph", "figure"),
        # Output("progress-div", "children")
    ],
    Input("map", "clickData"),
)
def display_click_data(clickData):
    # print('clasd', clickData)
    # set_progress()
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
    # uxs = None
    # mxs = None
    # name = None
    location = None
    obs = None
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
            nm_aquifer_obs = get_nm_aquifer_obs(iotid, data)
            if nm_aquifer_obs:
                obs.extend(nm_aquifer_obs)

            else:
                # get the data from USGS
                usgs = get_usgs(location)
                if usgs:
                    # name = "OSE-Roswell"
                    obsu = extract_usgs_timeseries(usgs)
                    obs.extend(obsu)
                else:
                    # name = "NMBGMR"
                    vs = make_additional_selection(location, thing)
                    data.extend(vs)

    fd = []
    if obs:
        # print('nasadfme', name, len(obs), len(uxs) if uxs else 0)
        obs = sorted(obs, key=lambda x: x["phenomenonTime"])

        xs = [xi["phenomenonTime"] for xi in obs]
        ys = [xi["result"] for xi in obs]

        fd = [go.Scatter(x=xs, y=ys)]

    layout = dict(
        height=350,
        margin=dict(t=50, b=50, l=50, r=25),
        xaxis=xaxis,
        yaxis=yaxis,
        title=location["name"] if location else "",
        paper_bgcolor=chart_bgcolor,
    )

    fig = go.Figure(data=fd, layout=layout)

    return "", data, fig


# usgslocation = '333149104170801'
# usgs = get_usgs(siteid =usgslocation)
# print(extract_usgs_timeseries(usgs))
init_app()

if __name__ == "__main__":
    dash_app.run_server(debug=True, port=8051)
# ============= EOF =============================================
