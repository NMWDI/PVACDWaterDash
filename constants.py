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
ST2 = "https://st2.newmexicowaterdata.org/FROST-Server/v1.1"

DTFORMAT = "%Y-%m-%dT%H:%M:%S.000Z"
DEPTH_TO_WATER_FT_BGS = "Depth To Water (ft bgs)"
TITLE = "PVACD Groundwater Dashboard"

DEBUG_OBS = True
DEBUG_OBS = False
DEBUG_LIMIT_OBS = 0
DEBUG_N_WELLS = 0

MACROSTRAT_BM = {
    "below": "traces",
    "sourcetype": "raster",
    "sourceattribution": '&copy; <a href="https://macrostrat.org">MacroStrat</a> contributors',
    "source": ["http://tiles.macrostrat.org/carto/{z}/{x}/{y}.png"],
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

# ============= EOF =============================================
