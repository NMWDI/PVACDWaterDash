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

import pandas as pd
import requests

from constants import (
    ST2,
    DEBUG_N_WELLS,
    AQUIFER_PVACD_MAP,
    DEBUG_OBS,
    DTFORMAT,
    DEPTH_TO_WATER_FT_BGS,
    DEBUG_LIMIT_OBS,
)
from util import todatetime, get_formation_name, floatfmt

crosswalk = pd.read_csv(
    "https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/pvacd_nm_aquifer.csv"
)
if DEBUG_N_WELLS:
    crosswalk = crosswalk[:DEBUG_N_WELLS]

now = datetime.datetime.now()
now_month = now.month
now_month_name = now.strftime("%B")

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


def calculate_stats(obs):
    obs = [(todatetime(o), o["result"]) for o in obs]
    obs = [o for o in obs if o[0].month == now_month]
    ys = [o[1] for o in obs]
    month_average = sum(ys) / len(ys)

    return {"month_average": month_average}


def make_additional_selection(location, thing, formation=None, formation_code=None):
    data = []

    tprops = thing["properties"]
    if not formation and not formation_code:
        formation_code = tprops.get("GeologicFormation")

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
            "value": floatfmt(tprops.get("WellDepth")),
        }
    )

    aquifer = tprops.get("aquifer", "")
    model_formation = tprops.get("model_formation", "")
    pvacd_aquifer_name = AQUIFER_PVACD_MAP.get(aquifer, "")

    data.append({"name": "Aquifer (PVACD)", "value": pvacd_aquifer_name})
    data.append({"name": "Aquifer", "value": aquifer})
    # data.append({"name": "Aquifer Group", "value": aquifer_group})
    data.append({"name": "Formation", "value": formation})
    data.append({"name": "Model Formation", "value": model_formation})
    return data


# @cache.memoize()
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
        print("lea", len(obs))
        return location, obs


# @cache.memoize()
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

        nm_aquifer_location, manual_obs = get_observations(
            location_iotid=aiotid, limit=10000
        )
        return manual_obs


# ============= EOF =============================================
