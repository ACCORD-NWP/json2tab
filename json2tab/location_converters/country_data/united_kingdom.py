"""Converter to generate wind turbine location files for United Kingdom."""

import math
import os
from typing import Optional

import geopandas as gpd
import pandas as pd

from ...io.writers import save_dataframe
from ...logs import logger
from ...turbine_utils import datarow_to_turbine


def united_kingdom(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for United Kingdom."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"United Kingdom xlsx Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    data = pd.read_excel(input_filename, sheet_name="REPD")

    # Filter to only windfarms
    data = data[
        (data["Technology Type"] == "Wind Offshore")
        | (data["Technology Type"] == "Wind Onshore")
    ]

    # Filter to only operational and decommissioned windfarms
    data = data[
        (data["Development Status"] == "Operational")
        | (data["Development Status"] == "Decommissioned")
    ]

    if "source" not in data:
        data["source"] = label_source

    x = data["X-coordinate"].to_numpy().tolist()
    y = data["Y-coordinate"].to_numpy().tolist()

    # Derive is_offshore field from Technology Type
    data["is_offshore"] = data["Technology Type"] == "Wind Offshore"

    geometry = gpd.points_from_xy(x, y, crs="EPSG:27700")
    geo_data = gpd.GeoDataFrame(data, geometry=geometry)

    # Project data to WGS84 coordinate system
    geo_data.to_crs(crs="EPSG:4326", inplace=True)

    logger.debug(f"Loaded {len(geo_data.index)} turbines")

    renames = {
        "Operator (or Applicant)": "operator",
        "Site Name": "name",
        "Installed Capacity (MWelec)": "Installed capacity [MW]",
        "Turbine Capacity": "rated_power_mw",
        "No. of Turbines": "n_turbines",
        "Height of Turbines (m)": "hub_height",
        "Operational": "start_date",
        "Ref ID": "turbine_id",
        "Record Last Updated (dd/mm/yyyy)": "end_date",
    }
    geo_data = geo_data.rename(columns=renames)

    geo_data.loc[geo_data["Development Status"] == "Operational", "end_date"] = None

    turbines = []
    for _, row in geo_data.iterrows():
        turbine = datarow_to_turbine(row)
        if (
            turbine.latitude == turbine.latitude
            and turbine.longitude == turbine.longitude
            and not math.isinf(turbine.latitude)
            and not math.isinf(turbine.longitude)
        ):
            turbines.append(turbine)

    data = pd.DataFrame(turbines)
    save_dataframe(data, output_filename)
    return data
