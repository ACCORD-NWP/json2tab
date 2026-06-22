"""Module containing the windturbine location file converter from csv to csv."""

from typing import Optional

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import generate_output_filename, save_dataframe
from ..logs import logger
from ..turbine_utils import standarize_dataframe


def csv_to_csv(
    input_filename: str,
    output_filename: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
    write_rules: Optional[str | dict] = None,
    filter_rules: Optional[str | dict] = None,
) -> pd.DataFrame:
    """Converter to convert windturbine location file from csv-format to csv-format.

    Args:
        input_filename:  csv-filename to windturbine location data from
        output_filename: (Optional) csv-filename to write windturbine location data
        rename_rules:    Rename rules to rename columns in read data
        write_rules:     Write rules to (conditional) write columns in read data
        filter_rules:    Filter rules to filter columns based on value

    Returns:
        pandas.DataFrame with the written csv-file

    Raises:
        Exception: when convertion is failed
    """
    if output_filename is None:
        output_filename = generate_output_filename(input_filename, "csv")

    try:
        data = read_locationdata_as_dataframe(
            input_filename,
            ext="csv",
            rename_rules=rename_rules,
            write_rules=write_rules,
            filter_rules=filter_rules,
        )

        # Convert read data rows to interpret the rows as standarized turbines
        data = standarize_dataframe(data)

        save_dataframe(data, output_filename)
        return data
    except Exception as e:
        logger.exception(
            f"Failed to convert {input_filename} -> {output_filename}: {e!s}"
        )
        raise e
