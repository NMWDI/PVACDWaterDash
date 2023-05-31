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
chart_bgcolor = "white"

card_style = {
    "border": "solid",
    "borderRadius": "10px",
    "marginBlock": "3px",
    "backgroundColor": chart_bgcolor,
    "boxShadow": "2px 2px #8d9ea2",
    "borderColor": "7d777a",
}

lcol_style = card_style.copy()
rcol_style = card_style.copy()
lcol_style["marginRight"] = "5px"
COLOR_MAP = {
    "locations_no_aquifer": "orange",
    "locations_permian_aquifer_system": "blue",
    "locations_pecos_valley_alluvial_aquifer": "purple",
    "locations_high_mountain_aquifer_system": "black",
    "pvacd_hydrovu": "green",
}
header_style = {
    "font-family": "verdana",
    "font-weight": "bold",
    "fontSize": "10px",
    # "height": "50px"
}
data_style = {"fontSize": "10px", "font-family": "verdana"}
# ============= EOF =============================================
