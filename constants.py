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
import os

ST2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1"

DTFORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
DEPTH_TO_WATER_FT_BGS = "Depth To Water (ft bgs)"
TITLE = "PVACD Groundwater Dashboard"

DEBUG_OBS = True
DEBUG_OBS = False
DEBUG_LIMIT_OBS = 0
DEBUG_N_WELLS = int(os.environ.get("DEBUG_N_WELLS", 0))


MACROSTRAT_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": '&copy; <a href="https://macrostrat.org">MacroStrat</a> contributors',
    "source": ["https://tiles.macrostrat.org/carto/{z}/{x}/{y}.png"],
}

USGS_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": 'Tiles courtesy of the <a href="https://usgs.gov/">U.S. Geological Survey</a>',
    "source": [
        "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    ],
}

ESRI_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, "
    "GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    "source": [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    ],
}
OPENTOPO_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> '
    '(<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',
    "source": ["https://a.tile.opentopomap.org/{z}/{x}/{y}.png"],
}

OSM_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    "source": ["https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"],
}

# AQUIFER_FORMATION_MAP = {'300YESO': 'Yeso',
#                          '300YESO/000IRSV': 'Yeso',
#                          '313SADR': 'SanAndres'}

# AQUIFER_3DMODEL_MAP = {'Yeso': PERMIAN_AQUIFER_SYSTEM,
#                        'SanAndres': PERMIAN_AQUIFER_SYSTEM,
#                        'Alluvium': "Pecos Valley Alluvial Aquifer",
#                        'Artesia': "Artesia Group"}

PERMIAN_AQUIFER_SYSTEM = "Permian Aquifer System"
PECOS_VALLEY_ALLUVIAL_AQUIFER = "Pecos Valley Alluvial Aquifer"
ARTESIA_GROUP = "Artesia Group"
HIGH_PLAINS_AQUIFER_SYSTEM = "High Plains Aquifer System"
HIGH_MOUNTAIN_AQUIFER_SYSTEM = "High Mountain Aquifer System"


AQUIFER_PVACD_MAP = {
    PECOS_VALLEY_ALLUVIAL_AQUIFER: "Shallow",
    ARTESIA_GROUP: "Confining Unit",
    HIGH_PLAINS_AQUIFER_SYSTEM: "Plains",
    HIGH_MOUNTAIN_AQUIFER_SYSTEM: "Mountain",
    PERMIAN_AQUIFER_SYSTEM: "Artesian",
}

AQUIFER_3DMODEL_MAP = {
    "050QUAL": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "100ALVM": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110ALVM": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110AVMB": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110AVPS": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110AVTV": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110BLSN": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "110PTODC": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "111ALVM": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "112QTBFlac": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "112QTBFpd": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "112QTBFppm": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "120BLSN": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "180TKSCC_Upper": HIGH_MOUNTAIN_AQUIFER_SYSTEM,
    "211CRVC": HIGH_MOUNTAIN_AQUIFER_SYSTEM,
    "260SNAN": PERMIAN_AQUIFER_SYSTEM,
    "260SNAN_lower": PERMIAN_AQUIFER_SYSTEM,
    "261SNGL": PERMIAN_AQUIFER_SYSTEM,
    "300YESO": PERMIAN_AQUIFER_SYSTEM,
    "300YESO/000IRSV": PERMIAN_AQUIFER_SYSTEM,
    "300YESO_lower": PERMIAN_AQUIFER_SYSTEM,
    "300YESO_upper": PERMIAN_AQUIFER_SYSTEM,
    "310ABO": PERMIAN_AQUIFER_SYSTEM,
    "310GLOR": PERMIAN_AQUIFER_SYSTEM,
    "310MBLC": PERMIAN_AQUIFER_SYSTEM,
    "310SYDR": PERMIAN_AQUIFER_SYSTEM,
    "310TRRS": PERMIAN_AQUIFER_SYSTEM,
    "310YESO": PERMIAN_AQUIFER_SYSTEM,
    "310YESOG": PERMIAN_AQUIFER_SYSTEM,
    "313ARTS": ARTESIA_GROUP,
    "313BRNL": ARTESIA_GROUP,
    "313GRBG": ARTESIA_GROUP,
    "313QUEN": PERMIAN_AQUIFER_SYSTEM,
    "313SADG": PERMIAN_AQUIFER_SYSTEM,
    "313SADR": PERMIAN_AQUIFER_SYSTEM,
    "313SADRL": PERMIAN_AQUIFER_SYSTEM,
    "313SADRU": PERMIAN_AQUIFER_SYSTEM,
    "313SADY": PERMIAN_AQUIFER_SYSTEM,
    "313SVRV": ARTESIA_GROUP,
    "313TNSL": ARTESIA_GROUP,
    "313YATS": ARTESIA_GROUP,
    "315YESOABO": PERMIAN_AQUIFER_SYSTEM,
    "317ABYS": PERMIAN_AQUIFER_SYSTEM,
    "318ABO": PERMIAN_AQUIFER_SYSTEM,
    "318ABOL": PERMIAN_AQUIFER_SYSTEM,
    "318ABOU": PERMIAN_AQUIFER_SYSTEM,
    "318JOYT": PERMIAN_AQUIFER_SYSTEM,
    "318YESO": PERMIAN_AQUIFER_SYSTEM,
    "Alluvium": PECOS_VALLEY_ALLUVIAL_AQUIFER,
    "Ogallala": HIGH_PLAINS_AQUIFER_SYSTEM,
    "SierraBlanca": HIGH_MOUNTAIN_AQUIFER_SYSTEM,
    "UCretaceous": HIGH_MOUNTAIN_AQUIFER_SYSTEM,
    "LCretaceous": HIGH_PLAINS_AQUIFER_SYSTEM,
    "UDockum": HIGH_PLAINS_AQUIFER_SYSTEM,
    "LDockum (NW)": HIGH_MOUNTAIN_AQUIFER_SYSTEM,
    "LDockum (NE)": HIGH_PLAINS_AQUIFER_SYSTEM,
    "UOchoan": HIGH_PLAINS_AQUIFER_SYSTEM,
    "LOchoan": HIGH_PLAINS_AQUIFER_SYSTEM,
    "Artesia": ARTESIA_GROUP,
    "SanAndres": PERMIAN_AQUIFER_SYSTEM,
    "Yeso": PERMIAN_AQUIFER_SYSTEM,
}
# ============= EOF =============================================
