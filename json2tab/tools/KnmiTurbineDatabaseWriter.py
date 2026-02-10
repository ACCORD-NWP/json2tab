"""Converter to convert KNMI turbine type tab-files to tubine type database."""

import glob
import json
from typing import List, Optional

import pandas as pd

from ..logs import logger
from ..ModelNameBuilder import build_model_designation
from ..ModelNameParser import parse_model_name
from ..TurbineCurveLoader import calculate_power_curve
from ..utils import get_rated_power_kw


def knmi_turbine_database_writer(
    input_file_patterns: Optional[List[str]] = None,
    output_file_name: str = "output.json",
):
    """Converter to convert KNMI turbine type tab-files to tubine type database."""
    if input_file_patterns is None:
        input_file_patterns = ["wind_turbine_*.tab"]
    print(f"knmi_turbine_database_writer({input_file_patterns}, {output_file_name})")

    db = {}

    for input_file_pattern in input_file_patterns:
        for filename in glob.glob(input_file_pattern):
            logger.debug(f"Process file {filename}")

            prefix = "KN"

            try:
                type_id = get_knmi_typeid_from_filename(filename)
                logger.debug(f"Found knmi typeid for {filename}: {type_id}")
            except ValueError as e:
                try:
                    # Mybe we process Fortran-based tab-files
                    type_id = get_knmi_typeid_from_filename(filename, "wind_turbine_FO_")
                    logger.debug(f"Found fortran typeid for {filename}: {type_id}")
                    prefix = "FO"
                except ValueError:
                    # Assuming Fortran-style tab-files didn't solve the issue
                    raise e from None

            # Read turbine name
            with open(filename, "r") as f:
                try:
                    first_line = f.readline()
                    end = first_line.rfind("(")
                    turbine_model = first_line[1:end].strip()
                except Exception as e:
                    logger.exception(f"Error reading file {filename}: {e!s}")
                    turbine_model = None

            if turbine_model is not None:
                logger.debug(f"Found turbine name for typeID {type_id} from {filename}")

                logger.info(
                    f"Process file '{filename}' with "
                    f"{'KNMI' if prefix == 'KN' else 'FORTRAN' if prefix == 'FO' else ''}"
                    f" typeID {type_id} containing turbine model '{turbine_model}'"
                )

                # Read turbine characteristics
                dfHeader = pd.read_csv(
                    filename,
                    sep=r"\s\s+",
                    header=None,
                    nrows=1,
                    engine="python",
                    comment="#",
                )
                dfHeader.columns = ["r", "z", "cT_low", "cT_high"]
                logger.debug(
                    f"Typeid = {type_id}: r={dfHeader['r'][0]}, "
                    f"z={dfHeader['z'][0]}, "
                    f"cT_low={dfHeader['cT_low'][0]}, "
                    f"cT_high={dfHeader['cT_high'][0]}"
                )

                height = dfHeader["z"][0]
                diameter = 2.0 * dfHeader["r"][0]
                rated_power = None

                # Read cP and cT curves
                dfData = pd.read_csv(
                    filename,
                    sep=r"\s+",
                    skiprows=[0, 1, 2],
                    header=None,
                    engine="python",
                    comment="#",
                )
                dfData.columns = ["U", "cP", "cT"]
                wind_speeds = dfData["U"].tolist()
                cp = dfData["cP"].tolist()
                ct = dfData["cT"].tolist()

                logger.debug(
                    f"Typeid = {type_id}: read {len(dfData['U'].tolist())} lines "
                    "of cP and cT curves"
                )

                if prefix == "KN":
                    # Strip the '_ECN'-appendix as added by some KNMI turbines
                    if turbine_model.endswith("_ECN"):
                        turbine_model = turbine_model[:-4]

                    # Update turbine_model based on known special types
                    model_renames = {
                        "Senvion-5": "Senvion 5.0M126",
                        "Senvion-6.2": "Senvion 6.2M126",
                        "onshore": "REF-0.0",
                    }

                    if turbine_model in model_renames:
                        turbine_model = model_renames[turbine_model]

                    modelname_data = parse_model_name(turbine_model)

                    logger.debug(f"modelname_data = {modelname_data}")

                    rated_power = get_rated_power_kw(modelname_data)
                    if rated_power > 0:
                        logger.debug(
                            f"Derived rated_power = {rated_power} kW "
                            "from model name data."
                        )

                    if (rated_power or 0) == 0 and diameter > 0 and len(wind_speeds) > 0:
                        # Guess rated power by power curve
                        power_curve = calculate_power_curve(
                            wind_speeds, cp, diameter / 2, None
                        )
                        rated_power = round(max(power_curve) / 1000, 1) * 1000

                        logger.debug(
                            f"Derived rated_power = {rated_power} kW " "from power curve."
                        )

                    if rated_power > 0:
                        new_turbine_model = build_model_designation(
                            modelname_data["manufacturer"], diameter, rated_power
                        )
                        if new_turbine_model is not None:
                            turbine_model = new_turbine_model
                            logger.info(
                                f"Turbine_model reset to turbine_model = {turbine_model} "
                                "to include estimated power data"
                            )

                    type_code = f"{prefix}_{type_id:03n}"

                if prefix == "FO":
                    type_code = f"{prefix}_{type_id!s}"
                    turbine_model = type_code

                db[type_code] = generate_database_entry(
                    type_code=type_code,
                    turbine_model=turbine_model,
                    type_id=type_id,
                    height=height,
                    diameter=diameter,
                    power=rated_power,
                    ct_low=dfHeader["cT_low"][0],
                    ct_high=dfHeader["cT_high"][0],
                    wind_speeds=wind_speeds,
                    cp=cp,
                    ct=ct,
                    is_manufacturer_data=(prefix == "KN" and turbine_model[0:3] != "REF"),
                )

    with open(output_file_name, "w") as outputfile:
        json.dump(db, outputfile, indent=4)

    logger.debug(
        f"Turbine database output with {len(db)} "
        f"turbine-type{'s' if len(db) > 1 else ''} written to '{output_file_name}'"
    )


def get_knmi_typeid_from_filename(filename: str, prefix: str = "wind_turbine_") -> int:
    """Get (KNMI)-type id from filename."""
    start = filename.find(prefix) + len(prefix)
    end = filename.find(".tab")
    logger.debug(f"filename = '{filename}', start = {start}")
    return int(filename[start:end])


def generate_database_entry(
    type_code: str,
    turbine_model: Optional[str] = None,
    type_id: int = 0,
    height: float = 0.0,
    diameter: float = 0.0,
    power: float = 0.0,
    ct_low: float = 0.0,
    ct_high: float = 0.0,
    wind_speeds: Optional[List[float]] = None,
    cp: Optional[List[float]] = None,
    ct: Optional[List[float]] = None,
    is_manufacturer_data: bool = False,
):
    """Generates a dict as tubine type database entry."""
    # Ensure required fields exist with defaults if necessary
    if ct is None:
        ct = []
    if cp is None:
        cp = []
    if wind_speeds is None:
        wind_speeds = []
    processed_specs = {
        "turbine_model": turbine_model or type_code,
        "type_id": type_id or 0,
        "height": height or 0.0,
        "diameter": diameter or 0.0,
        "rated_power": power or 0.0,
        "additional_params": {
            "radius (m)": diameter / 2 or 0.0,
            "z_height (m)": height or 0,
            "cT_low (-)": ct_low or 0.0,
            "cT_high (-)": ct_high or 0.0,
        },
        "wind_speeds": wind_speeds,
        "cp": cp,
        "ct": ct,
        "is_manufacturer_data": is_manufacturer_data,
    }

    return processed_specs
