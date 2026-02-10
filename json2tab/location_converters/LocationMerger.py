"""Module for advanched wind turbine location merger."""

import os
import time
from typing import List, Optional, Tuple

import pandas as pd
from scipy.spatial import KDTree

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.get_lat_lon_matrix import get_lat_lon_matrix
from ..location_converters.MergeStrategy import MergeStrategy
from ..location_converters.MixStrategy import MixStrategy
from ..logs import logger, logging
from ..Turbine import Turbine
from ..turbine_utils import datarow_to_turbine, merge_turbine_data


def location_merger(
    file1: str,
    file2: str,
    output_file: str,
    merge_mode: Optional[MergeStrategy | str] = MergeStrategy.Combine,
    label_source1: Optional[str] = None,
    label_source2: Optional[str] = None,
    min_distance: Optional[float] = None,
    dump_temp_files: Optional[bool] = None,
    unique_file1=None,
    unique_file2=None,
    common_file1=None,
    common_file2=None,
    merged_file=None,
):
    """The advanched wind turbine location merger."""
    if dump_temp_files is None:
        dump_temp_files = logger.getEffectiveLevel() <= logging.DEBUG

    if dump_temp_files:
        base_output = os.path.splitext(output_file)[0]
        if merged_file is None:
            merged_file = f"{base_output}.merged.csv"

        if unique_file1 is None:
            unique_file1 = f"{base_output}.unique_file1.csv"

        if unique_file2 is None:
            unique_file2 = f"{base_output}.unique_file2.csv"

        if common_file1 is None:
            common_file1 = f"{base_output}.common_file1.csv"

        if common_file2 is None:
            common_file2 = f"{base_output}.common_file2.csv"

    if isinstance(merge_mode, str):
        merge_mode = MergeStrategy.from_string(merge_mode)

    if merge_mode is None:
        merge_mode = MergeStrategy.Combine

    print(
        f"Windturbine location merger; "
        f"{file1} + {file2} -> {output_file} (merge_mode = {merge_mode}, "
        f"min_distance = {min_distance} (~"
        f"{int(111 * 1000 * min_distance) if min_distance is not None else None} meter)"
    )
    if unique_file1 is not None:
        print(f"Unique turbines in {file1} are written to {unique_file1}")
    if unique_file2 is not None:
        print(f"Unique turbines in {file2} are written to {unique_file2}")
    if common_file1 is not None:
        print(f"Common turbines in {file1} are written to {common_file1}")
    if common_file2 is not None:
        print(f"Common turbines in {file2} are written to {common_file2}")
    if merged_file is not None:
        print(f"Merged turbines are written to {merged_file}")

    df_file1 = read_locationdata_as_dataframe(file1)
    df_file2 = read_locationdata_as_dataframe(file2)

    ignored_labels = [None, "", "NA", "N/A", "n/a", "-"]
    if label_source1 not in ignored_labels:
        df_file1["source"] = label_source1
        logger.info(f"Set source-field for {file1} to '{label_source1}'")

    if label_source2 not in ignored_labels:
        df_file2["source"] = label_source2
        logger.info(f"Set source-field for {file2} to '{label_source2}'")

    (
        merged_turbines,
        df_file1_unique,
        df_file2_unique,
        df_file1_duplicate,
        df_file2_duplicate,
    ) = merge_dataframes(
        df_file1,
        df_file2,
        tol=min_distance,
        mix_strategy=MixStrategy.from_merge_strategy(merge_mode),
    )

    if merged_file is not None:
        pd.DataFrame(merged_turbines).to_csv(merged_file, index=False)

    if unique_file1 is not None and df_file1_unique is not None:
        df_file1_unique.to_csv(unique_file1, index=False)

    if unique_file2 is not None and df_file2_unique is not None:
        df_file2_unique.to_csv(unique_file2, index=False)

    if common_file1 is not None and df_file1_duplicate is not None:
        df_file1_duplicate.to_csv(common_file1, index=False)

    if common_file2 is not None and df_file2_duplicate is not None:
        df_file2_duplicate.to_csv(common_file2, index=False)

    # Write combined data
    file1_unique = []
    file2_unique = []

    turbine_keys = set(Turbine().to_dict().keys())

    if (
        df_file1_unique is not None
        and len(set(df_file1_unique.columns) - turbine_keys) > 0
    ):
        file1_unique = df_file1_unique.apply(datarow_to_turbine, axis=1).to_list()
        df_file1_unique = None

    if (
        df_file2_unique is not None
        and len(set(df_file2_unique.columns) - turbine_keys) > 0
    ):
        file2_unique = df_file2_unique.apply(datarow_to_turbine, axis=1).to_list()
        df_file2_unique = None

    unique1 = len(file1_unique) + (
        len(df_file1_unique.index) if df_file1_unique is not None else 0
    )
    unique2 = len(file2_unique) + (
        len(df_file2_unique.index) if df_file2_unique is not None else 0
    )
    logger.info(f"Collecting {unique1} unique turbines from {file1}")
    logger.info(f"Collecting {unique2} unique turbines from {file2}")
    logger.info(
        f"Collecting {len(merged_turbines)} merged turbines from {file1} and {file2}"
    )

    if merge_mode in [MergeStrategy.EnrichSet1, MergeStrategy.Intersect]:
        file2_unique = []
        df_file2_unique = None

    if merge_mode in [MergeStrategy.EnrichSet2, MergeStrategy.Intersect]:
        file1_unique = []
        df_file1_unique = None

    combined_turbines = file1_unique + file2_unique + merged_turbines
    df_combined_turbines = pd.concat(
        [df_file1_unique, df_file2_unique, pd.DataFrame(combined_turbines)]
    )

    logger.info(f"Merged dataframe contains {len(df_combined_turbines.index)} turbines.")
    save_dataframe(df_combined_turbines, output_file)


def merge_dataframes(
    df_file1: pd.DataFrame,
    df_file2: pd.DataFrame,
    tol: Optional[float] = None,
    preferred_source_df: Optional[pd.DataFrame] = None,
    merged_source_name: Optional[str] = None,
    mix_strategy: Optional[MixStrategy | str] = MixStrategy.MultiMerge,
) -> Tuple[List[Turbine], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Merge wind turbine locations from different pandas.DataFrames."""
    start_time = time.time()
    tree = KDTree(get_lat_lon_matrix(df_file1))

    # Set tolerance for distance between turbines
    if tol is None:
        tol = 1.5e-3  # ~150m threshold

    if isinstance(mix_strategy, str):
        mix_strategy = MixStrategy.from_string(mix_strategy)

    if mix_strategy is None:
        mix_strategy = MixStrategy.MultiMerge

    distances, idx = tree.query(
        get_lat_lon_matrix(df_file2), k=1, distance_upper_bound=tol
    )

    overlapping = distances < tol

    logger.info(
        f"Compare wind turbine locations based on tol={tol} degree "
        f"(~<{int(111*1000 * tol)} meter)."
    )

    overlapping = distances < tol

    if overlapping.any():
        df_file1_duplicate = df_file1.iloc[list(set(idx[overlapping]))]
        df_file2_duplicate = df_file2[overlapping]
        df_file1_unique = df_file1.drop(df_file1_duplicate.index.array)
        df_file2_unique = df_file2.drop(df_file2_duplicate.index.array)
        logger.info(
            f"Loaded {len(df_file1_duplicate.index)} turbines from set1 with "
            f"{len(df_file2_duplicate.index)} duplicate turbines in set2"
        )

        idx_file1 = idx[overlapping]
        idx_file2 = df_file2_duplicate.index.to_list()
        distances = distances[overlapping]
    else:
        df_file1_duplicate = None
        df_file2_duplicate = None
        df_file1_unique = df_file1
        df_file2_unique = df_file2

    logger.info(f"Loaded {len(df_file1_unique.index)} unique turbines from set1")
    logger.info(f"Loaded {len(df_file2_unique.index)} unique turbines from set2")

    merged_turbines = []

    if overlapping.any():
        for idx1, row1 in df_file1_duplicate.iterrows():
            idx2_dist = sorted(
                [
                    (idx_file2[i], distances[i])
                    for i, x in enumerate(idx_file1)
                    if x == idx1
                ],
                key=lambda x: x[1],
            )

            if len(idx2_dist) > 1 and mix_strategy == MixStrategy.MultiMerge:
                merged_alternative = None
                for idx2, _ in idx2_dist:
                    row2 = df_file2_duplicate.loc[idx2]
                    if merged_alternative is not None:
                        merged_alternative = merge_turbine_data(
                            merged_alternative, row2
                        ).to_dict()
                    else:
                        merged_alternative = row2

                merged_turbine = merge_turbine_data(
                    row1, merged_alternative, merged_source_name
                )

                merged_turbines.append(merged_turbine)
            elif len(idx2_dist) > 1 and mix_strategy == MixStrategy.Crash:
                msg = "Found not a 1:1 relation between turbines from different sources."
                logger.error(msg)
                logger.error(
                    f"Turbine {row1.to_dict()} is mapped to the following turbines:"
                )
                for idx2, dist in idx2_dist:
                    row2 = df_file2_duplicate.loc[idx2]
                    logger.error(f"- {row2.to_dict()} (distance: {dist})")

                raise Exception(msg)
            else:
                for idx2, _ in idx2_dist:
                    row2 = df_file2_duplicate.loc[idx2]

                    if preferred_source_df is df_file1 or len(idx2_dist) > 1:
                        preferred_source, alternative_source = row1, row2
                    elif preferred_source_df is df_file2:
                        preferred_source, alternative_source = row2, row1
                    else:
                        preferred_source, alternative_source = select_richest_source(
                            row1, row2
                        )

                        if (
                            alternative_source.get("manufacturer") is not None
                            and alternative_source.get("type") is not None
                            and preferred_source.get("manufacturer") is None
                        ):
                            # Swap perf./alt. source if manufacturer+type seems richer
                            preferred_source, alternative_source = (
                                alternative_source,
                                preferred_source,
                            )

                    merged_turbine = merge_turbine_data(
                        preferred_source, alternative_source, merged_source_name
                    )

                    merged_turbines.append(merged_turbine)

                    if mix_strategy == MixStrategy.SkipRemainder:
                        break
    else:
        logger.info("No duplicates found")

    logger.info(f"Merging datasets took {time.time() - start_time} seconds")

    return (
        merged_turbines,
        df_file1_unique,
        df_file2_unique,
        df_file1_duplicate,
        df_file2_duplicate,
    )


def select_richest_source(row1, row2):
    """Select richest source for as preffered source for merging."""
    merged_cols = [
        "geometry",
        "latitude",
        "longitude",
        "lat",
        "lon",
        "x",
        "y",
        "utm_x",
        "utm_y",
        "name",
        "naam",
        "turbine_nr",
        "manufacturer",
        "type",
        "wt_type",
        "wf101_type",
        "hubheight",
        "hub_height",
        "height",
        "ash",
        "radius",
        "radius (m)",
        "diameter",
        "diameter (m)",
        "rotor_diameter",
        "diam",
        "rated_power",
        "power",
        "power_rating",
        "kw",
        "source",
    ]

    if count_none_fields(row1, merged_cols) > count_none_fields(row2, merged_cols):
        preferred_source, alternative_source = row2, row1
    else:
        preferred_source, alternative_source = row1, row2

    return preferred_source, alternative_source


def get_nearest_turbine(
    df_file1: pd.DataFrame, turbine: Turbine, tol: float, tree: Optional[KDTree] = None
):
    """Get wind turbine closest to a given turbine.

    Args:
        df_file1 (pd.DataFrame): Dataframe with wind turbine locations
        turbine (Turbine):       Turbine for which closest turbine should be found
        tol (float):             Distance upper bound for nearest turbine
        tree (KDTree):           (Optional) KDTree of [lat, lon] matrix of df_file1

    Returns:
        row:  Row of wind turbine with shortest distance (or None)
        dist: Distance between turbines
        tree: KDTree of [lat, lon] matrix of df_file1


    """
    if tree is None:
        tree = KDTree(get_lat_lon_matrix(df_file1))

    distances, idx = tree.query(
        [[turbine.latitude, turbine.longitude]], k=1, distance_upper_bound=tol
    )

    match = (distances < tol) & (distances == min(distances))

    if match.any():
        matched_turbine = df_file1.iloc[idx[match]]
        try:
            import geopy.distance

            lat_lon = get_lat_lon_matrix(matched_turbine)

            coords_1 = (turbine.latitude, turbine.longitude)
            coords_2 = (lat_lon[0][0], lat_lon[0][1])

            dist = geopy.distance.geodesic(coords_1, coords_2).m
        except Exception as e:
            logger.exception(
                f"Failed to compute distance between " f"requested point and match: {e!s}"
            )
            dist = None
        return df_file1.iloc[idx[match]], dist, tree

    return None, dist, tree


def count_none_fields(row, fields_to_check):
    """Count number of none-fields in row."""
    ignored_values = [None, "", 0, "NaN"]

    if row is None:
        return len(fields_to_check) + 1

    nr_of_nones = 0
    for field in fields_to_check:
        if row.get(field) in ignored_values:
            nr_of_nones += 1

    return nr_of_nones
