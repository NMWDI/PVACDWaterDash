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
        # fs.append(f"{gfname} ({gf})")
        fs.append(gfname)

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


def make_customdata(locations, tag):
    fs = []
    for l in locations:
        if tag == "pvacd_hydrovu":
            code = "313SADR"
        else:
            code = l["Things"][0]["properties"].get("GeologicFormation")

        customdata = []
        if code:
            name = get_formation_name(code)
            customdata.append(f"Formation: {name}")

        welldepth = l["Things"][0]["properties"].get("WellDepth")
        if welldepth:
            customdata.append(f"Well Depth: {welldepth} (ft)")

        customdata = "<br>".join(customdata)
        fs.append(customdata)

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


# ============= EOF =============================================
