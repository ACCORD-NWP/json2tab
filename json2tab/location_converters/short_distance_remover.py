"""Module with remover to remove wind turbines with short distance."""

import os
import shutil
from typing import List, Optional, Tuple

import pandas as pd
from scipy.spatial import KDTree

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.get_lat_lon_matrix import get_lat_lon_matrix
from ..logs import logger
from ..turbine_utils import merge_turbine_data


def short_distance_remover(
    input_filename: str,
    output_filename: Optional[str] = None,
    min_distance: Optional[float] = None,
):
    """Remover to remove wind turbine locations with short distance.

    Args:
        input_filename (str):  Input filename to process
        output_filename (str): (Optional) Output filename to write data to
        min_distance (float):  (Optional) Minimal required distance between turbines

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

    print(
        f"Short Distance Remover ({input_filename} -> {output_filename}) with "
        f"min_distance = {min_distance} (~"
        f"{int(111 * 1000 * min_distance) if min_distance is not None else None} "
        f"meter)"
    )
    logger.debug(f"input filename: {backup_input_filename or input_filename}")
    logger.debug(f"output filename: {output_filename}")

    df_input = read_locationdata_as_dataframe(input_filename)
    df_merged_output = cleanup_short_distance_turbines(df_input, min_distance)

    save_dataframe(df_merged_output, output_filename)


def cleanup_short_distance_turbines(data: pd.DataFrame, dist: Optional[float] = None):
    """Merge turbines with a short distance to each orther.

    Args:
        data: DataFrame containing wind turbine data
        dist: Minimal distance between turbines (in degrees); default: 1.5e-3 ~ 150m

    Returns:
        merged_data: Merged filtered data with only turbines with distance >= dist

    """
    if dist is None:
        dist = 1.5e-3  # ~150m threshold

    restart = True
    while restart:
        df_unique, duplicate_data, min_dist = split_long_short_distance_turbines(
            data, dist=dist
        )
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
            data = df_merged_output
            logger.debug(
                "Duplicates found, so restart search for duplicates again to find cycles"
            )
        else:
            restart = False

    return df_merged_output


def split_long_short_distance_turbines(
    data: pd.DataFrame, dist: float
) -> Tuple[pd.DataFrame, float, List[Tuple[int, int]]]:
    """Split turbines to set of long and short distance turbines.

    Args:
        data: DataFrame containing wind turbine data
        dist: Minimal distance between turbines (in degrees); default: 1e-3 ~ 100m

    Returns:
        filtered_data:     Filtered data with only the turbines with distance >= dist
        duplicate_data:    List of duplicate rows in dataset
        min_dist:          Minimal distance between turbines in filtered data set

    """
    tree = KDTree(get_lat_lon_matrix(data))

    distances, idx = tree.query(
        get_lat_lon_matrix(data),
        k=2,
        # distance_upper_bound=dist
    )

    duplicate_pairs = {
        tuple(sorted(idx))
        for (idx, pair_dist) in zip(idx, distances[:, 1])
        if pair_dist < dist
    }
    duplicate_data = [
        (data.iloc[idx1], data.iloc[idx2]) for (idx1, idx2) in duplicate_pairs
    ]

    # Get rid of self-match
    distances = distances[:, 1]
    selector = distances >= dist

    if selector.any():
        mindist = min(distances[selector])
        return data[selector], duplicate_data, mindist

    return data, duplicate_data, None
