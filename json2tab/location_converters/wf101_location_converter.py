"""Converter to translate WF101 wind turbine data to csv/geojson file."""

import os
from typing import Optional

import pandas as pd

from ..io.readers import read_locationdata_from_txt_as_dataframe
from ..io.writers import save_dataframe


def wf101_location_converter(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Read and convert WF101 wind turbine data to csv/geojson file.

    Args:
        input_filename:  Input file to the WF101 data file
        output_filename: Output file for the csv/geojson file
        label_source:    Label for source field

    Returns:
        DataFrame with standardized WF101 turbine data
    """
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.geojson"

    print(f"WF101 Location Converter ({input_filename} -> {output_filename})")

    wf101_data = read_locationdata_from_txt_as_dataframe(input_filename)

    if wf101_data is not None:
        if label_source is not None:
            wf101_data["source"] = label_source

        save_dataframe(wf101_data, output_filename)

    return wf101_data
