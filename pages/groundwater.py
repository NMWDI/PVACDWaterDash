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

import dash
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
    page_registry,
)
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dash_table import DataTable

from gw_util import (
    now_month_name,
    yaxis,
    xaxis,
    crosswalk,
    calculate_stats,
    get_observations,
    get_nm_aquifer_obs,
    make_additional_selection,
)

from styles import (
    lcol_style,
    rcol_style,
    card_style,
    COLOR_MAP,
    chart_bgcolor,
    header_style,
    data_style,
)
from usgs import get_gwl
from util import (
    floatfmt,
    get_formation_name,
    extract_usgs_timeseries,
    todatetime,
    make_customdata,
    prep_hydrovu_name,
)
from constants import (
    DEPTH_TO_WATER_FT_BGS,
    DTFORMAT,
    ST2,
    TITLE,
    DEBUG_N_WELLS,
    DEBUG_OBS,
    DEBUG_LIMIT_OBS,
    USGS_BM,
    ESRI_BM,
    MACROSTRAT_BM,
    OPENTOPO_BM,
    OSM_BM,
    AQUIFER_PVACD_MAP,
    PERMIAN_AQUIFER_SYSTEM,
    PECOS_VALLEY_ALLUVIAL_AQUIFER,
    HIGH_MOUNTAIN_AQUIFER_SYSTEM,
)

dash.register_page(__name__, path="/")
hydrocomp = dcc.Graph(id="hydrograph")

sdata = []
data = []
trends = {}
stats = {}
charts = []
grouped_hydrograph_data = []


summarytable = DataTable(
    id="summarytable",
    tooltip_header={
        "last_measurement": f"Last depth to water. If current value is > than the long term average for"
        f" {now_month_name} highlight row in red",
        "month_average_value": f"Average depth to water (ft) for for all years with water levels in {now_month_name}.",
        "trend": "Depth to water trend. Calculated by performing a linear regression "
        "on the last ~25-50 days depending on sampling frequency",
    },
    css=[
        {
            "selector": ".dash-table-tooltip",
            "rule": "background-color: grey; font-family: verdana; color: white;"
            "width: fit-content; max-width: 440px; min-width: unset; font-size: 10px;"
            "border-radius: 5px",
        },
        {
            "selector": ".dash-tooltip",
            "rule": "max_width: 500px; border-radius: 5px",
        },
    ],
    tooltip_duration=None,
    style_cell={"textAlign": "left"},
    columns=[
        {"name": ["Location", ""], "id": "location"},
        {"name": ["Depth to Water", "ft"], "id": "last_measurement"},
        {"name": ["Avg. Depth to Water", "ft"], "id": "month_average_value"},
        {"name": ["Measurement Time", ""], "id": "last_time"},
        {"name": ["Measurement Int.", "hrs"], "id": "measurement_interval"},
        {"name": ["Trend", ""], "id": "trend"},
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
                "filter_query": "{month_average_value_diff}<0",
            },
            "backgroundColor": "red",
            "color": "white",
        },
        {
            "if": {
                "column_id": "last_measurement",
                "filter_query": "{month_average_value_diff}>0",
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


for i, row in crosswalk.iterrows():
    iotid = row["PVACD"]
    print(iotid, row)

    location, obs = get_observations(location_iotid=iotid, limit=10000)
    obs = [o for i, o in enumerate(obs) if not i % 10]
    historic_obs = get_nm_aquifer_obs(iotid)
    if historic_obs:
        obs.extend(historic_obs)

    obs = sorted(obs, key=lambda o: o["phenomenonTime"], reverse=True)
    obs = [o for i, o in enumerate(obs) if not i % 5]

    scatter = px.line(obs, x="phenomenonTime", y="result", height=350)
    xs = [o["phenomenonTime"] for o in obs]
    ys = [o["result"] for o in obs]
    grouped_hydrograph_data.append(
        go.Scatter(x=xs, y=ys, name=prep_hydrovu_name(location["name"]))
    )

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
        "month_average_value_diff": month_average - lm,
        "month_average_value": f"{month_average:0.2f}",
        "last_measurement": f"{lm:0.2f}",
        "measurement_interval": floatfmt(interval / 3600.0, 1),
        "last_time": todatetime(lt).strftime("%H:%M %m/%d/%y"),
    }
    sdata.append(srow)

summarytable.data = sdata
for a, tag in (
    # ("ISC Seven Rivers", "isc_seven_rivers"),
    # ("OSE Roswell", "ose_roswell"),
    ("Well, uncertain aquifer", "locations_no_aquifer"),
    (PERMIAN_AQUIFER_SYSTEM, "locations_permian_aquifer_system"),
    (PECOS_VALLEY_ALLUVIAL_AQUIFER, "locations_pecos_valley_alluvial_aquifer"),
    (HIGH_MOUNTAIN_AQUIFER_SYSTEM, "locations_high_mountain_aquifer_system"),
    ("PVACD Monitoring Wells", "pvacd_hydrovu"),
):
    locations = pd.read_json(
        f"./data/{tag}.json"
        # f"https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/{tag}.json"
    )
    locations = locations["locations"]

    lats = [f'{l["location"]["coordinates"][1]:0.3f}' for l in locations]
    lons = [f'{l["location"]["coordinates"][0]:0.3f}' for l in locations]
    ids = [l["name"] for l in locations]
    size = 10
    colors = COLOR_MAP[tag]
    if tag == "pvacd_hydrovu":
        # colors = [
        #     "green" if trends.get(l["@iot.id"], 1) < 0 else "red" for l in locations
        # ]
        size = 15
        # ids = [prep_hydrovu_name(i) for i in ids]
    else:
        a = AQUIFER_PVACD_MAP.get(a, a)

    data.append(
        go.Scattermapbox(
            lat=lats,
            lon=lons,
            text=ids,
            name=a,
            customdata=make_customdata(locations, tag),
            hovertemplate="<b>%{text}</b><br>%{customdata}",
            marker=dict(
                size=size,
                color=colors,
            ),
        )
    )


tablecomp = DataTable(
    id="selected_table",
    style_cell={"textAlign": "left"},
    columns=[{"name": "Name", "id": "name"}, {"name": "Value", "id": "value"}],
    style_as_list_view=True,
    style_header=header_style,
    style_data=data_style,
    style_table={"height": "350px", "overflowY": "auto"},
)

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
gchart = dcc.Graph(id="grouped_hydrograph", style=card_style, figure=grouped_hydrograph)
slider = dcc.Slider(
    0,
    100,
    value=75,
    id="basemap_opacity",
    tooltip={"placement": "bottom", "always_visible": False},
    marks=None,
)
label = html.Label("Opacity")
sliderdiv = html.Div([label, slider])

maptoolrow = dbc.Row(
    [
        dbc.Col(
            dbc.DropdownMenu(
                label="Base Map",
                size="sm",
                color="secondary",
                style={"marginTop": "5px"},
                id="basemap_select",
                children=[
                    dbc.DropdownMenuItem("USGS Base Map", id="usgs_basemap_select"),
                    dbc.DropdownMenuItem("Macrostrat", id="macrostrat_basemap_select"),
                    dbc.DropdownMenuItem(
                        "ESRI World Imagery",
                        id="esri_basemap_select",
                    ),
                    dbc.DropdownMenuItem("Open Topo", id="opentopo_basemap_select"),
                    dbc.DropdownMenuItem("Open Street Map", id="osm_basemap_select"),
                    # dbc.DropdownMenuItem("Item 3"),
                ],
            ),
            width=2,
        ),
        dbc.Col(sliderdiv),
        dbc.Col(
            dbc.Input(
                id="search_input",
                placeholder="Search for a well..",
                type="text",
                debounce=True,
                style={"marginTop": "10px"},
            )
        ),
    ]
)

first_row = dbc.Row(
    [
        dbc.Col(
            html.Div([html.H4("PVACD Monitoring Wells"), summarytable]),
            style=lcol_style,
            width=6,
        ),
        dbc.Col(
            html.Div(
                [
                    maptoolrow,
                    mapcomp,
                ]
            ),
            style=rcol_style,
        ),
    ]
)

layout = html.Div(
    [
        first_row,
        dbc.Row(
            [
                dbc.Col([html.H4("Selected Well"), tablecomp], style=lcol_style),
                dbc.Col(
                    [
                        dbc.Button(
                            "Download Selected",
                            style={"margin": "5px"},
                            color="secondary",
                            size="sm",
                            title="Download all the water levels for the selected location"
                            " as a single csv file",
                            id="download_selected_btn",
                        ),
                        dcc.Download(id="download_selected_csv"),
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
                        dbc.Button(
                            "Download Monitoring Wells",
                            style={"margin": "10px", "width": "40%"},
                            color="primary",
                            title="Download all the water levels for all the monitoring"
                            " wells as a single csv file",
                            id="download_monitor_wells_btn",
                        ),
                        dcc.Download(id="download-csv"),
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
    ]
)


@dash.callback(
    Output("map", "figure"),
    [
        Input("usgs_basemap_select", "n_clicks"),
        Input("macrostrat_basemap_select", "n_clicks"),
        Input("esri_basemap_select", "n_clicks"),
        Input("opentopo_basemap_select", "n_clicks"),
        Input("osm_basemap_select", "n_clicks"),
        Input("basemap_opacity", "value"),
        Input("search_input", "value"),
        State("map", "figure"),
    ],
    prevent_initial_call=True,
)
def handle_basemap_select(a, b, c, d, e, opacity, search_input, fig):
    # print('asdf', a, b)
    l = None
    if ctx.triggered_id == "usgs_basemap_select":
        l = USGS_BM
    elif ctx.triggered_id == "macrostrat_basemap_select":
        l = MACROSTRAT_BM
    elif ctx.triggered_id == "esri_basemap_select":
        l = ESRI_BM
    elif ctx.triggered_id == "opentopo_basemap_select":
        l = OPENTOPO_BM
    elif ctx.triggered_id == "osm_basemap_select":
        fig["layout"]["mapbox"]["layers"] = []
    elif ctx.triggered_id == "search_input":
        search_input = search_input.lower()
        for di in fig["data"]:
            location = next(
                (
                    (i, name)
                    for i, name in enumerate(di["text"])
                    if name.lower().startswith(search_input)
                ),
                None,
            )
            if location:
                idx, location = location
                lat = di["lat"][idx]
                lon = di["lon"][idx]
                fig["layout"]["mapbox"]["center"] = {"lat": lat, "lon": lon}
                fig["layout"]["mapbox"]["zoom"] = 11
    elif ctx.triggered_id == "basemap_opacity":
        layers = fig["layout"]["mapbox"].get("layers")
        if layers:
            l = layers[0]

    if l:
        l["opacity"] = opacity / 100.0

        fig["layout"]["mapbox"]["layers"] = [
            l,
        ]
    return fig


@dash.callback(
    Output("download_selected_csv", "data"),
    [Input("download_selected_btn", "n_clicks"), Input("hydrograph", "figure")],
    prevent_initial_call=True,
)
def handle_download_selected(n, fig):
    if ctx.triggered_id == "download_selected_btn":
        return make_fig_csv(fig)


@dash.callback(
    Output("download-csv", "data"),
    [
        Input("download_monitor_wells_btn", "n_clicks"),
        Input("grouped_hydrograph", "figure"),
    ],
    prevent_initial_call=True,
)
def handle_download_monitor_wells(n, fig):
    if ctx.triggered_id == "download_monitor_wells_btn":
        return make_fig_csv(fig)


def make_fig_csv(fig):
    data = fig["data"]
    if data:
        content = [
            "please cite this data: New Mexico Water Data Initiative https://newmexicowaterdata.org"
        ]
        for di in data:
            content.append(f'location_name: {di["name"]}')
            content.append(f"measurement_timestamp, depth_to_water_ft_bgs")
            for xi, yi in zip(di["x"], di["y"]):
                row = f"{xi},{yi}"
                content.append(row)

        content = "\n".join(content)
        return dict(content=content, filename="download.csv")


@dash.callback(
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


@dash.callback(
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
        {"name": "Lat/Lon", "value": ""},
        {"name": "Source", "value": ""},
        {"name": "PointID", "value": ""},
        {"name": "Elevation (ft)", "value": ""},
        {"name": "Well Depth (ft)", "value": ""},
        {"name": "Aquifer (PVACD)", "value": ""},
        {"name": "Aquifer", "value": ""},
        {"name": "Formation", "value": ""},
        {"name": "Model Formation", "value": ""},
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
        print(point)
        name = point["text"]
        url = f"{ST2}/Locations?$filter=name eq '{name}'&$expand=Things/Datastreams"
        resp = requests.get(url)
        data = [
            {"name": "Location", "value": name},
            {"name": "Lat/Lon", "value": f'{point["lat"]}, {point["lon"]}'},
        ]

        if resp.status_code == 200:
            try:
                location = resp.json()["value"][0]
                iotid = location["@iot.id"]
                osewellid = ""
                data.append(
                    {"name": "Source", "value": location["properties"]["agency"]}
                )
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
                vs = make_additional_selection(location, thing)
                data.extend(vs)
            else:
                # get the data from USGS
                usgs = get_gwl(location)
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

        fd = [go.Scatter(x=xs, y=ys, name=name, mode="markers+lines")]

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


# ============= EOF =============================================
