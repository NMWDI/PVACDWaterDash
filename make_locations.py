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

import requests


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
        with open("{}.json".format(out), "w") as wfile:

            obj = {}
            # print(jobj)
            # for ji in jobj.json()['value']:
            #     locations.append({'@iot.id': ji['@iot.id'], 'name': ji['']})
            locations = jobj.json()["value"]
            nlocations = []

            n = len(locations)
            for i, l in enumerate(locations):
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


if __name__ == "__main__":
    st2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1/"
    # usgs = 'https://labs.waterdata.usgs.gov/sta/v1.1/'
    # make_st_agency(st2, 'ose_roswell', 'OSE-Roswell')
    # make_st_agency(st2, 'isc_seven_rivers', 'ISC_SEVEN_RIVERS')
    # make_st_agency(st2, 'pvacd_hydrovu', 'PVACD')
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
# ============= EOF =============================================
