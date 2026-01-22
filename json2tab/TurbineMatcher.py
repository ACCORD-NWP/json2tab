"""Module for turbine matching to match each turbine to a specific model_designation."""

import contextlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

from .DefaultTurbineSelector import DefaultTurbineSelector
from .DimensionLocationMapper import DimensionLocationMapper
from .io.write_statistics import inject_suffix_in_filename, write_statistics
from .io.writers import generate_output_filename
from .logs import logger
from .ModelDesignationDeriver import ModelDesignationDeriver
from .ModelNameParser import parse_model_name
from .ProbabilisticMapper import ProbabilisticMapper
from .TurbineLocationManager import TurbineLocationManager
from .TurbineTypeManager import TurbineTypeManager
from .utils import (
    empty_to_none,
    get_height,
    get_radius,
    get_rated_power_kw,
    print_processing_status,
    zero_to_none,
)


class TurbineMatcher:
    """The turbine matcher matches each turbine to a specific model_designation."""

    def __init__(
        self,
        config,
        turbine_location_manager: TurbineLocationManager,
        turbine_type_manager: TurbineTypeManager,
        model_designation_key: Optional[str] = None,
        matched_line_index_key: Optional[str] = None,
    ):
        """Initialize turbine matcher.

        Args:
            config (dict):                The json2tab configuration
            turbine_location_manager:     The manager that holds the turbine locations
            turbine_type_manager:         The manager that holds the turbine types
            model_designation_key (str):  (Optional) column name for model_designation
            matched_line_index_key (str): (Optional) column name for matched_line_index
        """
        self.turbine_location_manager = turbine_location_manager
        self.turbine_type_manager = turbine_type_manager

        self.model_designation_deriver = ModelDesignationDeriver(turbine_type_manager)
        self.dimension_location_mapper = DimensionLocationMapper()
        self.probabilistic_mapper = ProbabilisticMapper()
        self.default_turbine_selector = DefaultTurbineSelector()

        self.suffix = None
        self.match_generated = None
        self.model_designation_key = model_designation_key
        self.matched_line_index_key = matched_line_index_key
        self.used_matcher_key = "MatchedBy"

        self.match_cache = {}

        self.output_dir = Path(config["output"]["directory"])
        self.matching_summary_file = config["output"]["files"].get("matching_summary")
        self.write_matching_summary_per_country = config["output"]["files"].get(
            "matching_summary_per_country", False
        )

        try:
            self.forbidden_types = config["matcher"]["forbidden_types"]
        except (KeyError, ValueError, TypeError):
            self.forbidden_types = []

        if isinstance(self.forbidden_types, str):
            self.forbidden_types = self.forbidden_types.split(";")

        try:
            self.use_probabilistic_mapper = config["matcher"]["use_probabilistic_mapper"]
        except (KeyError, ValueError, TypeError):
            self.use_probabilistic_mapper = True

        try:
            self.use_default_selector = config["matcher"]["use_default_selector"]
        except (KeyError, ValueError, TypeError):
            self.use_default_selector = True

    def _turbine_type_to_model_designation(
        self, turbine_type: str
    ) -> Tuple[str, int, str]:
        if turbine_type in self.match_cache:
            model_designation, matched_line_index = self.match_cache[turbine_type]

            logger.debug(
                f"Model designation for turbine_type='{turbine_type}' is set to "
                f"already cached '{model_designation}'."
            )

            return model_designation, matched_line_index

        # Translate fallback turbine_type to known model_designation using deriver
        (
            model_designation,
            matched_line_index,
            _,
        ) = self.model_designation_deriver.by_turbine_type(
            turbine_type,
            fields=["model_designation", "type_id", "type_code", "turbine_model"],
        )

        if model_designation:
            logger.debug(
                f"Model designation for turbine_type={turbine_type} is set to "
                f"'{model_designation}' (match found in dataframe on "
                f"index={matched_line_index})."
            )

            return model_designation, matched_line_index

        return None, None

    def add_to_cache(
        self,
        turbine_type: str | List[str],
        model_designation: str,
        matched_line_index: int,
    ):
        """Adds turbine type(s) to match_cache."""
        if isinstance(turbine_type, str):
            turbine_type = [turbine_type]

        for item in turbine_type:
            if item not in self.match_cache:
                self.match_cache[item] = (model_designation, matched_line_index)

    def tower_implements_turbine_type(
        self, tower_properties, matched_line_index: int
    ) -> bool:
        """Check if properties of a wind turbine can match a given indexed turbine type.

        Args:
            tower_properties (dict-like): properties of a concrete located wind turbine
            matched_line_index (int):     line index of turbine type that should match

        Returns:
            True if basic radius < height check is valid for this turbine+type
        """
        type_specs = self.turbine_type_manager.get_specs_by_line_index(
            matched_line_index
        ).to_dict()

        sources = [tower_properties, type_specs]
        radius = get_radius(sources)
        height = get_height(sources)

        if radius < height:
            return True

        logger.info(
            "Found wrong radius/height for turbine "
            f"(radius={get_radius(tower_properties)}, "
            f"height={get_height(tower_properties)}) and "
            f"turbine type (radius={get_radius(type_specs)}, "
            f"height={get_height(type_specs)}). "
            f"Mixing results in model_designation='{type_specs['model_designation']}'; "
            f"radius={radius} >= hubheight={height}."
        )

        return False

    def tower_implements_cached_type(
        self, tower_properties, cached_turbine_type: str
    ) -> bool:
        """Check if properties of a wind turbine can match a given cached turbine type.

        Args:
            tower_properties (dict-like): properties of a concrete located wind turbine
            cached_turbine_type (str):    suggested turbine type for this tower

        Returns:
            True if basic radius < height check is valid for this turbine+type
        """
        _, matched_line_index = self.match_cache[cached_turbine_type]
        return self.tower_implements_turbine_type(tower_properties, matched_line_index)

    def match(self, turbines: pd.DataFrame = None) -> pd.DataFrame:
        """Matches types of turbines on given locations to known model_designations.

        Args:
            turbines (pd.DataFrame): (Optional) pandas.DataFrame with turbine locations

        Raises:
            Exception: when there is an error in mapping a certain turbine

        Returns:
            turbines (pd.DataFrame): dataframe turbine locations with model_designation
        """
        if turbines is None:
            turbines = self.turbine_location_manager.turbines

        # Setup match tag
        self.match_generated = datetime.now()
        stamp = f"{self.match_generated:%Y%m%d_%H%M%S_%f}"

        self.suffix = f"_matched_by_json2tab_{stamp}"

        if self.model_designation_key is None:
            self.model_designation_key = f"model_designation{self.suffix}"

        if self.matched_line_index_key is None:
            self.matched_line_index_key = f"matched_line_index{self.suffix}"

        # Add columns to DataFrame to store matched model_designation / specs
        no_match_idx = -1
        turbines[self.model_designation_key] = None
        turbines[self.matched_line_index_key] = no_match_idx

        # Setup cache for quick store of found matches
        self.match_cache = {}

        # Setup counters for book keeping
        counter_global = {}
        counter_per_country = {}

        total_turbines = len(turbines.index)
        logger.info(f"Start matching types to {total_turbines} turbine locations")

        # Map all unique turbine types to known model designations.
        turbine_counter = 0
        for idx, turbine in turbines.iterrows():
            turbine_counter += 1
            try:
                print_processing_status(
                    turbine_counter,
                    total_turbines,
                    "Matching turbines with model designations",
                )

                (
                    model_designation,
                    matched_line_index,
                    used_matcher,
                ) = self.match_model_designation_on_turbine(turbine)

                type_props = self.turbine_type_manager.get_specs_by_line_index(
                    matched_line_index
                )
                sources = [turbine, type_props]
                radius = get_radius(sources)
                diameter = 2 * radius if radius is not None else 0
                height = get_height(sources)
                rated_power = get_rated_power_kw(sources)

                turbines.loc[idx, "radius"] = radius
                turbines.loc[idx, "diameter"] = diameter
                turbines.loc[idx, "power_rating"] = rated_power
                turbines.loc[idx, "hub_height"] = height
                turbines.loc[idx, self.model_designation_key] = model_designation
                turbines.loc[idx, self.matched_line_index_key] = (
                    matched_line_index or no_match_idx
                )
                if self.used_matcher_key is not None:
                    turbines.loc[idx, self.used_matcher_key] = used_matcher

                country = turbine.get("country")
                if country not in counter_per_country:
                    counter_per_country[country] = {}

                # Do book keeping to count different matcher sources
                for counter in [counter_global, counter_per_country[country]]:
                    if used_matcher in counter:
                        counter[used_matcher] += 1
                    else:
                        counter[used_matcher] = 1

            except Exception as e:
                logger.error(
                    f"Error in mapping turbine at index {idx}.\n"
                    f"Turbine = {turbine}\n"
                    f"Error: {e}"
                )
                raise e

        self._write_statistics_reports(counter_global, counter_per_country)
        return turbines

    def _write_statistics_reports(self, counter_global, counter_per_country):
        """Write matching statistics reports."""
        known_matchers = [
            "Total",
            "CacheHit(TurbineType)",
            "CacheHit(Manufacturer+TurbineType)",
            "DatabaseLookup(Manufacturer+TurbineType)",
            "DatabaseLookup(TurbineType)",
            "DimensionLocationMapper",
            "DatabaseLookup(TowerProperties)",
            "ProbabilisticMapper",
            "DefaultTurbineSelector",
        ]

        # Add missed keys
        for key in counter_global:
            if key not in known_matchers:
                known_matchers.append(key)

        hits_per_country = {"Matcher": known_matchers, "Total": []}

        percent_per_country = {"Matcher": known_matchers, "Total (%)": []}

        counter_per_country["Total"] = counter_global
        for country, counter in counter_per_country.items():
            if country not in hits_per_country:
                hits_per_country[country] = []

            if f"{country} (%)" not in percent_per_country:
                percent_per_country[f"{country} (%)"] = []

            total = 0
            for value in counter.values():
                total += value

            details = {"Matcher": known_matchers, "Nr of Hits": [], "Percentage (%)": []}

            for key in known_matchers:
                value = counter.get(key, 0) if key != "Total" else total
                percent = int(value / total * 100)

                details["Nr of Hits"].append(value)
                details["Percentage (%)"].append(percent)

                hits_per_country[country].append(value)
                percent_per_country[f"{country} (%)"].append(percent)

            filename = inject_suffix_in_filename(
                self.matching_summary_file, f"_{country}"
            )
            if isinstance(self.write_matching_summary_per_country, str):
                ext = self.write_matching_summary_per_country
                if filename is not None and len(filename) > 0:
                    filename = generate_output_filename(filename, ext)
                    self.write_matching_summary_per_country = True
                else:
                    self.write_matching_summary_per_country = False

            if self.write_matching_summary_per_country:
                stats = pd.DataFrame(data=details)
                stats = stats.sort_values(by=["Percentage (%)"], ascending=False)

                with contextlib.suppress(Exception):
                    write_statistics(
                        stats,
                        self.output_dir,
                        filename,
                        header=f"Matching Summary "
                        f"(total towers matched in {country}: {total}):\n\n",
                    )

        header = f"Matching Summary (total towers matched: {total}):\n\n"
        print(header)

        for datasource, sort_key, suffix in [
            (hits_per_country, "Total", "_hits"),
            (percent_per_country, "Total (%)", "_percent"),
        ]:
            stats = pd.DataFrame(data=datasource).sort_values(
                by=[sort_key], ascending=False
            )

            txt_tbl = write_statistics(
                stats,
                self.output_dir,
                inject_suffix_in_filename(self.matching_summary_file, suffix),
                header=header,
            )

            print(f"{txt_tbl}\n\n")

    def match_model_designation_on_turbine(self, turbine) -> Tuple[str, int, str]:
        """Gets the model_designation for a given turbine tower.

        Args:
            turbine: row of pandas.DataFrame with wind turbine locations

        Returns:
            model_designation (str):
            matched_line_index (int):
            used_matcher (str):
        """
        manufacturer = empty_to_none(turbine.get("manufacturer"))
        turbine_type = empty_to_none(turbine.get("type"))

        if isinstance(manufacturer, str):
            manufacturer = manufacturer.strip("?")

        if isinstance(turbine_type, str):
            turbine_type = turbine_type.strip("?")

        lon = turbine.get("longitude")
        lat = turbine.get("latitude")
        country = turbine.get("country")
        is_offshore = turbine.get("is_offshore")

        diameter = zero_to_none(turbine.get("diameter"))
        height = zero_to_none(turbine.get("hub_height"))
        power = zero_to_none(turbine.get("power_rating"))

        # Delete turbine_type if turbine_type is in the forbidden_types-list
        if turbine_type in self.forbidden_types:
            turbine_type = None

        # [Option 1]: Check if this turbine can implement this turbine_type
        if turbine_type is not None and turbine_type in self.match_cache:
            if self.tower_implements_cached_type(turbine, turbine_type):
                model_designation, matched_line_index = self.match_cache[turbine_type]
                return model_designation, matched_line_index, "CacheHit(TurbineType)"

            # Basic checks faild, don't trust this turbine_type for this turbine.
            turbine_type = None

        # Build extended turbine type
        extended_type = None
        if turbine_type is not None and isinstance(manufacturer, str):
            parts = manufacturer.split(" ")

            man_code = parts[0] if len(parts) > 0 else ""
            man_code += f" {parts[1]}" if len(parts) > 1 else ""

            if len(parts) > 0 and not turbine_type.lower().startswith(man_code.lower()):
                # Extend turbine_type with manufacturer info
                extended_type = f"{man_code} {turbine_type}"

        # [Option 2]: Check if this turbine can implement the extended turbine_type
        if extended_type is not None and extended_type in self.match_cache:
            if self.tower_implements_cached_type(turbine, extended_type):
                model_designation, matched_line_index = self.match_cache[extended_type]
                return (
                    model_designation,
                    matched_line_index,
                    "CacheHit(Manufacturer+TurbineType)",
                )

            # Basic checks faild, don't trust this extended type for this turbine.
            extended_type = None

        tag_str = f"N{lat}, E{lon} ({country}, {'off' if is_offshore else 'on'}shore)"
        props = (
            f"manufacturer='{manufacturer}', turbine_type='{turbine_type}', "
            f"extended_type='{extended_type}'; "
            f"(diameter={diameter}, height={height}, power={power})"
        )

        logger.debug(f"Process turbine {tag_str} with {props}")

        if turbine_type is not None:
            # [Option 3]: Extended turbine_type-based model_designation detection
            if extended_type is not None:
                (
                    model_designation,
                    matched_line_index,
                    _,
                ) = self.model_designation_deriver.by_turbine_type(
                    extended_type, row_data=turbine
                )

                if model_designation and self.tower_implements_turbine_type(
                    turbine, matched_line_index
                ):
                    # Found realistic match
                    logger.info(
                        f"Model designation is set to '{model_designation}' "
                        f"(via turbine_type='{extended_type}'; from '{turbine_type}') "
                        "by ModelDesignationDeriver (by manufacturer+turbine_type) "
                        f"(match found in dataframe on index={matched_line_index})."
                    )

                    self.add_to_cache(
                        [extended_type, turbine_type],
                        model_designation,
                        matched_line_index,
                    )
                    return (
                        model_designation,
                        matched_line_index,
                        "DatabaseLookup(Manufacturer+TurbineType)",
                    )

            # [Option 4]: Pure turbine_type-based model_designation detection
            (
                model_designation,
                matched_line_index,
                _,
            ) = self.model_designation_deriver.by_turbine_type(
                turbine_type, row_data=turbine
            )

            if model_designation and self.tower_implements_turbine_type(
                turbine, matched_line_index
            ):
                # Found realistic match
                logger.info(
                    f"Model designation is set to '{model_designation}' "
                    f"(from turbine_type={turbine_type}) "
                    f"by ModelDesignationDeriver (by turbine_type) "
                    f"(match found in dataframe on index={matched_line_index})."
                )

                self.add_to_cache(turbine_type, model_designation, matched_line_index)
                return (
                    model_designation,
                    matched_line_index,
                    "DatabaseLookup(TurbineType)",
                )

            # [Option 3b] Extended turbine_type-based detection via enriched
            if extended_type is not None:
                extended_type_parse_data = parse_model_name(extended_type)
                if extended_type_parse_data["is_known_manufacturer"]:
                    extended_type_enriched = (
                        self.model_designation_deriver.enrich_model_designation(
                            extended_type, additional_data=turbine
                        )
                    )
                    if extended_type_enriched != extended_type:
                        (
                            model_designation,
                            matched_line_index,
                            _,
                        ) = self.model_designation_deriver.by_turbine_type(
                            extended_type_enriched, row_data=turbine
                        )

                        if model_designation and self.tower_implements_turbine_type(
                            turbine, matched_line_index
                        ):
                            # Found realistic match
                            logger.info(
                                f"Model designation is set to '{model_designation}' "
                                f"(via turbine_type='{extended_type_enriched}' and "
                                f"'{extended_type}'; from '{turbine_type}') "
                                "by ModelDesignationDeriver "
                                "(by enriched manufacturer+turbine_type) "
                                "(match found in dataframe on "
                                f"index={matched_line_index})."
                            )

                            self.add_to_cache(
                                [extended_type_enriched, extended_type, turbine_type],
                                model_designation,
                                matched_line_index,
                            )
                            return (
                                model_designation,
                                matched_line_index,
                                "DatabaseLookup(EnrichedTurbineType)",
                            )
                ...

            # [Option 4b]: Pure turbine_type-based model_designation detection
            turbine_type_parse_data = parse_model_name(turbine_type)
            if turbine_type_parse_data["is_known_manufacturer"]:
                turbine_type_enriched = (
                    self.model_designation_deriver.enrich_model_designation(
                        turbine_type, additional_data=turbine
                    )
                )
                if turbine_type_enriched != turbine_type:
                    (
                        model_designation,
                        matched_line_index,
                        _,
                    ) = self.model_designation_deriver.by_turbine_type(
                        turbine_type_enriched, row_data=turbine
                    )

                    if model_designation and self.tower_implements_turbine_type(
                        turbine, matched_line_index
                    ):
                        # Found realistic match
                        logger.info(
                            f"Model designation is set to '{model_designation}' "
                            f"(via turbine_type='{turbine_type_enriched}'; "
                            f"from '{turbine_type}') "
                            f"by ModelDesignationDeriver (by enriched turbine_type) "
                            f"(match found in dataframe on index={matched_line_index})."
                        )

                        self.add_to_cache(
                            [turbine_type_enriched, turbine_type],
                            model_designation,
                            matched_line_index,
                        )
                        return (
                            model_designation,
                            matched_line_index,
                            "DatabaseLookup(EnrichedTurbineType)",
                        )

        # [Option 5]: Use the dimension/location mapper to get a guess for turbine_type
        turbine_type_guess = self.dimension_location_mapper.map(turbine)
        if turbine_type_guess:
            (
                model_designation,
                matched_line_index,
            ) = self._turbine_type_to_model_designation(turbine_type_guess)

            if model_designation:
                logger.info(
                    f"Model designation is set to '{model_designation}' "
                    f"(via turbine_type='{turbine_type_guess}') "
                    f"based on DimensionLocationMapper "
                    f"(match found in dataframe on index={matched_line_index})."
                )

                self.add_to_cache(
                    turbine_type_guess, model_designation, matched_line_index
                )
                return model_designation, matched_line_index, "DimensionLocationMapper"

        if not (diameter is None and height is None and power is None):
            # [Option 6]: Use tower properties to derive model_designation for this tower
            (
                specs,
                matched_line_index,
            ) = self.turbine_type_manager.get_specs_by_tower_properties(
                diameter=diameter, height=height, power=power
            )

            if specs is not None:
                model_designation = specs["model_designation"]

                if model_designation:
                    logger.info(
                        f"Model designation for tower with "
                        f"diameter={diameter}, height={height}, power={power} "
                        f"is set to '{model_designation}' "
                        "by TurbineTypeManager (by tower properties) "
                        f"(match found in dataframe on index={matched_line_index})."
                    )
                    return (
                        model_designation,
                        matched_line_index,
                        "DatabaseLookup(TowerProperties)",
                    )

        # [Option 7]: Use the probabilistic mapper as fallback
        if self.use_probabilistic_mapper:
            turbine_type_probabilistically = self.probabilistic_mapper.map(
                turbine_type, lat, lon, diameter
            )
            if turbine_type_probabilistically:
                (
                    model_designation,
                    matched_line_index,
                ) = self._turbine_type_to_model_designation(
                    turbine_type_probabilistically
                )

                if model_designation:
                    logger.info(
                        f"Model designation is set to '{model_designation}' "
                        f"(via turbine_type='{turbine_type_probabilistically}') "
                        "based on ProbabilisticMapper, "
                        f"lat={lat}, lon={lon}, diameter={diameter} "
                        f"(match found in dataframe on index={matched_line_index})."
                    )

                    self.add_to_cache(
                        turbine_type_probabilistically,
                        model_designation,
                        matched_line_index,
                    )
                    return model_designation, matched_line_index, "ProbabilisticMapper"

        # [Option 8]: Use DefaultTurbineSelector as final fallback
        if self.use_default_selector:
            fallback_type = self.default_turbine_selector.get_default_turbine(lat, lon)

            if fallback_type:
                (
                    model_designation,
                    matched_line_index,
                ) = self._turbine_type_to_model_designation(fallback_type)

                if model_designation:
                    logger.info(
                        f"Model designation is set to '{model_designation}' "
                        f"(via turbine_type='{fallback_type}') "
                        f"based on DefaultTurbineSelector, lat={lat}, lon={lon} "
                        f"(match found in dataframe on index={matched_line_index})."
                    )

                    self.add_to_cache(
                        fallback_type, model_designation, matched_line_index
                    )
                    return model_designation, matched_line_index, "DefaultTurbineSelector"

        # Final option: discard this turbine
        logger.error(f"Cannot find turbine type for turbine at {tag_str} with {props}.")

        if turbine_type is not None:
            logger.warning(
                "Did you missed model name parsing rules for "
                f"turbine_type='{turbine_type}'?"
            )

        if extended_type is not None:
            logger.warning(
                "Did you missed model name parsing rules for "
                f"extended_type='{extended_type}'?"
            )

        return None, None, "NotMatched"
