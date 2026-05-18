"""Module containing the windturbine location file converter from csv to csv."""

from typing import Optional

import pandas as pd

from ..io.readers import parse_rules, read_locationdata_from_csv_as_dataframe
from ..io.writers import generate_output_filename, save_dataframe
from ..logs import logger
from ..turbine_utils import standarize_dataframe


def csv_to_csv(
    input_filename: str,
    output_filename: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
    write_columns: Optional[str | dict] = None,
) -> pd.DataFrame:
    """Converter to convert windturbine location file from csv-format to csv-format.

    Args:
        input_filename:  csv-filename to windturbine location data from
        output_filename: (Optional) csv-filename to write windturbine location data
        rename_rules:    Rename rules to rename columns in read data
        write_columns:   Column name and values to write in read data

    Returns:
        pandas.DataFrame with the written csv-file

    Raises:
        Exception: when convertion is failed
    """
    if output_filename is None:
        output_filename = generate_output_filename(input_filename, "csv")

    try:
        data = read_locationdata_from_csv_as_dataframe(input_filename)

        # Apply rename rules
        if rename_rules is not None:
            data = data.rename(columns=parse_rules(rename_rules))

        if write_columns is not None:
            for key, val in parse_rules(write_columns).items():
                val_dict = val if isinstance(val, dict) else {None: val}

                for old_value, new_value in val_dict.items():
                    if old_value is not None:
                        data.loc[data[key] == old_value, key] = new_value
                        logger.info(f"Translate data[{key}] {old_value} to {new_value}")
                    else:
                        logger.info(f"Write data[{key}] = {new_value}")
                        data[key] = new_value

        # Convert read data rows to interpret the rows as standarized turbines
        data = standarize_dataframe(data)

        save_dataframe(data, output_filename)
        return data
    except Exception as e:
        logger.exception(
            f"Failed to convert {input_filename} -> {output_filename}: {e!s}"
        )
        raise e
