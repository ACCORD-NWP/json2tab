"""Module containing the windturbine location file converter between csv and geojson."""

import os
from typing import Optional

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import generate_output_filename, save_dataframe
from ..logs import logger


def convert_between_csv_geojson(
    input_filename: str,
    output_filename: Optional[str] = None,
    rename_rules: Optional[str|dict] = None,
) -> pd.DataFrame:
    """Converter to convert windturbine location file between csv- and geojson-format.

    Args:
        input_filename:  csv or geojson file to windturbine location data from
        output_filename: (Optional) geojson or csv file to write turbine location data
        rename_rules     Rename rules to rename columns in read data

    Returns:
        pandas.DataFrame with csv file data
    """
    if output_filename is None:
        _, input_ext = os.path.splitext(input_filename)
        output_extension = "csv" if input_ext.lower().endswith("json") else "geojson"
        output_filename = generate_output_filename(input_filename, output_extension)

    try:
        data = read_locationdata_as_dataframe(input_filename, rename_rules=rename_rules)
        save_dataframe(data, output_filename)
        return data

    except Exception as e:
        logger.exception(
            f"Failed to convert {input_filename} -> {output_filename}: {e!s}"
        )
