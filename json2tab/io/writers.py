"""Module to write pandas dataframe with wind turbine location data to file."""

import os
from typing import List, Optional

import pandas as pd

from ..io.save_dataframe_as_csv import save_dataframe_as_csv
from ..io.save_dataframe_as_geojson import save_dataframe_as_geojson
from ..logs import logger


def generate_output_filename(input_filename: str, output_extension: str) -> str:
    """Generates filename based on filename and prefered output extension.

    Args:
        input_filename (str):   Filename to derive output filename from
        output_extension (str): Extension of the output file

    Returns:
        The generated output filename with the requested extension

    """
    input_filename_base, _ = os.path.splitext(input_filename)
    if not output_extension.startswith("."):
        output_extension = f".{output_extension}"
    output_filename = f"{input_filename_base}{output_extension}"
    return output_filename


def save_dataframe(
    dataframe: pd.DataFrame, filename: str, formats: Optional[str | List[str]] = None
) -> None:
    """Save dataframe to filename in given format.

    Args:
        dataframe (pandas.DataFrame): pandas.DataFrame to write
        filename (str):               Filename to write data
        formats (str or list[str]):   One or more formats to write dataframe

    """
    if formats is None:
        _, formats = os.path.splitext(filename)

    formats = parse_ext_string_to_list(formats)

    for ext in formats:
        output_filename = generate_output_filename(filename, ext)
        if ext.lower() in ["csv", ".csv"]:
            save_dataframe_as_csv(dataframe, output_filename)
        elif ext.lower() in ["json", ".json", "geojson", ".geojson"]:
            save_dataframe_as_geojson(dataframe, output_filename)
        else:
            logger.warning(
                f"Could not derive valid output format for extension {ext}. "
                "No file written."
            )


def parse_ext_string_to_list(formats: str) -> List[str]:
    """Parses extensions like .[csv,txt] as a list of extensions."""
    if formats.startswith(".[") and formats.endswith("]"):
        formats = formats[2:-1].split(",")

    if not isinstance(formats, list):
        formats = [formats]

    return formats
