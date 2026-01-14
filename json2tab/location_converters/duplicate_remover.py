"""Module with Duplicate remover to remove wind turbines with short distance."""

import os
import shutil
from typing import Optional

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.LocationMerger import merge_turbine_data
from ..logs import logger
from .cleanup_short_distance_turbines import cleanup_short_distance_turbines


def duplicate_remover(input_filename: str, output_filename: Optional[str] = None):
    """Duplicate remover to remove wind turbine locations with short distance.

    Args:
        input_filename (str):  Input filename to process
        output_filename (str): (Optional) Output filename to write data to

    """
    if output_filename is None:
        input_filename_base, input_filename_ext = os.path.splitext(input_filename)
        backup_input_filename = f"{input_filename_base}{input_filename_ext}.orig"

        shutil.copyfile(input_filename, backup_input_filename)
        logger.info(
            f"Copied original input-file {input_filename} to "
            f"{backup_input_filename}, set output-file to {input_filename}"
        )
        output_filename = input_filename
    else:
        backup_input_filename = None

    print(f"Duplicate Remover ({input_filename} -> {output_filename})")
    logger.debug(f"input filename: {backup_input_filename or input_filename}")
    logger.debug(f"output filename: {output_filename}")

    df_input = read_locationdata_as_dataframe(input_filename)
    logger.info(f"Loaded {len(df_input.index)} turbines from {input_filename}")

    restart = True
    while restart:
        df_unique, min_dist, duplicate_data = cleanup_short_distance_turbines(df_input)
        logger.info(
            f"Filtered dataframe to {len(df_unique.index)} turbines "
            f"with at least ~{int(111 * 1000 * min_dist)} meter "
            f"(i.e. {min_dist} degree) distance"
        )

        merged_duplicate_turbines = []
        for row1, row2 in duplicate_data:
            duplicate_turbine = merge_turbine_data(row1, row2, row1["source"])
            merged_duplicate_turbines.append(duplicate_turbine)
        logger.info(
            f"Selected {len(merged_duplicate_turbines)} duplicate/merged turbines"
        )

        df_duplicate = pd.DataFrame(merged_duplicate_turbines)
        df_merged_output = pd.concat([df_unique, df_duplicate], ignore_index=True)

        if len(merged_duplicate_turbines) > 0:
            df_input = df_merged_output
            logger.debug(
                "Duplicates found, so restart search for duplicates again to find cycles"
            )
        else:
            restart = False

    save_dataframe(df_merged_output, output_filename)
