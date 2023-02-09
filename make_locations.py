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
from itertools import groupby
from operator import attrgetter

import pandas as pd
import requests

from constants import AQUIFER_3DMODEL_MAP
from usgs import get_site_metadata


def make_locations(url, out, source, as_csv=False, datastream_filter=True):
    print(url)
    jobj = requests.get(url)
    print(jobj)
    if as_csv:
        locations = jobj.json()["value"]
        with open("{}.csv".format(out), "w") as wfile:
            for l in locations:
                c = l["location"]["coordinates"]
                row = ",".join([l["name"], str(c[1]), str(c[0])])
                row = "{}\n".format(row)
                wfile.write(row)

    else:
        with open("./data/{}.json".format(out), "w") as wfile:
            obj = {}
            # print(jobj)
            # for ji in jobj.json()['value']:
            #     locations.append({'@iot.id': ji['@iot.id'], 'name': ji['']})
            locations = jobj.json()["value"]
            nlocations = []

            n = len(locations)
            for i, l in enumerate(locations):
                # print(l['name'])
                # if l['name'].lower().strip().endswith('level'):
                #     continue

                print("i={}/{}".format(i, n))
                for thing in l["Things"]:
                    for ds in thing["Datastreams"]:
                        if not datastream_filter or ds["name"] == "Groundwater Levels":
                            l["source"] = source
                            nlocations.append(l)

            print(len(nlocations))
            obj["locations"] = nlocations
            json.dump(obj, wfile, indent=2)


def make_st_agency(
    base_url, out, agency, bounds=None, filter_by_agency=True, pointids=None, **kw
):
    fs = []
    if filter_by_agency:
        fs.append(f"properties/agency%20eq%20%27{agency}%27")
    if bounds:
        points = ",".join(bounds)
        fs.append(f"st_within(Location/location, geography'POLYGON (({points}))')")

    if pointids:
        pf = " or ".join([f"name eq '{p}'" for p in pointids])
        fs.append(f"({pf})")

    f = " and ".join(fs)

    url = (
        f"{base_url}Locations?$orderby=id&" f"$filter={f}" "&$expand=Things/Datastreams"
    )

    make_locations(url, out, agency, **kw)


def get_well_depths():
    with open("./data/locations.json", "r") as rfile:
        obj = json.load(rfile)
        n = len(obj["locations"])
        for i, location in enumerate(obj["locations"]):
            props = location["properties"]
            iotid = location["@iot.id"]
            name = location["name"]
            agency = props["agency"]
            print(f"{i + 1}/{n} examining {agency} {iotid} {name}")

            # print(iotid, props['agency'])
            thing = location["Things"][0]
            tprops = thing["properties"]

            # wdepth = tprops.get("WellDepth")
            wdepth = None
            formation = None
            if not wdepth:
                print(f"    no well depth for {agency} {iotid}, {name}")
                if agency == "OSE-Roswell":
                    md = get_site_metadata(location)
                    if md:
                        md, url = md
                        formation = md["aqfr_cd"]

                        tprops["well_depth"] = wd = md["well_depth_va"]
                        tprops["WellDepth"] = wd
                        if wd:
                            tprops["well_depth_attribution"] = {
                                "agency": "USGS",
                                "source_url": url,
                            }

                        tprops["hole_depth"] = hd = md["hole_depth_va"]
                        tprops["HoleDepth"] = hd
                        if hd:
                            tprops["hole_depth_attribution"] = {
                                "agency": "USGS",
                                "source_url": url,
                            }

                        tprops["GeologicFormation"] = formation
                        tprops["geologic_formation"] = formation
                        if formation:
                            tprops["geologic_formation_attribution"] = {
                                "agency": "USGS",
                                "source_url": url,
                            }

                    # get welldepth from usgs
                    # usgs_data = get_usgs(location)
                    # print(usgs_data)
                    # print(usgs_data.keys())
                    # break

            # else:
            #     coords = location["location"]["coordinates"]
            #     lat, lon = coords[1], coords[0]
            #     formation = get_model_aquifer(lat, lon, wdepth)
            #     tprops["model_formation"] = formation
            #
            #     # compare db formation code with model formation
            #     dbformation = tprops.get("GeologicFormation")
            #     if dbformation:
            #         formation = dbformation
            #         # aquifer = AQUIFER_FORMATION_MAP.get(dbformation)

            if formation:
                aquifer = AQUIFER_3DMODEL_MAP.get(formation, "")
                # aquifer_group = AQUIFER_3DMODEL_MAP.get(aquifer, '')
                tprops.update(
                    {"aquifer": aquifer, "aquifer_attribution": {"agency": "NMWDI"}}
                )
                # for k in ('aquifer_group', 'WellDepth_attribution', 'WellDepth', 'HoleDepth',
                #           'HoleDepth_attribution', 'GeologicFormation', 'GeologicFormation_attribution'):
                #     try:
                #         del tprops[k]
                #     except KeyError:
                #         pass

                patch_thing(thing["@iot.selfLink"], {"properties": tprops})


def patch_thing(url, patch):
    print("    patching", url)
    resp = requests.patch(url, json=patch, auth=("write", "write"))
    print(f"    {resp.status_code}")


def get_model_aquifer(lat, lon, depth):
    print(lat, lon, depth)
    url = f"https://pecosslope-dot-waterdatainitiative-271000.appspot.com/formation/{lon}/{lat}/{depth}"
    resp = requests.get(url)
    if resp.status_code == 200:
        j = resp.json()
        return j["name"]


def group_locations():
    with open("./data/locations.json", "r") as rfile:
        obj = json.load(rfile)
        locations = obj["locations"]

        # key = attrgetter('properties.aquifer')
        def key(l):
            return l["Things"][0]["properties"].get("aquifer", "no_aquifer")

        for gname, gs in groupby(sorted(locations, key=key), key=key):
            gs = list(gs)
            print(gname, len(gs))
            gname = gname.lower().replace(" ", "_")
            out = f"./data/locations_{gname}.json"
            with open(out, "w") as wfile:
                json.dump({"locations": gs}, wfile, indent=2)


def assemble_locations(root=None):
    totallocations = []
    for a, tag in (
        ("ISC Seven Rivers", "isc_seven_rivers"),
        ("OSE Roswell", "ose_roswell"),
        ("Healy Collaborative", "healy_collaborative"),
        # ("PVACD Monitoring Wells", "pvacd_hydrovu"),
    ):
        path = f"{tag}.json"
        if root:
            path = f"{root}/{tag}.json"

        locations = pd.read_json(path)
        totallocations.extend(locations["locations"])

    with open("./data/locations.json", "w") as wfile:
        json.dump({"locations": totallocations}, wfile, indent=2)


def main_make():
    # f"https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/{tag}.json"
    st2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1/"
    # usgs = 'https://labs.waterdata.usgs.gov/sta/v1.1/'
    make_st_agency(st2, "ose_roswell", "OSE-Roswell")
    make_st_agency(st2, "isc_seven_rivers", "ISC_SEVEN_RIVERS")

    ps = [
        "Zumwalt level-822322",
        "Transwestern Level 823779",
        "Cottonwood level-821572",
        "Berrendo-Smith level-823069",
        "LFD Level 826171",
        "Poe Corn Level 819270",
        "Artesia A Level-822328",
        "Orchard Park Level-826157",
        "Greenfield level-822321",
        "Bartlett level-950188",
    ]
    make_st_agency(st2, "pvacd_hydrovu", "PVACD", pointids=ps)
    pointids = [
        "SM-0235",
        "SM-0246",
        "SM-0259",
        "NM-00643",
        "SM-0257",
        "SM-0258",
        "NM-28250",
        "NM-28251",
        "NM-28252",
        "NM-28253",
        "NM-28254",
        "NM-28255",
        "NM-28256",
        "NM-28257",
        "NM-28258",
        "WL-0002",
        "WL-0037",
        "WL-0040",
        "WL-0042",
        "WL-0168",
        "WL-0172",
        "WL-0199",
        "WL-0244",
        "WL-0263",
        "WL-0274",
    ]
    make_st_agency(st2, "healy_collaborative", "NMBGMR", pointids=pointids)

    assemble_locations("./data")
    #
    # points = ['-105.70 34.73', '-103.05 34.73',
    #           '-105.70 32.3',  '-103.05 32.3',
    #           '-105.70 34.73'
    #           ]
    # # make_st_agency(st2, 'nmbgmr', 'NMBGMR', points)
    #
    # make_st_agency(usgs, 'usgs', 'USGS', filter_by_agency=False,
    #                bounds=points, datastream_filter=False)
    # url = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1/Locations?$filter=properties/agency eq 'NMBGMR' and " \
    #       "st_within(" "Location/location, geography'POLYGON (({" "}))')&$expand=Things/Datastreams".format(points)

    # out = 'nmbgmr'
    # make_locations(url, out, 'NMBGMR')
    # # out = 'usgs_pvacd'
    # # make_locations(url, out, 'USGS')


if __name__ == "__main__":
    # st2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1/"
    # make_st_agency(st2, "pvacd_hydrovu", "PVACD")

    get_well_depths()
    # main_make()
    # group_locations()

# ============= EOF =============================================
