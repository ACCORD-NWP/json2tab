"""Converter to generate wind turbine location files for Italy."""

import os
from typing import Optional

import pandas as pd

from ...io.writers import save_dataframe
from ...turbine_utils import datarow_to_turbine
from ...logs import logger


def italy(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Italy."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"Italy xlsx Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    data = pd.read_excel(input_filename, header=1, sheet_name="db")

    if "source" not in data:
        data["source"] = label_source

    turbines = []
    for _, row in data.iterrows():
        turbine = datarow_to_turbine(row)
        if (
            turbine.latitude == turbine.latitude
            and turbine.longitude == turbine.longitude
        ):
            turbines.append(turbine)

    data = pd.DataFrame(turbines)
    save_dataframe(data, output_filename)
    return data
