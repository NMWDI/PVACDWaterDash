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
import json
import datetime

import requests

from constants import ST2, DEBUG_OBS, DTFORMAT, DEBUG_LIMIT_OBS


def floatfmt(t, n=2):
    if t is None:
        return ""

    try:
        f = float(t)
        return f"{f:0.{n}f}"
    except ValueError:
        return t


FORMATION_MAP = None


def get_formation_name(code):
    global FORMATION_MAP
    if FORMATION_MAP is None:
        with open("./formations.json") as rfile:
            FORMATION_MAP = json.load(rfile)

    def get(c):
        for f in FORMATION_MAP:
            if f["Code"] == c:
                return f["Meaning"]
        else:
            return c

    fs = []
    for gf in code.split("/"):
        gfname = get(gf)
        fs.append(f"{gfname} ({gf})")

    formation = "/".join(fs)
    return formation


def extract_usgs_timeseries(obj):
    # print(obj.keys())
    ts = obj["value"]["timeSeries"]
    # print(len(ts))
    data = []
    xs = []
    ys = []
    for i, ti in enumerate(ts):
        # print(ti.keys(), ti['variable'].keys(), ti['variable']['variableCode'][0])
        # print(ti['variable']['variableName'])
        # if ti['variable']['variableCode'][0]['variableID'] == 52331280:
        if (
            ti["variable"]["variableName"]
            == "Depth to water level, ft below land surface"
        ):
            for j, tj in enumerate(ti["values"]):
                values = tj["value"]
                data.append(
                    {
                        "phenomenonTime": values[0]["dateTime"],
                        "result": values[0]["value"],
                    }
                )

    return data
    # if data:
    #     xs, ys = zip(*[(x["dateTime"], x["value"]) for x in data])

    # return xs, ys


def make_formations(locations, tag):
    fs = []
    for l in locations:
        if tag == "pvacd_hydrovu":
            code = "313SADR"
        else:
            code = l["Things"][0]["properties"].get("GeologicFormation")
        name = ""
        if code:
            name = get_formation_name(code)

        fs.append(name)

    return fs


def todatetime(t, fmt=DTFORMAT):
    if isinstance(t, dict):
        t = t["phenomenonTime"]

    return datetime.datetime.strptime(t, fmt)


def get_usgs(location=None, siteid=None):
    if location:
        if location["properties"]["agency"] == "OSE-Roswell":
            siteid = location["name"].replace(" ", "")

    if siteid:
        url = f"https://waterservices.usgs.gov/nwis/gwlevels/?format=json&sites={siteid}&siteStatus=all"
        resp = requests.get(url)
        return resp.json()


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


# ============= EOF =============================================
