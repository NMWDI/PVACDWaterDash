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
import geojson as geojson
import pandas as pd
import requests

OSE = 'https://ose.newmexicowaterdata.org/FROST-Server/v1.1'


def get_ose_roswell_locations():
    locations = pd.read_json(
        f"https://raw.githubusercontent.com/NMWDI/VocabService/main/pvacd_hydroviewer/ose_roswell.json"
    )
    return locations["locations"]


def make_within(wkt):
    return f"st_within(Location/location, geography'{wkt}')"


def get_ose_pods_location(l):
    lon = l['location']['coordinates'][0]
    lat = l['location']['coordinates'][1]
    from shapely import geometry, affinity
    center = geometry.Point(lon, lat)  # Null Island
    radius = 0.001
    circle = center.buffer(radius, cap_style=3)  # Degrees Radius
    # print(circle.wkt)
    within = make_within(circle.wkt)
    url = f"{OSE}/Locations?$filter={within} and properties/pod_sub_basin eq 'RA'&$expand=Things"
    # print(url)
    resp = requests.get(url)
    return resp.json()['value']


def get_usgs(l):
    siteid = l['name'].replace(' ', '')

    resp = requests.get(f'https://waterservices.usgs.gov/nwis/gwlevels/?format=json&sites={siteid}&siteStatus=all')



def do_crosswalk():
    ose_roswell_locations = get_ose_roswell_locations()
    n = len(ose_roswell_locations)
    print(f'examining {n} locations')
    with open('crosswalk.csv', 'w') as wfile:
        header = 'OSE-RoswellID,POD,OSE_ST_LOCATION_NAME,OSE_ST_LOCATION_ID,POTENTIAL\n'
        wfile.write(header)
        for i, l in enumerate(ose_roswell_locations):
            # pods = get_ose_pods_location(l)
            usgs = get_usgs(l)
            break
            if pods:
                for j, pod in enumerate(pods):
                    pod_location_name = pod['name']
                    pod_iotid = str(pod['@iot.id'])

                    thing = pod['Things'][0]
                    properties = thing['properties']
                    basin = properties['pod_basin']
                    num = properties['pod_number']

                    pod_id = f'{basin}-{num}'

                    row = ','.join([l['name'], pod_id, pod_location_name, pod_iotid, str(j)])
                    prefix = '' if not j else '   '
                    print(f"{prefix}{i}/{n}, {row}")
                    line = f'{row}\n'
                    wfile.write(line)
            else:
                row = ','.join([l['name'], '', '', '', ''])
                print(f'{i}/{n} {row}')
                line = f'{row}\n'
                wfile.write(line)
        # break


if __name__ == '__main__':
    do_crosswalk()

# ============= EOF =============================================
