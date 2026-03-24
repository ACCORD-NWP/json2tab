"""Module to write pandas dataframe with wind turbine locations as csv."""

import os

import pandas as pd

from ..logs import logger


def save_dataframe_as_csv(
    data: pd.DataFrame, output_file: str = "wind_turbines.csv"
) -> None:
    """Save dataframe with wind turbine location data as a CSV file.

    Args:
        data (pandas.DataFrame): DataFrame containing wind turbine data
        output_file (str):       Path for the output CSV file

    Raises:
        Exception: when writing data is failed
    """
    try:
        logger.info("Writing data to CSV file...")
        data.to_csv(output_file, index=False)

        # Log success and file size
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # Convert to MB
        logger.info(
            f"Successfully saved CSV file to {output_file} "
            f"(File size: {file_size:.2f} MB)"
        )

    except Exception as e:
        logger.error(f"Error saving CSV file: {e}")
        raise e
