"""Module for geometry or distance based turbine to windfarm mapper."""

import math
import os
from typing import Literal, Optional

import pandas as pd
from scipy.spatial import KDTree
from shapely.geometry import Point

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.MergeStrategy import MergeStrategy
from ..logs import logger, logging
from ..turbine_utils import merge_turbine_data, standarize_dataframe
from ..utils import print_processing_status
from .get_lat_lon_matrix import get_lat_lon_matrix, get_lon_lat


class TurbineWindfarmMapper:
    """Geometry or distance based turbine to windfarm mapper."""

    key_wf_idx = "windfarm_idx"
    key_wt_idx = "turbine_idx"
    key_wf_dist = "windfarm_dist"
    key_mapped = "mapped_turbines"
    key_n_wt = "n_turbines"
    tag_unmapped = None

    merged_file = None
    remaining_windfarm_file = None
    remaining_turbine_file = None

    def __init__(self, dump_temp_files: Optional[bool] = None):
        """Initialize turbine windfarm mapper.

        Args:
            config (dict): Configuration dictionary
            dump_temp_files (bool): Optional flag indicating if temp files should saved
        """
        if dump_temp_files is None:
            self.dump_temp_files = logger.getEffectiveLevel() <= logging.DEBUG
        else:
            self.dump_temp_files = dump_temp_files

    def map_files(
        self,
        scheme: Literal[
            "by_distance",
            "by_geometry",
            "by_distance+by_geometry",
            "by_geometry+by_distance",
        ],
        windfarm_file: str,
        turbine_file: str,
        output_file: str,
        merge_mode: Optional[MergeStrategy | str] = MergeStrategy.Combine,
        source_label: Optional[str] = None,
        rename_rules: Optional[str | dict] = None,
        max_distance: Optional[float] = None,
        merged_file=None,
        remaining_windfarm_file=None,
        remaining_turbine_file=None,
    ):
        """The distance/geometry based wind turbine to windfarm mapper on files."""
        if self.dump_temp_files:
            base_output = os.path.splitext(output_file)[0]
            if merged_file is None:
                merged_file = f"{base_output}.merged.csv"

            if remaining_windfarm_file is None:
                remaining_windfarm_file = f"{base_output}.remaining_windfarms.csv"

            if remaining_turbine_file is None:
                remaining_turbine_file = f"{base_output}.remaining_turbines.csv"

            self.merged_file = merged_file
            self.remaining_windfarm_file = remaining_windfarm_file
            self.remaining_turbine_file = remaining_turbine_file
        else:
            self.merged_file = None
            self.remaining_windfarm_file = None
            self.remaining_turbine_file = None

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
        df_turbines = read_locationdata_as_dataframe(
            turbine_file, rename_rules=rename_rules
        )

        n_turbines = (
            int(sum(df_windfarms["n_turbines"].fillna(0)))
            if "n_turbines" in df_windfarms
            else None
        )
        logger.info(
            f"Loaded {len(df_windfarms.index)} windfarms "
            f"with {n_turbines} turbines from {windfarm_file}"
        )
        logger.info(f"Loaded {len(df_turbines.index)} turbines from {turbine_file}")

        df_combined_turbines = self.map_dataframes(
            scheme,
            df_windfarms,
            df_turbines,
            merge_mode=merge_mode,
            source_label=source_label,
            max_distance=max_distance,
        )

        save_dataframe(df_combined_turbines, output_file)

    def map_dataframes(
        self,
        scheme: Literal[
            "by_distance",
            "by_geometry",
            "by_distance+by_geometry",
            "by_geometry+by_distance",
        ],
        df_windfarms: pd.DataFrame,
        df_turbines: pd.DataFrame,
        merge_mode: Optional[MergeStrategy | str] = MergeStrategy.Combine,
        source_label: Optional[str] = None,
        max_distance: Optional[float] = None,
    ):
        """The distance/geometry based wind turbine to windfarm mapper on dataframes."""
        # Standarize input dataframes
        df_windfarms = standarize_dataframe(df_windfarms).dropna(
            axis="columns", how="all"
        )
        df_turbines = standarize_dataframe(df_turbines)

        for method in scheme.split("+"):
            # Apply actual mapping
            if method == "by_distance":
                df_windfarms, df_turbines = self._map_distance_based(
                    df_windfarms, df_turbines, max_distance=max_distance
                )
            elif method == "by_geometry":
                df_windfarms, df_turbines = self._map_geometry_based(
                    df_windfarms, df_turbines, max_distance=max_distance
                )
            else:
                logger.error(f"Unknown mapping scheme field: {method} (from {scheme})")

        # Inner join mapped wind turbines and windfarm info
        pure_wt_cols = {"id", "name", "latitude", "longitude", "is_offshore", "country"}
        pure_wf_cols = {self.key_n_wt, self.key_mapped}
        df_wf_turbines = df_turbines[
            list(set(df_turbines.columns) & (pure_wt_cols | {self.key_wf_idx}))
        ]
        df_wf_turbines[self.key_wt_idx] = df_wf_turbines.index.copy()

        df_wf_windfarms = df_windfarms[
            list(set(df_windfarms.columns) - pure_wt_cols - pure_wf_cols)
        ]

        df_wf_turbines = df_wf_turbines.merge(
            df_wf_windfarms, on=self.key_wf_idx, how="inner"
        ).dropna(axis=1, how="all")

        turbines = []
        for _, wf_turbine in df_wf_turbines.iterrows():
            idx = wf_turbine[self.key_wt_idx]
            orig_turbine = df_turbines.iloc[idx]

            map_source_label = source_label
            if map_source_label is None:
                map_source_label = f"{wf_turbine['source']}+{orig_turbine['source']}"

            merged_turbine = merge_turbine_data(
                wf_turbine, orig_turbine, map_source_label
            )
            turbines.append(merged_turbine)

        logger.info(f"Mapped {len(turbines)} turbines to a windfarm")

        # Handle remainder
        wt_source = df_turbines["source"].iloc[0] if len(df_turbines.index) > 0 else None
        df_turbines = df_turbines.drop(df_wf_turbines[self.key_wt_idx].to_list())
        logger.info(
            f"Remaining {len(df_turbines.index)} turbines not mapped to a windfarm"
        )

        df_windfarms = df_windfarms.rename(columns={self.key_n_wt: "total_turbines"})
        df_windfarms[self.key_n_wt] = (
            df_windfarms["total_turbines"] - df_windfarms[self.key_mapped]
        )

        if wt_source is not None:
            df_windfarms["source"] = df_windfarms["source"] + f"-({wt_source} turbines)"

        if self.merged_file is not None:
            pd.DataFrame(turbines).to_csv(self.merged_file, index=False)

        if self.remaining_windfarm_file is not None:
            df_windfarms.to_csv(self.remaining_windfarm_file, index=False)

        if self.remaining_turbine_file is not None:
            df_turbines.to_csv(self.remaining_turbine_file, index=False)

        # Ignore errors as not all collumns might be added
        df_turbines = df_turbines.drop(
            [self.key_wt_idx, self.key_wf_idx], axis=1, errors="ignore"
        )
        df_windfarms = df_windfarms.drop([self.key_wf_idx], axis=1)

        df_windfarms = df_windfarms[df_windfarms[self.key_n_wt] > 0]
        logger.info(
            f"Remaining {len(df_windfarms.index)} windfarms with "
            f"{int(sum(df_windfarms['n_turbines'].fillna(0)))} unmapped turbines"
        )

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

        logger.info(
            f"Merged dataframe contains {len(df_combined_turbines.index)} turbine lines."
        )

        return df_combined_turbines

    def _prep_mapping_collumns(
        self, df_windfarms: pd.DataFrame, df_turbines: pd.DataFrame
    ):
        """Add some key values used for turbine/windfarm mapping."""
        # Define some keys/values used for mapping
        if self.tag_unmapped is None:
            self.tag_unmapped = len(df_windfarms.index)

        if self.key_mapped not in df_windfarms.columns:
            df_windfarms[self.key_mapped] = 0

        if self.key_wf_idx not in df_windfarms.columns:
            df_windfarms[self.key_wf_idx] = df_windfarms.index.copy()

        if self.key_wf_idx not in df_turbines.columns:
            df_turbines[self.key_wf_idx] = self.tag_unmapped

        return df_windfarms, df_turbines

    def _map_distance_based(
        self,
        df_windfarms: pd.DataFrame,
        df_turbines: pd.DataFrame,
        max_distance: Optional[bool] = None,
    ):
        """Map turbines to windfarms based on shortest distance windfarm and turbine."""
        logger.info("Map turbines to windfarms based on distance.")

        if max_distance is None:
            max_distance = 1e-1  # ~11km threshold

        logger.info(
            f"Max wf-wt distance={max_distance} ~{int(max_distance*111*100)/100}km"
        )

        # Define some keys/values used for mapping
        df_windfarms, df_turbines = self._prep_mapping_collumns(df_windfarms, df_turbines)

        if self.key_wf_dist not in df_turbines.columns:
            df_turbines[self.key_wf_dist] = math.inf
            df_turbines.loc[
                df_turbines[self.key_wf_idx] < self.tag_unmapped, self.key_wf_dist
            ] = 0

        mapped_turbines = 0

        done = False
        while not done:
            sub_windfarms = df_windfarms[
                df_windfarms[self.key_mapped] < df_windfarms[self.key_n_wt]
            ]

            sub_windfarms = sub_windfarms.reset_index(drop=True)
            tree = KDTree(get_lat_lon_matrix(sub_windfarms, compute_centroid=True))

            sub_turbines = df_turbines[df_turbines[self.key_wf_idx] == self.tag_unmapped]

            distances, idxs = tree.query(
                get_lat_lon_matrix(sub_turbines), k=1, distance_upper_bound=max_distance
            )

            # Translate index subset of windfarms back to original windfarm index
            sel = idxs < len(sub_windfarms.index)
            idxs[sel] = sub_windfarms[self.key_wf_idx].iloc[idxs[sel]]
            idxs[~sel] = self.tag_unmapped

            df_turbines.loc[sub_turbines.index, self.key_wf_idx] = idxs
            df_turbines.loc[sub_turbines.index, self.key_wf_dist] = distances

            for _, windfarm in sub_windfarms.iterrows():
                idx = windfarm[self.key_wf_idx]
                count = windfarm.get(self.key_n_wt)
                if count is None:
                    count = 0

                if not isinstance(count, int):
                    count = int(count)

                mapped = df_turbines[df_turbines[self.key_wf_idx] == idx].sort_values(
                    by=self.key_wf_dist
                )

                if len(mapped.index) > count:
                    # Don't match turbines with longest distance to this windfarm
                    df_turbines.loc[
                        mapped.iloc[count:].index, self.key_wf_idx
                    ] = self.tag_unmapped

                len_mapped = min(len(mapped.index), count)
                df_windfarms.loc[idx, self.key_mapped] = len_mapped

                wf_name = windfarm.get("name")
                if wf_name is None:
                    wf_name = windfarm.get("id", "Unknown")

                logger.debug(
                    f"Windfarm '{wf_name}' should have {count} wind turbines "
                    f"({len_mapped} turbines mapped)"
                )

            old_mapped_turbines = mapped_turbines
            mapped_turbines = sum(df_windfarms[self.key_mapped])
            logger.info(f"Mapped {mapped_turbines} wind turbines to a windfarm")

            # Done if none of the selected turbines isn't rejected
            # due to overbooking to a windfarm
            done = old_mapped_turbines + sum(sel) == mapped_turbines

        # Clean-up
        df_turbines = df_turbines.drop([self.key_wf_dist], axis=1)

        return df_windfarms, df_turbines

    def _map_geometry_based(
        self,
        df_windfarms: pd.DataFrame,
        df_turbines: pd.DataFrame,
        max_distance: Optional[float] = None,
    ):
        """Map turbines to windfarms based on geometry shape of windfarm."""
        logger.info("Map turbines to windfarms based on geometry shape of windfarm.")

        if max_distance is not None:
            logger.info(
                f"Max wf-wt distance={max_distance} ~{int(max_distance*111*100)/100}km"
            )

        # Define some keys/values used for mapping
        df_windfarms, df_turbines = self._prep_mapping_collumns(df_windfarms, df_turbines)

        if self.key_wt_idx not in df_turbines.columns:
            df_turbines[self.key_wt_idx] = df_turbines.index.copy()

        wf_countries = df_windfarms["country"].tolist()
        subset_turbines = df_turbines[df_turbines["country"].isin(wf_countries)]
        len_df_turbines = len(subset_turbines)
        turbine_counter = 0

        hit = 0
        missed = 0
        skipped = len(df_turbines) - len(subset_turbines)

        for _, turbine in subset_turbines.iterrows():
            turbine_counter += 1
            print_processing_status(
                turbine_counter,
                len_df_turbines,
                "Mapping turbines to windfarms by geometry",
            )

            found_windfarm = False
            turbine_point = Point(*get_lon_lat(turbine))

            fallback = None
            for _, windfarm in df_windfarms[
                df_windfarms["country"] == turbine.get("country")
            ].iterrows():
                geometry = windfarm["geometry"]

                if (
                    geometry.contains(turbine_point)
                    or max_distance is not None
                    and geometry.boundary.distance(turbine_point) < max_distance
                ):
                    wt_idx = turbine[self.key_wt_idx]
                    wf_idx = windfarm[self.key_wf_idx]
                    if windfarm["n_turbines"] > 0:
                        found_windfarm = True
                        df_turbines.loc[wt_idx, self.key_wf_idx] = wf_idx
                        df_windfarms.loc[wf_idx, self.key_mapped] += 1
                        break

                    fallback = {"wt_idx": wt_idx, "wf_idx": wf_idx}

            if not found_windfarm and fallback is not None:
                # Restore data from fallback
                wt_idx = fallback["wt_idx"]
                wf_idx = fallback["wf_idx"]
                df_turbines.loc[wt_idx, self.key_wf_idx] = wf_idx
                df_windfarms.loc[wf_idx, self.key_mapped] += 1
                found_windfarm = True

            if found_windfarm:
                hit += 1
            else:
                missed += 1
        print(
            f"Mapped {hit} turbines to a windfarm (missed: {missed}, skipped: {skipped})"
        )

        return df_windfarms, df_turbines
