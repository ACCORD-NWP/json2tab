"""Converter to generate wind turbine location files for The Netherlands.

Input data based on RIVM and RWS data.
"""

import os
from typing import Optional

import geopandas as gpd
import pandas as pd

from ...io.writers import save_dataframe
from ...location_converters.LocationMerger import (
    get_nearest_turbine,
    merge_dataframes,
    merge_turbine_data,
)
from ...logs import logger
from ...turbine_utils import datarow_to_turbine


def netherlands(
    rivm_input_filename: str,
    rws_input_filename: str,
    output_filename: Optional[str] = None,
):
    """Converter to generate wind turbine location files for The Netherlands."""
    if output_filename is None:
        input_filename_base = os.path.splitext(rivm_input_filename)[0]
        output_filename = f"{input_filename_base}.geojson"

    print(
        f"Netherlands Windturbine location shape Converter and Merger "
        f"(RIVM: {rivm_input_filename}, "
        f"RWS: {rws_input_filename} -> {output_filename})"
    )
    print(
        "  > RIVM Shape-file (for Windturbines - vermogen) can be downloaded from: "
        "https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/90f5eab6-9cea-4869-a031-2a228fb82fea"
    )
    print(
        "  > RWS Shape-file (for exact offshore locations) can be downloaded from: "
        "https://nationaalgeoregister.nl/geonetwork/srv/dut/catalog.search#/metadata/9b1b9185-5126-4dd9-90f6-4b5b1a061915"
    )

    logger.debug(f"RIVM input filename: {rivm_input_filename}")
    logger.debug(f"RWS  input filename: {rws_input_filename}")
    logger.debug(f"output filename: {output_filename}")

    rivm_data = gpd.read_file(rivm_input_filename)
    rws_data = gpd.read_file(rws_input_filename)

    # Project data to WGS84 coordinate system
    rivm_data.to_crs(crs="EPSG:4326", inplace=True)
    rws_data.to_crs(crs="EPSG:4326", inplace=True)

    logger.info(f"Loaded {len(rivm_data)} RIVM wind turbines")
    logger.info(f"Loaded {len(rws_data)} RWS wind turbine/data entries")

    # Filter RWS data to only (used) turbines
    used_turbines = (rws_data["opmerking"] == "Turbine") & (
        rws_data["status"] == "In gebruik"
    )
    rws_data_removed = rws_data[~used_turbines]
    rws_data = rws_data[used_turbines]

    logger.info(f"Filtered RWS data to {len(rws_data)} used wind turbines")

    rivm_data["source"] = "Netherlands (RIVM)"
    rws_data["source"] = "Netherlands (RWS)"

    merged_source_name = "Netherlands (RWS+RIVM)"
    (
        rws_rivm_common,
        rivm_unique,
        rws_unique,
        rivm_duplicate,
        rws_duplicate,
    ) = merge_dataframes(
        rivm_data,
        rws_data,
        tol=0.0015,
        preferred_source_df=rws_data,
        merged_source_name=merged_source_name,
    )
    logger.info(f"Found {len(rws_rivm_common)} common turbines in RIVM and RWS dataset")

    # Collect all rivm-unique turbines
    turbines_rivm_unique = []
    for _, row in rivm_unique.iterrows():
        turbines_rivm_unique.append(datarow_to_turbine(row))
    logger.info(
        f"Collected {len(turbines_rivm_unique)} unique turbines from RIVM dataset "
        f"with {len(rivm_unique.index)} entries"
    )

    # Collect all relevant rws-unique turbines
    turbines_rws_unique = []
    rivm_data_tree = None
    for _, row in rws_unique.iterrows():
        mask = (rws_data_removed["utm_x"] == row["utm_x"]) & (
            rws_data_removed["utm_y"] == row["utm_y"]
        )
        # Drop 'turbines' that are located on exactly the same location as
        # OSS, OHVS, monopile
        if not mask.any():
            turbine = datarow_to_turbine(row)

            if (
                turbine.diameter is None
                or turbine.hub_height is None
                or turbine.type is None
            ):
                logger.info(
                    f"Turbine {turbine.name} has poor properties, try to enrich it"
                )

                nearest_turbine, dist, rivm_data_tree = get_nearest_turbine(
                    rivm_data, turbine, tol=1, tree=rivm_data_tree
                )

                if nearest_turbine is not None:
                    turbine_enriched = merge_turbine_data(
                        row, nearest_turbine.iloc[0], merged_source_name=row["source"]
                    )
                    if (
                        turbine_enriched.is_offshore
                        and dist is not None
                        and dist < 10 * turbine_enriched.diameter
                    ):
                        # Enrich turbine with properties from nearest_turbine
                        # if it is in distance of 10*diameter
                        logger.info(
                            f"Enriched specs of {turbine.name} with a nearest turbine "
                            f"with distance "
                            f"{int(dist)}m < {int(10*turbine_enriched.diameter)}m"
                        )
                        turbine = turbine_enriched

            turbines_rws_unique.append(turbine)
        else:
            logger.info(
                f"Removed 'turbine' at location {row['geometry']}, "
                f"utm_x={row['utm_x']}, utm_y={row['utm_y']} "
                f"as it exactly is located on a removed item."
            )

    logger.info(
        f"Collected {len(turbines_rws_unique)} unique relevant turbines "
        f"from RWS dataset with {len(rws_unique.index)} entries"
    )

    # Combine lists of turbines
    all_turbines = rws_rivm_common + turbines_rivm_unique + turbines_rws_unique
    logger.info(f"Combined turbines to list with {len(all_turbines)} turbines")

    # Create a DataFrame to dump to csv and/or geojson
    data = pd.DataFrame(all_turbines)
    save_dataframe(data, output_filename)
    return data
