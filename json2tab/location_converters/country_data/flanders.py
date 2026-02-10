"""Converter to generate wind turbine location files for Flanders.

Input data based on stedenbouwkundig aangevraagde windturbines.
"""

import os
from typing import Optional

import geopandas as gpd
import pandas as pd

from ...io.writers import save_dataframe
from ...logs import logger
from ...turbine_utils import datarow_to_turbine
from ..short_distance_remover import cleanup_short_distance_turbines


def flanders(
    input_filename: str,
    output_filename: Optional[str] = None,
    min_distance: Optional[float] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Flanders."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.geojson"

    if min_distance is None:
        min_distance = 0.5e-3  # By default take min distance of ~50 meter for turbines

    print(
        f"Flanders Onshore Shape-file "
        "(a.k.a. stedenbouwkundig aangevraagde windturbines) Converter: "
        f"{input_filename} -> {output_filename} ("
        f"min_distance = {min_distance} (~"
        f"{int(111 * 1000 * min_distance) if min_distance is not None else None} meter)"
    )
    print(
        "  > Shape-file can be downloaded from: "
        "https://www.vlaanderen.be/datavindplaats/catalogus/stedenbouwkundig-aangevraagde-windturbines"
    )
    print("  > Note: dataset is Flanders ONLY.")

    logger.debug(f"input filename: {input_filename}")
    logger.debug(f"output filename: {output_filename}")

    data = gpd.read_file(input_filename)

    # Project data to WGS84 coordinate system
    data.to_crs(crs="EPSG:4326", inplace=True)

    logger.info(f"Loaded {len(data)} wind turbines")

    # Filter to only built turbines
    data = data[data["gebouwd"] == "ja"]

    # Set some static fields for this dataset
    data["source"] = "Flanders Onshore"
    data["country"] = "Belgium"
    data["is_offshore"] = False

    logger.info(f"Selected {len(data)} wind turbines that are built")

    turbines = []
    for _, row in data.iterrows():
        turbine = datarow_to_turbine(row)

        max_height = row["hoogte_max"]
        if max_height == 0:
            max_height = None

        if turbine.power_rating == 0:
            turbine.power_rating = None

        if turbine.hub_height == 0:
            turbine.hub_height = None

        if turbine.hub_height is not None and max_height is not None:
            turbine.radius = max_height - turbine.hub_height
            turbine.diameter = 2 * turbine.radius

        turbines.append(turbine)

    logger.info(f"Loaded {len(turbines)} turbines from {len(data.index)} data entries")

    data = pd.DataFrame(turbines)
    logger.info(f"Created dataframe with {len(data.index)} turbines")

    if min_distance > 0:
        data = cleanup_short_distance_turbines(data, dist=min_distance)
        logger.info(
            f"Filtered dataframe to {len(data.index)} turbines with "
            f"at least ~{int(111 * 1000 * min_distance)} meter "
            f"(i.e. {min_distance} degree) distance"
        )

    save_dataframe(data, output_filename)
    return data
