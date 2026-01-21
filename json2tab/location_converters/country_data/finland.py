"""Converter to generate wind turbine location files for Finland.

Input data based on Evgeny's finland wind fleet data.
"""

import json
import os
from typing import Optional

import pandas as pd

from ...io.writers import save_dataframe
from ...turbine_utils import datarow_to_turbine
from ...logs import logger


def finland(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Finland."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"Finland Json Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    with open(input_filename, "r") as input_file:
        data = json.load(input_file)

        elements = data["features"]

        turbines = []
        for element in elements:
            properties = element["properties"]

            if properties["status"] == "in operation":
                location = element["geometry"]
                lon, lat = location["coordinates"]

                turbine_id = properties["turbine id"]
                windfarm_id = properties["farm id"]

                properties["id"] = element["id"]
                properties["name"] = f"Turbine {windfarm_id}.{turbine_id}"
                properties["latitude"] = lat
                properties["longitude"] = lon
                properties["country"] = "Finland"
                if "source" not in properties:
                    properties["source"] = label_source

                turbines.append(datarow_to_turbine(properties))

        data = pd.DataFrame(turbines)
        save_dataframe(data, output_filename)
        return data
