"""Module for reading and processing wind turbine type data from file(s)."""

import contextlib
import json
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .logs import logger, logging
from .ModelNameBuilder import build_model_designation
from .ModelNameParser import parse_model_name
from .utils import (
    get_diameter,
    get_height,
    get_radius,
    get_rated_power_kw,
    power_to_kw,
    unify_file_list,
)


class TurbineTypeManager:
    """Main class for reading and processing wind turbine type data from file(s)."""

    def __init__(
        self, specs_data_file: Optional[Path | List[Path] | str | List[str]] = None
    ):
        """Initialize turbine type manager.

        Args:
            specs_data_file: (Optional) one or more files with turbine type specs
        """
        self.reset_type_specs()

        if specs_data_file is not None:
            self.load_type_specs(specs_data_file)

    def get_specs_dataframe(self, filtered: bool = True):
        """Gets turbine specs dataframe (filtered or non-filtered)."""
        if filtered:
            return self.specs_df_filtered

        return self.specs_df_full

    def get_specs_by_line_index(self, line_index: int):
        """Get turbine specification by line index of full turbine database."""
        if (
            line_index is not None
            and line_index >= 0
            and line_index < len(self.specs_df_full)
        ):
            return self.specs_df_full.iloc[line_index]

        return None

    def get_specs_by_tower_properties(
        self,
        diameter: Optional[float] = None,
        height: Optional[float] = None,
        power: Optional[float] = None,
        year: Optional[int] = None,
        is_offshore: Optional[bool] = None,
        country: Optional[str] = None,
    ):
        """Find closest matching turbine type with database lookup.

        Args:
            diameter:    (Optional) diameter of specific wind turbine tower
            height:      (Optional) height of specific wind turbine tower
            power:       (Optional) rated power of specific wind turbine tower
            year:        (Optional) installation year of specific wind turbine tower
            is_offshore: (Optional) is_offshore-flag of specific wind turbine tower
            country:     (Optional) country of specific wind turbine tower

        Returns:
            turbine specs closest matching tower properties
        """
        logger.debug(
            f"Get model_designation by tower properties: "
            f"diameter={diameter} (type={type(diameter).__name__}), "
            f"height={height} (type={type(height).__name__}), "
            f"power={power} (type={type(power).__name__}), "
            f"year={year} (type={type(year).__name__}), "
            f"is_offshore={is_offshore} (type={type(is_offshore).__name__}), "
            f"country={country} (type={type(country).__name__})"
        )

        filtered_df = self.get_specs_dataframe(filtered=True)

        # Apply filters
        if False:
            # WARNING: The is_offshore-field is of low quality at the moment;
            # don't use it to filter turbines
            offshore_value = "yes" if is_offshore else "no"
            filtered_df = filtered_df[
                filtered_df["is_offshore"].fillna("") == offshore_value
            ]
            logger.debug(
                f"Filtered to {len(filtered_df)} "
                f"{'off' if offshore_value == 'yes' else 'on'}shore turbines."
            )

            if filtered_df.empty:
                logger.info(
                    f"No matching turbines after filtering to "
                    f"{'off' if offshore_value == 'yes' else 'on'}shore turbines, "
                    "using full database."
                )
                filtered_df = self.specs_df_filtered

        if diameter is not None and not (
            np.min(filtered_df["diameter"]) <= diameter <= np.max(filtered_df["diameter"])
        ):
            logger.info("Don't allow extrapolation in diameter range, so it is not used.")
            diameter = None

        if height is not None and not (
            np.min(filtered_df["height"]) <= height <= np.max(filtered_df["height"])
        ):
            logger.info("Don't allow extrapolation in height range, so it is not used.")
            height = None

        if power is not None and not (
            np.min(filtered_df["rated_power"])
            <= power
            <= np.max(filtered_df["rated_power"])
        ):
            logger.info("Don't allow extrapolation in power range, so it is not used.")
            power = None

        scores = pd.DataFrame()
        if not (diameter is None and height is None and power is None):
            # Calculate similarity scores
            if diameter:
                scores["diameter_score"] = np.abs(filtered_df["diameter"] - diameter)
            else:
                # Slightly prefer smaller turbines over larger ones
                scores["diameter_score"] = np.abs(filtered_df["diameter"])

            if height:
                scores["height_score"] = np.abs(filtered_df["height"] - height)

            if power:
                scores["power_score"] = np.abs(filtered_df["rated_power"] - power)
            else:
                # Slightly prefer powerfull/powerless turbines in offshore/onshore region
                scores["power_score"] = np.abs(filtered_df["rated_power"])

        if not scores.empty:
            # Normalize and calculate total score with weighted factors
            for col in scores.columns:
                max_val = scores[col].max()
                if max_val > 0:
                    scores[col] = scores[col] / max_val

            # Apply weights to different factors
            if "diameter_score" in scores.columns:
                if diameter:
                    scores["diameter_score"] = (
                        scores["diameter_score"] * 3.0
                    )  # High weight for diameter
                else:
                    scores["diameter_score"] = (
                        scores["diameter_score"] * 1e-6
                    )  # In equal situation slighly prefer smaller turbines

            if "height_score" in scores.columns:
                scores["height_score"] = (
                    scores["height_score"] * 1.5
                )  # Medium weight for height

            if "power_score" in scores.columns:
                if power:
                    scores["power_score"] = (
                        scores["power_score"] * 2.0
                    )  # High weight for power
                else:
                    scores["power_score"] = (
                        scores["power_score"] * 1e-6 * (-1 if is_offshore else 1)
                    )  # In equal situation slighly prefer powerfull turbines offshore
                    # In equal situation slighly prefer powerless turbines onshore

            scores["total_score"] = scores.mean(axis=1)

            # Get best match
            matched_line_index = scores["total_score"].idxmin()
            return self.get_specs_by_line_index(matched_line_index), matched_line_index

        return None, None

    def reset_type_specs(self):
        """Reset turbine type specs data."""
        self.specs_files = []
        self.specs_df_full = None
        self.specs_df_filtered = None

    def load_type_specs(self, specs_data_file: Path | List[Path] | str | List[str]):
        """Load wind turbine type specification file(s).

        Args:
            specs_data_file: one or more files with turbine type specs data

        Raises:
            FileNotFoundError: if a single provided turbine type specs file is not found
        """
        specs_files = unify_file_list(specs_data_file)

        logger.debug(
            "Loading windturbine type specs data from the following "
            f"file{'(s)' if len(specs_files) > 1 else ''}: "
            f"{' '.join(str(p) for p in specs_files)}"
        )

        loaded_files = 0
        specs_list = []

        for specs_file in specs_files:
            if specs_file.exists():
                self.specs_files.append(specs_file)
                specs = self._load_specs_file(specs_file)
                specs_list.append(specs)
                loaded_files += 1
            elif len(specs_files) == 1:
                raise FileNotFoundError(
                    f"Turbine type specs file '{specs_file!s}' not found."
                )
            else:
                logger.error(
                    f"Turbine type specs file '{specs_file!s}' not found, "
                    "multiple files provided. Let's skip this file."
                )

        if loaded_files == 0:
            raise FileNotFoundError(
                "All turbine type specs files "
                f"'{' '.join(str(p) for p in specs_files)}' not found."
            )

        if len(specs_list) > 0:
            specs_df = pd.concat(specs_list)
            logger.debug(
                "Columns available after concatenation of specs_list: "
                f"{', '.join(specs_df.columns)}"
            )
        else:
            # Initialize with empty DataFrame with required columns
            specs_df = pd.DataFrame(
                columns=[
                    "type_code",
                    "turbine_model",
                    "height",
                    "diameter",
                    "rated_power",
                    "manufacturer",
                    "is_offshore",
                    "radius",
                    "z_height",
                    "ct_low",
                    "ct_high",
                ]
            )

        specs_df = self._add_computed_fields(specs_df)
        self.specs_df_full = pd.concat([self.specs_df_full, specs_df])

        # Set all nan's to None in specs table
        self.specs_df_full = self.specs_df_full.replace({np.nan: None})

        # Reset index such that we have a unique index to trace back turbine specs
        self.specs_df_full = self.specs_df_full.reset_index(drop=True)

        dump_specs(self.specs_df_full, "specsdump.csv")

        # Select a subset of the valid usable specs
        self.specs_df_filtered = filter_specs(self.specs_df_full)

    def _load_specs_file(self, specs_file: Path):
        try:
            loader = "Unknown"
            if specs_file.suffix.lower() == ".json":
                loader = "JSON"
                with open(specs_file, "r") as file_stream:
                    specs = convert_json_to_specs_df(json.load(file_stream))
            else:
                loader = "CSV"
                # Note: due to NaN values on some lines the type_id field are
                # implicitly promoted to float which make treating them as
                # integer-valued type_code impossible; see also
                # https://pandas.pydata.org/pandas-docs/stable/user_guide/gotchas.html#na-type-promotions-for-numpy-types
                specs = pd.read_csv(specs_file, dtype={"type_id": "Int32"})

                # Fix power rating to kW
                for power_col in ["power", "rated_power"]:
                    if power_col in specs.columns:
                        specs[power_col] = specs.apply(
                            lambda row, power_col=power_col: power_to_kw(
                                row[power_col],
                                diameter=row["diameter"],
                                hub_height=row["height"],
                            ),
                            axis=1,
                        )

                # Remove full N/A columns from dataset
                specs = specs.dropna(axis="columns", how="all")

            logger.info(
                f"Loaded {len(specs)} turbine specifications using "
                f"{loader}-format from {specs_file!s}"
            )

            # Mapping of renames of columns
            mapping = {
                "power": "rated_power",
                "original_name": "turbine_model",
                "turbine_id": "type_code",
            }

            for source, target in mapping.items():
                if source in specs.columns and target not in specs.columns:
                    logger.info(
                        f"Found column '{source}' but no '{target}' in dataframe, "
                        f"rename column '{source}' to '{target}'."
                    )
                    specs = specs.rename(columns={source: target})

            logger.debug(
                f"Columns available: {', '.join(specs.columns)} from {specs_file!s}"
            )

            # Store source file to dataframe for debug purposes
            specs["source_file"] = str(specs_file)

            return specs

        except (json.JSONDecodeError, pd.errors.ParserError) as e:
            logger.error(f"Error loading specifications from {specs_file!s}: {e}")

    def _add_computed_fields(self, specs_df):
        # Compute model_designation
        source_name = None
        if "turbine_model" in specs_df.columns:
            source_name = "turbine_model"

        if source_name:
            logger.info(
                f"Compute model designation for all specs based on source={source_name}"
            )
            specs_df["model_designation"], specs_df["is_known_manufacturer"] = zip(
                *specs_df.apply(
                    lambda row: build_model_designation_from_rowdata(row, source_name),
                    axis=1,
                )
            )
        else:
            logger.warning(
                "No source found for model_designation, "
                "so model_designation is missing in specs."
            )

        if "wind_speeds" in specs_df.columns:
            specs_df["wind_speeds_length"] = specs_df["wind_speeds"].apply(safe_length)
        else:
            specs_df["wind_speeds_length"] = 0

        specs_df["model_designation_length"] = specs_df["model_designation"].apply(
            safe_length
        )

        logger.info(
            f"Columns available in turbine type specs dataframe: "
            f"{', '.join(specs_df.columns)}"
        )

        return specs_df


def dump_specs(
    specs_df: pd.DataFrame,
    outputfile: str,
    exclude_cols: Optional[List] = None,
):
    """Dump turbine specs to csv-file."""
    if exclude_cols is None:
        exclude_cols = [
            "wind_speeds",
            "cp",
            "ct",
            "cps_gen",
            "ct_gen",
            "powerc_gen",
            "source_file",
        ]

    if logger.getEffectiveLevel() <= logging.DEBUG:
        with contextlib.suppress(Exception):
            exclude_cols = list(set(exclude_cols) & set(specs_df.columns))
            specs_df.drop(columns=exclude_cols).to_csv(outputfile)
            logger.debug(
                f"Dumped specs (w/o columns "
                f"{', '.join(str(col_name) for col_name in exclude_cols)}) "
                f"table of TurbineTypeManager to {outputfile}"
            )


def filter_specs(specs: pd.DataFrame) -> pd.DataFrame:
    """Filter specs to types with known manufacturer, model_designation and ws data.

    Args:
        specs (pd.DataFrame): dataframe with turbine type specs

    Returns:
        Filtered dataframe with turbine type specs
    """
    filtered_specs = specs[
        (specs["is_known_manufacturer"])
        & (specs["wind_speeds_length"] > 0)
        & (specs["model_designation_length"] > 0)
    ]

    logger.info(
        f"Filtered turbine specifications to {len(filtered_specs)} turbines "
        "with known manufacturer, windspeed-data and model_designation."
    )

    dump_specs(filtered_specs, "specsdump-filtered.csv")

    return filtered_specs


def convert_json_to_specs_df(specs_data) -> pd.DataFrame:
    """Convert JSON turbine specs data to pandas.DataFrame format."""
    records = []
    for type_code, data in specs_data.items():
        try:
            type_id = int(data.get("type_id", None))
        except (ValueError, IndexError, TypeError):
            type_id = None

        model_name = data.get("turbine_model", "")

        manufacturer = None
        diameter = get_diameter(data, 0)
        power = get_rated_power_kw(data)
        height = get_height(data, 0)

        try:
            model_name_data = parse_model_name(model_name)
            manufacturer = model_name_data["manufacturer"]
            if diameter == 0:
                diameter = get_diameter(model_name_data, default=0)
            if power == 0:
                power = power_to_kw(
                    get_rated_power_kw(model_name_data, guess_unit=False),
                    diameter=diameter,
                    height=height,
                )
        except (ValueError, IndexError, TypeError):
            pass

        if not manufacturer:
            manufacturer = model_name.split()[0] if model_name else ""

        # Fix wrong diameter (use radius instead)
        radius = get_radius(data, 0)
        if diameter < radius:
            diameter = 2 * radius
            logger.debug(f"Correced diamter for {type_code}, set diameter = 2*radius.")

        record = {
            "type_code": type_code,
            "type_id": type_id,
            "turbine_model": model_name,
            "height": height,
            "diameter": diameter,
            "rated_power": power,
            "manufacturer": manufacturer,
            "is_offshore": "yes" if "OFFSHORE" in model_name.upper() else "no",
        }

        # Add additional parameters
        add_params = data.get("additional_params", {})
        record["radius"] = add_params.get("radius (m)", diameter / 2)
        record["z_height"] = add_params.get("z_height (m)", height)
        record["ct_low"] = add_params.get("cT_low (-)", None)
        record["ct_high"] = add_params.get("cT_high (-)", None)

        # Add optional parameters
        optional_list_parameters = [
            "wind_speeds",
            "cp",
            "ct",
            "cps_gen",
            "ct_gen",
            "powerc_gen",
            "is_manufacturer_data",
        ]
        for param in optional_list_parameters:
            if param in data:
                record[param] = data[param]

        records.append(record)

    return pd.DataFrame(records)


def safe_length(data: list | str):
    """Returns length of data where data is list or string.

    Args:
        data (list|str): data to compute length from

    Returns:
        Length of string or list, otherwise 0
    """
    if data and isinstance(data, (list, str)):
        return len(data)

    return 0


def build_model_designation_from_rowdata(row, model_name_source: str) -> Tuple[str, bool]:
    """Derive model designation from row.

    Args:
        row:               row of pandas.DataFrame containing turbine specs
        model_name_source: Field of datarow to get the turbine_model name

    Returns:
        model_designation (str):      Model designation for the turbine type of this row
        is_known_manufacturer (bool): Flag indicating if manufacturer is known
    """
    forbidden_values = [None, ""]

    # Don't recompute model_designation if it is stored in row-data
    model_designation = row.get("model_designation", None)
    if model_designation not in forbidden_values:
        is_known_manufacturer = row.get("is_known_manufacturer")
        return model_designation, is_known_manufacturer

    # First approach: use source_name/turbine_model-field to get model_name_data
    model_name_data = row.get(model_name_source, None)
    specs_model_name = None

    if model_name_data not in forbidden_values:
        specs_model_name = parse_model_name(model_name_data)
        model_designation = specs_model_name["model_designation"]
        is_known_manufacturer = specs_model_name["is_known_manufacturer"]
    else:
        model_designation = None
        is_known_manufacturer = False

    # Alternative approach: construct model_designation from row-data
    manufacturer = row["manufacturer"] if "manufacturer" in row else None

    try:
        # Fallback to parsed manufacturer if that one is richer
        if len(specs_model_name["manufacturer"]) > len(manufacturer):
            manufacturer = specs_model_name["manufacturer"]
    except (TypeError, IndexError):
        pass

    diameter = get_diameter(row, None)
    power = get_rated_power_kw(row)
    if power == 0:
        power = None

    model_designation_generated = (
        build_model_designation(str(manufacturer).title(), diameter, power)
        if manufacturer and diameter and power
        else None
    )

    if model_designation_generated:
        # Test generated model_designation
        result_generated = parse_model_name(model_designation_generated)

        missing_fields_from_turbine_model = 0
        missing_fields_from_generated = 0
        compare_fields = ["manufacturer", "diameter", "power"]
        if specs_model_name and result_generated:
            for field in compare_fields:
                if (
                    field not in specs_model_name
                    or specs_model_name[field] in forbidden_values
                ):
                    missing_fields_from_turbine_model += 1

                if (
                    field not in result_generated
                    or result_generated[field] in forbidden_values
                ):
                    missing_fields_from_generated += 1

            if (
                missing_fields_from_turbine_model > missing_fields_from_generated
                and specs_model_name["manufacturer_pattern"]
                == result_generated["manufacturer_pattern"]
                and len(model_designation_generated) > len(model_designation)
            ):
                # More info seems to be kept in the generated model_designation
                model_designation = model_designation_generated
        else:
            model_designation = model_designation_generated

    return model_designation, is_known_manufacturer
