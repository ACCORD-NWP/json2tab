"""Module for distance based turbine to windfarm mapper."""

import math
import os
from typing import Optional

import pandas as pd
from scipy.spatial import KDTree

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.MergeStrategy import MergeStrategy
from ..logs import logger, logging
from ..turbine_utils import merge_turbine_data, standarize_dataframe
from .get_lat_lon_matrix import get_lat_lon_matrix


def turbine_windfarm_mapper(
    windfarm_file: str,
    turbine_file: str,
    output_file: str,
    merge_mode: Optional[MergeStrategy | str] = MergeStrategy.Combine,
    source_label: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
    max_distance: Optional[float] = None,
    dump_temp_files: Optional[bool] = None,
    merged_file=None,
    remaining_windfarm_file=None,
    remaining_turbine_file=None,
):
    """The distance based wind turbine to windfarm mapper."""
    if dump_temp_files is None:
        dump_temp_files = logger.getEffectiveLevel() <= logging.DEBUG

    if dump_temp_files:
        base_output = os.path.splitext(output_file)[0]
        if merged_file is None:
            merged_file = f"{base_output}.merged.csv"

        if remaining_windfarm_file is None:
            remaining_windfarm_file = f"{base_output}.remaining_windfarms.csv"

        if remaining_turbine_file is None:
            remaining_turbine_file = f"{base_output}.remaining_turbines.csv"

    if isinstance(merge_mode, str):
        merge_mode = MergeStrategy.from_string(merge_mode)

    if merge_mode is None:
        merge_mode = MergeStrategy.Combine

    print(
        f"Windturbine to windfarm mapper "
        f"{windfarm_file} (windfarms) + {turbine_file} (turbines) "
        f"-> {output_file}  (merge_mode = {merge_mode})"
    )

    if merged_file is not None:
        print(f"Merged turbines are written to {merged_file}")
    if remaining_windfarm_file is not None:
        print(
            f"Remaining windfarms from {windfarm_file} are "
            f"written to {remaining_windfarm_file}"
        )
    if remaining_turbine_file is not None:
        print(
            f"Remaining wind turbines from {turbine_file} are "
            f"written to {remaining_turbine_file}"
        )

    df_windfarms = read_locationdata_as_dataframe(
        windfarm_file, rename_rules=rename_rules
    )
    df_turbines = read_locationdata_as_dataframe(turbine_file, rename_rules=rename_rules)

    logger.info(
        f"Loaded {len(df_windfarms.index)} windfarms "
        f"with {int(sum(df_windfarms['n_turbines'].fillna(0)))} turbines "
        f"from {windfarm_file}"
    )
    logger.info(f"Loaded {len(df_turbines.index)} turbines from {turbine_file}")

    df_windfarms = standarize_dataframe(df_windfarms).dropna(axis="columns", how="all")
    df_turbines = standarize_dataframe(df_turbines)

    df_combined_turbines, turbines, df_windfarms, df_turbines = apply(
        df_windfarms,
        df_turbines,
        source_label=source_label,
        merge_mode=merge_mode,
        max_distance=max_distance,
        merged_file=merged_file,
        remaining_windfarm_file=remaining_windfarm_file,
        remaining_turbine_file=remaining_turbine_file,
    )

    logger.info(
        f"Merged dataframe contains {len(df_combined_turbines.index)} turbine lines."
    )
    save_dataframe(df_combined_turbines, output_file)


def apply(
    df_windfarms,
    df_turbines,
    source_label,
    max_distance=None,
    merge_mode=MergeStrategy.Combine,
    merged_file=None,
    remaining_windfarm_file=None,
    remaining_turbine_file=None,
):
    """Apply the actual windfarm to turbine mapping."""
    if max_distance is None:
        max_distance = 1e-1  # ~11km threshold

    logger.info(f"Max wf-wt distance={max_distance} ~{int(max_distance*111*100)/100}km")

    # Define some keys/values used for mapping
    tag_unmapped = len(df_windfarms.index)
    key_wf_idx = "windfarm_idx"
    key_wt_idx = "turbine_idx"
    key_wf_dist = "windfarm_dist"
    key_mapped = "mapped_turbines"
    key_n_wt = "n_turbines"

    df_windfarms[key_mapped] = 0
    df_windfarms[key_wf_idx] = df_windfarms.index.copy()
    df_turbines[key_wf_idx] = tag_unmapped
    df_turbines[key_wf_dist] = math.inf

    mapped_turbines = 0
    done = False
    while not done:
        sub_windfarms = df_windfarms[df_windfarms[key_mapped] < df_windfarms[key_n_wt]]
        sub_windfarms = sub_windfarms.reset_index(drop=True)
        tree = KDTree(get_lat_lon_matrix(sub_windfarms))

        sub_turbines = df_turbines[df_turbines[key_wf_idx] == tag_unmapped]
        distances, idxs = tree.query(
            get_lat_lon_matrix(sub_turbines), k=1, distance_upper_bound=max_distance
        )

        # Translate index subset of windfarms back to original windfarm index
        sel = idxs < len(sub_windfarms.index)
        idxs[sel] = sub_windfarms[key_wf_idx].iloc[idxs[sel]]
        idxs[~sel] = tag_unmapped

        df_turbines.loc[sub_turbines.index, key_wf_idx] = idxs
        df_turbines.loc[sub_turbines.index, key_wf_dist] = distances

        for _, windfarm in sub_windfarms.iterrows():
            idx = windfarm[key_wf_idx]
            name = windfarm["name"]
            count = int(windfarm[key_n_wt] or 0)
            mapped = df_turbines[df_turbines[key_wf_idx] == idx].sort_values(
                by=key_wf_dist
            )

            if len(mapped.index) > count:
                # Don't match turbines with longest distance to this windfarm
                df_turbines.loc[mapped.iloc[count:].index, key_wf_idx] = tag_unmapped

            len_mapped = min(len(mapped.index), count)
            df_windfarms.loc[idx, key_mapped] = len_mapped
            logger.debug(
                f"Windfarm '{name}' should have {count} wind turbines "
                f"({len_mapped} turbines mapped)"
            )

        old_mapped_turbines = mapped_turbines
        mapped_turbines = sum(df_windfarms[key_mapped])
        logger.info(f"Mapped {mapped_turbines} wind turbines to a windfarm")

        # Done if none of the selected turbines isn't rejected
        # due to overbooking to a windfarm
        done = old_mapped_turbines + sum(sel) == mapped_turbines

    # Inner join mapped wind turbines and windfarm info
    pure_wt_cols = {"id", "name", "latitude", "longitude", "is_offshore", "country"}
    pure_wf_cols = {key_n_wt, key_mapped}
    df_wf_turbines = df_turbines[
        list(set(df_turbines.columns) & (pure_wt_cols | {key_wf_idx}))
    ]
    df_wf_turbines[key_wt_idx] = df_wf_turbines.index.copy()

    df_wf_windfarms = df_windfarms[
        list(set(df_windfarms.columns) - pure_wt_cols - pure_wf_cols)
    ]

    df_wf_turbines = df_wf_turbines.merge(
        df_wf_windfarms, on=key_wf_idx, how="inner"
    ).dropna(axis=1, how="all")

    turbines = []
    for _, wf_turbine in df_wf_turbines.iterrows():
        idx = wf_turbine[key_wt_idx]
        orig_turbine = df_turbines.iloc[idx]

        map_source_label = (
            source_label or f"{wf_turbine['source']}+{orig_turbine['source']}"
        )
        merged_turbine = merge_turbine_data(wf_turbine, orig_turbine, map_source_label)
        turbines.append(merged_turbine)

    logger.info(f"Mapped {len(turbines)} turbines to a windfarm")

    wt_source = df_turbines["source"].iloc[0]
    df_turbines = df_turbines.drop(df_wf_turbines[key_wt_idx].to_list())
    logger.info(f"Remaining {len(df_turbines.index)} turbines not mapped to a windfarm")

    df_windfarms = df_windfarms.rename(columns={key_n_wt: "total_turbines"})
    df_windfarms[key_n_wt] = df_windfarms["total_turbines"] - df_windfarms[key_mapped]
    df_windfarms["source"] = df_windfarms["source"] + f"-({wt_source} turbines)"

    logger.info(
        f"Remaining {len(df_windfarms.index)} windfarms with "
        f"{int(sum(df_windfarms['n_turbines'].fillna(0)))} unmapped turbines"
    )

    if merged_file is not None:
        pd.DataFrame(turbines).to_csv(merged_file, index=False)

    if remaining_windfarm_file is not None:
        df_windfarms.to_csv(remaining_windfarm_file, index=False)

    if remaining_turbine_file is not None:
        df_turbines.to_csv(remaining_turbine_file, index=False)

    df_turbines = df_turbines.drop([key_wf_idx, key_wf_dist], axis=1)

    df_windfarms = df_windfarms.drop([key_wf_idx], axis=1)
    df_windfarms = df_windfarms[df_windfarms[key_n_wt] > 0]

    if merge_mode == MergeStrategy.Intersect:
        df_combined_turbines = pd.DataFrame(turbines)
    elif merge_mode == MergeStrategy.EnrichSet1:
        df_combined_turbines = pd.concat([pd.DataFrame(turbines), df_windfarms])
    elif merge_mode == MergeStrategy.EnrichSet2:
        df_combined_turbines = pd.concat([pd.DataFrame(turbines), df_turbines])
    elif merge_mode == MergeStrategy.Combine:
        df_combined_turbines = pd.concat(
            [pd.DataFrame(turbines), df_windfarms, df_turbines]
        )
    else:
        df_combined_turbines = pd.DataFrame()

    return df_combined_turbines, turbines, df_windfarms, df_turbines
