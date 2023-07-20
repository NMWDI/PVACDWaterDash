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
    page_registry,
    page_container,
)
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dash_table import DataTable

from gw_util import yaxis, xaxis
from styles import card_style, chart_bgcolor
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
    "CACHE_DEFAULT_TIMEOUT": 3,
    "CACHE_DIR": "/tmp/cache",
}

dash_app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title=TITLE,
    use_pages=True
    # background_callback_manager=background_callback_manager,
)

app = dash_app.server
cache = Cache(app, config=config)

# now = datetime.datetime.now()
# now_month = now.month
# now_month_name = now.strftime("%B")

crosswalk = pd.read_csv(
    "https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv"
)
if DEBUG_N_WELLS:
    crosswalk = crosswalk[:DEBUG_N_WELLS]

now = datetime.datetime.now()
now_month = now.month
now_month_name = now.strftime("%B")

# chart_bgcolor = "#b5aeae"
# chart_bgcolor = "white"
# card_style = {
#     "border": "solid",
#     "borderRadius": "10px",
#     "marginBlock": "3px",
#     "backgroundColor": chart_bgcolor,
#     "boxShadow": "2px 2px #8d9ea2",
#     "borderColor": "7d777a",
# }
#
# lcol_style = card_style.copy()
# rcol_style = card_style.copy()

# lcol_style["marginRight"] = "5px"
# rcol_style["marginLeft"] = "5px"


BGCOLOR = "#d3d3d3"
# COLOR_MAP = {
#     # "isc_seven_rivers": "orange",
#     # "ose_roswell": "orange",
#     # "pvacd_hydrovu": "",
#     # "healy_collaborative": "orange",
#     # "locations": "orange",
#     ""
# }


banner_style = card_style.copy()
# banner_style['background-image']="url('assets/new-mexico-408068_1280.jpg')"
banner_style["backgroundImage"] = "url('assets/1599247175576.jpg')"
banner_style["backgroundRepeat"] = "no-repeat"
# banner_style["background-attachment"]= "fixed"
banner_style["backgroundSize"] = "cover"
banner_style["backgroundPosition"] = "0% 5%"
# banner_style['background-image']="url('assets/pvacd_logo.png')"

banner_row = dbc.Row(
    [
        dbc.Col(
            html.A(
                href="https://newmexicowaterdata.org",
                children=[
                    html.Img(
                        src="assets/newmexicowaterdatalogo.png",
                        height=75,
                        style={"margin": "10px"},
                    )
                ],
            ),
            width=3,
        ),
        dbc.Col(
            html.H1(TITLE, style={"marginTop": "10px"}),
            width=6,
        ),
        dbc.Col(
            html.A(
                href="https://pvacd.com",
                children=[
                    html.Img(
                        src="assets/pvacd_logo.png",
                        height=75,
                        style={"margin": "10px"},
                    )
                ],
            ),
            width=3,
        ),
    ],
    style=banner_style,
)
buttons = [
    dbc.Button(
        f"{page['name']}",
        color="secondary",
        style={"margin": "5px"},
        href=page["relative_path"],
    )
    for page in page_registry.values()
]

subbanner_row = dbc.Row(
    [
        html.Div(
            [
                dbc.Button(
                    "Pecos Slope Story Map",
                    color="secondary",
                    style={"margin": "5px"},
                    href="https://nmt.maps.arcgis.com/apps/Cascade/index.html?appid=2f22f13a81f04042aabcfbe2e739ca96",
                ),
                #     dbc.Button(
                #         'Weather Stations',
                #         color="secondary",
                #         style={"margin": "5px"},
                #         href="/weather",
                #     )
            ]
            + buttons,
            style=card_style,
        )
    ]
)


def init_app():
    dash_app.layout = dbc.Container(
        [
            banner_row,
            subbanner_row,
            page_container,
            # dbc.Row(html.H1("PVACD Monitoring Locations"), style=card_style),
            dbc.Row(
                [
                    html.Footer(
                        "Developed By Jake Ross (2022). "
                        "Assembled with data from NMBGMR, OSE, USGS, PVACD and ISC"
                    )
                ]
            ),
        ],
        # fluid=True,
        # className="container-fluid",
        style={
            "backgroundColor": BGCOLOR,
        },
    )


# usgslocation = '333149104170801'
# usgs = get_usgs(siteid =usgslocation)
# print(extract_usgs_timeseries(usgs))
init_app()

if __name__ == "__main__":
    dash_app.run_server(debug=True, port=8051)
# ============= EOF =============================================
