"""Module that handles generation of turbine type tab files for wind turbine data."""

import contextlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from tabulate import tabulate

from .AutoIncrementTypeIndexGenerator import AutoIncrementTypeIndexGenerator
from .logs import logger
from .TurbineCurveLoader import get_cp_ct_power_curves
from .TurbineMatcher import TurbineMatcher
from .utils import (
    get_diameter,
    get_float_from_dict_list,
    get_height,
    get_radius,
    get_rated_power_kw,
)


class TurbineTypeTabFileWriter:
    """Handles generation of turbine type tab files for wind turbine data."""

    def __init__(
        self,
        config: Dict[str, Any],
        matcher: TurbineMatcher,
        type_index_generator: AutoIncrementTypeIndexGenerator,
        date_generated: Optional[datetime] = None,
    ):
        """Initialize turbine type tab file writer with configuration.

        Args:
            config (dict):             The json2tab config
            matcher:                   The TurbineMatcher used to match turbines
            type_index_generator:      The type index generator as used to generate types
            date_generated (datetime): (Optional) timestamp used for creation
        """
        self.matcher = matcher
        self.type_manager = matcher.turbine_type_manager
        self.model_designation_deriver = matcher.model_designation_deriver
        self.type_index_generator = type_index_generator

        # Get power curve data
        try:
            type_spec = config["output"]["tab_format"]["type_spec"]
        except (KeyError, ValueError, TypeError):
            type_spec = {}

        self.data_range = type_spec.get("windspeed_range", "cut-in:0.5:cut-out")
        self.extend_to_35ms = type_spec.get("extend_to_35ms", False)
        self.bypass_cutout = type_spec.get("bypass_cutout", False)

        self.date_generated = date_generated

    def write(
        self, matched_turbines: pd.DataFrame, output_dir: Path, type_tab_prefix: str
    ) -> pd.DataFrame:
        """Write set of all matches turbine types to tab files.

        Args:
            matched_turbines (pd.DataFrame): The dataframe with turbine locations
            output_dir (Path):               The output folder to write tab-files to
            type_tab_prefix (str):           Prefix for turbine type tab files

        Raises:
            Exception: when there is an error creating tab file for a type_index

        Returns:
            pandas.DataFrame with statistics
        """
        key = self.type_index_generator.type_idx_key
        frequency = matched_turbines[key].value_counts()
        type_idx_list = frequency.index.get_level_values(key).to_list()
        frequency_list = frequency[type_idx_list]
            
        data = {
            "Type index": type_idx_list,
            "Manufacterer": [],
            "Model designation": [],
            "Hub height (m)": [],
            "Diameter (m)": [],
            "Rated power (kW)": [],
            "Installed capacity (MW)": [],
            "Frequency": frequency_list,
        }

        for type_index in type_idx_list:
            try:
                # Write tab file for this type/model combination
                filename = output_dir / f"{type_tab_prefix}{type_index:03d}.tab"

                matched_line_index = (
                    self.type_index_generator.type_idx_to_matched_line_index(type_index)
                )

                if matched_line_index >= 0:
                    specs = self.write_specs_file(matched_line_index, filename)
                else:
                    specs = {"model_designation": "No turbine type matched"}
                    logger.warning("Skipped writing turbine type tab file for "
                                  f"type_index = {type_index}; "
                                  "no valid model designation found")

                model_designation = specs.get("model_designation")
                manufacturer = specs.get("manufacturer")
                height = specs.get("height")
                diameter = specs.get("diameter")
                rated_power = specs.get("rated_power")

                data["Model designation"].append(model_designation)
                data["Manufacterer"].append(manufacturer)
                data["Hub height (m)"].append(height)
                data["Diameter (m)"].append(diameter)
                data["Rated power (kW)"].append(rated_power)
            except Exception as e:
                logger.error(f"Error creating tab file for type_index={type_index}: {e}")
                raise e

        # Compute installed capacity
        data["Installed capacity (MW)"] = [
            freq * power / 1000 if freq is not None and power is not None else None
            for freq, power in zip(data["Frequency"], data["Rated power (kW)"])
        ]

        # Dump statistics data
        stats = pd.DataFrame(data=data)
        stats_capa = stats.sort_values(by=["Installed capacity (MW)"], ascending=False)
        stats_freq = stats.sort_values(by=["Frequency"], ascending=False)

        tbl_capa = tabulate(stats_capa, headers="keys", tablefmt="psql", showindex=False)
        tbl_freq = tabulate(stats_freq, headers="keys", tablefmt="psql", showindex=False)

        header_str = (
            "Model designation statistics; "
            f"total assigned model designation: {len(type_idx_list)}.\n\n"
        )
        print(f"\n\n{header_str}{tbl_capa}")

        with contextlib.suppress(Exception):
            stats_filename = "model_designation_statistics"
            stats.to_csv(output_dir / f"{stats_filename}.csv", index=False)
            with open(output_dir / f"{stats_filename}_capacity.txt", "w") as file:
                file.write(f"{header_str}{tbl_capa}")

            with open(output_dir / f"{stats_filename}_frequency.txt", "w") as file:
                file.write(f"{header_str}{tbl_freq}")

        return stats_capa

    def write_specs_file(self, matched_line_index: int, filename: str) -> dict:
        """Write turbine type specifications to tab file with power curves.

        Args:
            matched_line_index (int):  Line index of type in the type database to write
            filename (str):            Output file name

        Returns:
            Turbine specs related to matched_line_index
        """
        # Get the turbine type specs
        specs = self.type_manager.get_specs_by_line_index(matched_line_index)
        model_designation = specs["model_designation"]

        logger.debug(
            f"Writing turbine type tab file for {model_designation} to {filename}"
        )

        (
            wind_speeds,
            cp_values,
            ct_values,
            power_values,
            model_designation_data,
            cut_in,
            cut_out,
        ) = get_cp_ct_power_curves(
            specs,
            self.model_designation_deriver,
            windspeed_subset=self.data_range,
            extend_to_35ms=self.extend_to_35ms,
            bypass_cutout=self.bypass_cutout,
        )

        # Calculate rated power - use maximum value from power curve or rated_power spec
        rated_power_spec_kw = get_rated_power_kw(specs)
        max_power_curve = max(power_values) if power_values else 0

        if rated_power_spec_kw > 0:
            ratio = max_power_curve / rated_power_spec_kw
            if ratio > 750:
                # power_values seems to be wrongly interpreted, scale back to kW
                power_values = [power / 1000 for power in power_values]
                max_power_curve_old = max_power_curve
                max_power_curve /= 1000
                logger.info(
                    "Found inconsistency between "
                    ""
                    f"max(power_curve)={max_power_curve_old} and "
                    f"rated_power={rated_power_spec_kw}. "
                    "The power curve is scaled back by a factor 1000 such that "
                    f"max(power_curve)={max_power_curve}."
                )

        # Use the larger of the two values as rated_power in header
        rated_power_kw = max(rated_power_spec_kw, max_power_curve)

        with open(filename, "w") as file:
            # Write header with turbine info, type ID reference, and rated power
            height = get_height(specs)
            diameter = get_diameter(specs)

            source_string = specs.get("source_file", {})
            if (
                "source" in specs
                and specs["source"]
                and specs["source"] == specs["source"]
            ):
                source_string += f" [{specs['source']}]"

            file.write(
                f"# Wind turbine specification file generated by json2tab on "
                f"{self.matcher.match_generated}\n"
            )
            file.write(f"# Data based on {source_string}\n")
            file.write(
                f"# model designation = '{model_designation}' ("
                f"z={height} m, "
                f"D={diameter} m, "
                f"PR={rated_power_kw:.1f} kW)\n"
            )

            if model_designation_data != model_designation:
                file.write(
                    f"# WARNING: no data for model designation = '{model_designation}', "
                    f"this file is based on data from "
                    f"model designation = '{model_designation_data}'\n"
                )

            # Write parameter headers
            file.write(
                "#\tr (m)\t"
                "z (m)\t"
                "cT_low (-)\t"
                "cT_high (-)\t"
                "cut_in (m/s)\t"
                "cut_out (m/s)\n"
            )

            # Write parameters
            params = specs.get("additional_params", {})
            radius = get_radius([params, specs], 0)
            height = get_height([params, specs], 0)
            ct_low, _ = get_float_from_dict_list(
                ["cT_low (-)", "ct_low", "cT_low"], [params, specs], default=0
            )
            ct_high, _ = get_float_from_dict_list(
                ["cT_high (-)", "ct_high", "cT_high"], [params, specs], default=0
            )

            file.write(
                f"\t{radius:.4f}"
                f"\t{height:.4f}"
                f"\t{ct_low:.4f}"
                f"\t{ct_high:.4f}"
                f"\t{cut_in:.4f}"
                f"\t{cut_out:.4f}\n"
            )

            # Write power curve header
            file.write("#\tU (m/s)\t" "cP (-)\t" "cT (-)\t" "Power (kW)\n")

            # Write power curve data
            for ws, cp, ct, power in zip(wind_speeds, cp_values, ct_values, power_values):
                file.write(
                    f"\t{float(ws):.4f}"
                    f"\t{float(cp):.4f}"
                    f"\t{float(ct):.4f}"
                    f"\t{float(power):.1f}\n"
                )

            logger.info(
                f"Written turbine type tab file for '{model_designation}' to {filename}"
            )

            # Return the model designation used for the filename
            return specs
