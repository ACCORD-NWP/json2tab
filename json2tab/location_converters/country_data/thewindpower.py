"""Converter to generate windfarm location file from TheWindPower.net data."""

import os
from typing import Optional

import pandas as pd

from ...io.writers import save_dataframe
from ...location_converters.LocationMerger import datarow_to_turbine
from ...logs import logger
from ...io.readers import parse_rename_rules

def thewindpower(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
    rename_rules: Optional[str|dict] = None
) -> pd.DataFrame:
    """Converter to generate windfarm location file from TheWindPower.net data."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"TheWindPower.net Windfarm Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    data = pd.read_excel(input_filename, header=[0, 1], sheet_name="Windfarms", na_values="#ND")

    data.columns = data.columns.droplevel(1)
    data.columns = data.columns.str.strip()

    # Apply rename rules
    data = data.rename(columns=parse_rename_rules(rename_rules))

    data = data[(data["Status"] == "Production") | 
                ((data["Status"] == "Dismantled") & ~pd.isnull(data["Decommissioning date"]))]

    if "source" not in data:
        data["source"] = label_source

    windfarms = []
    for _, row in data.iterrows():
        windfarm = datarow_to_turbine(row)
        if (
            windfarm.latitude == windfarm.latitude
            and windfarm.longitude == windfarm.longitude
        ):
            windfarms.append(windfarm)

    data = pd.DataFrame(windfarms)
    save_dataframe(data, output_filename)
    return data
