"""Converter to generate wind turbine location files for Sweden.

Input data based on Lansstyrelsen.
"""

import os
from typing import Optional

import geopandas as gpd
import pandas as pd

from ...io.writers import save_dataframe
from ...turbine_utils import datarow_to_turbine
from ...logs import logger


def sweden(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Sweden."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"Sweden Xlsx Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    data = pd.read_excel(input_filename, sheet_name="Land - Vindkraftverk")

    if "source" not in data:
        data["source"] = label_source

    if "country" not in data:
        data["country"] = "Sweden"

    x = data["E-Koordinat"].to_numpy().tolist()
    y = data["N-Koordinat"].to_numpy().tolist()

    geometry = gpd.points_from_xy(x, y, crs="EPSG:3006")
    geo_data = gpd.GeoDataFrame(data, geometry=geometry)

    # Project data to WGS84 coordinate system
    geo_data.to_crs(crs="EPSG:4326", inplace=True)

    logger.debug(f"Loaded {len(geo_data.index)} turbines")

    geo_data = geo_data[(geo_data["Status"] == "Nedmonterat") | 
                        (geo_data["Status"] == "Uppfört") | 
                        (~pd.isnull(geo_data["Uppfört"]))]

    logger.debug(f"Loaded {len(geo_data.index)} real turbines")

    turbines = []
    for _, row in geo_data.iterrows():
        turbine = datarow_to_turbine(row)
        if (
            turbine.latitude == turbine.latitude
            and turbine.longitude == turbine.longitude
        ):
            turbines.append(turbine)

    data = pd.DataFrame(turbines)
    save_dataframe(data, output_filename)
    return data
