"""Module to read/determine turbine curves (cP, cT and power) for model designations."""

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .logs import logger
from .ModelDesignationDeriver import ModelDesignationDeriver
from .SpecsE101 import specs_enercon_e101
from .utils import get_radius, get_rated_power_kw


def read_cp_ct_power_curve_data_from_specs(
    specs: Dict[str, Any]
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Retrieve windspeed, cp, ct and power curve data for a turbine specification.

    Args:
        specs: Dictionary with turbine specifications

    Returns:
        Tuple containing:
        - windspeed: List of wind speeds in m/s
        - cp: List of power coefficients
        - ct: List of thrust coefficients
        - power: List of power outputs in kW
    """
    cp_fields = ["cp", "cps_gen"]
    ct_fields = [
        "ct_gen",
        "ct",
    ]  # Prefer Evgeny's generated ct-curve over simple general ct-curve
    power_fields = ["powerc_gen", "power_curve"]

    windspeed = specs.get("wind_speeds", [])
    cp = []
    ct = []
    power = []

    # Set NaN windspeed to empty list
    if windspeed is None or (isinstance(windspeed, float) and math.isnan(windspeed)):
        windspeed = []

    if windspeed and len(windspeed) > 0:
        for cp_field in cp_fields:
            cp = specs.get(cp_field, [])
            if cp is None or (isinstance(cp, float) and math.isnan(cp)):
                cp = []

            if len(windspeed) == len(cp):
                break

        for ct_field in ct_fields:
            ct = specs.get(ct_field, [])
            if ct is None or (isinstance(ct, float) and math.isnan(ct)):
                ct = []

            if len(windspeed) == len(ct):
                break

        for power_field in power_fields:
            power = specs.get(power_field, [])
            if power is None or (isinstance(power, float) and math.isnan(power)):
                power = []

            if len(windspeed) == len(power):
                break

        if cp and ct and len(windspeed) == len(cp) == len(ct):
            logger.debug(
                f"Found cp and ct data for {specs['model_designation']} in "
                f"turbine specs using fieldnames '{cp_field}' and '{ct_field}'"
            )

    return windspeed, cp, ct, power


def calculate_power_curve(
    wind_speeds: List[float],
    cp_values: List[float],
    radius: float,
    rated_power_kw: float,
    cutin: float = 3,
    rated_speed: float = 12,
) -> List[float]:
    """Calculate power curve data based on windspeed, cp_values and rated_power.

    Args:
        wind_speeds:    List of wind speeds in m/s
        cp_values:      List of power coefficients
        radius:         Radius of wind turbime
        rated_power_kw: Rated power of wind turbine in kW
        cutin:          Optional argument for cut-in speed,
                        used in linear ramp in simplified power curve; default: 3 m/s
        rated_speed:    Optional argument rated speed,
                        used in linear ramp in simplified power curve; default: 12 m/s

    Returns:
        power_values: List of power outputs in kW
    """
    air_density = 1.225  # Air density (kg/m^3)
    area = np.pi * radius**2
    power_values = []

    if cp_values:
        # Simplified power calculation based on Cp and rated power
        max_cp = max(cp_values)
        logger.debug(
            f"Compute simplified power calculation based on Cp and "
            f"rated_power = {rated_power_kw}kW, max(cp) = {max_cp}."
        )
        for ws, cp in zip(wind_speeds, cp_values):
            if cp > 0:
                try:
                    power_in = 0.5 * air_density * area * ws**3 / 1000
                    if rated_power_kw:
                        power = min(cp * power_in, rated_power_kw)
                    else:
                        power = cp * power_in

                    power_values.append(power)
                except (ValueError, ZeroDivisionError):
                    power_values.append(0.0)
            else:
                power_values.append(0.0)

    elif rated_power_kw > 0:
        logger.debug(
            "Create a simplified power curve based on rated power "
            "with linear ramp from cut-in to rated speed."
        )
        # Create a simplified power curve based on rated power
        # Typical cut-in at 3 m/s, rated speed at ~12 m/s
        for ws in wind_speeds:
            if ws < cutin:
                power = 0.0
            elif ws < rated_speed:
                # Linear ramp from cut-in to rated speed
                power = (ws - cutin) / (rated_speed - cutin) * rated_power_kw
            else:
                power = rated_power_kw

            power_values.append(power)

    return power_values


def get_cp_ct_power_curves(
    specs: Dict[str, Any],
    model_designation_deriver: ModelDesignationDeriver = None,
    windspeed_subset: Optional[str | List[float]] = None,
    extend_to_35ms: bool = False,
    bypass_cutout: bool = False,
) -> Tuple[List[float], List[float], List[float], List[float], str, float, float]:
    """Calculate or retrieve power curve data for a turbine specification.

    Args:
        specs:            Dictionary with turbine specifications
        model_designation_deriver: (Optional) Deriver to find closest match for
                                     wind turbines without cp/ct data
        windspeed_subset: (Optional) List of windspeeds to return for subset,
                                     string of format start:[step:]stop for range of
                                     windspeeds or None (no subset taken of data)
        extend_to_35ms:   (Optional) extend output ct/cp data to 35m/s range
        bypass_cutout:    (Optional) Use 10% decay in cp in stead of zero cp/power
                                     for extending cp/power curve to 35m/s

    Returns:
        Tuple containing:
        - ws_values: List of wind speeds in m/s
        - cp_values: List of power coefficients
        - ct_values: List of thrust coefficients
        - power_values: List of power outputs in kW
        - model_designation: The model designation as source for cp/ct data
        - cut-in: Approximated cut-in speed
        - cut-out: Approximated cut-out speed
    """
    model_designation = specs["model_designation"]

    # First try to get values directly from specs
    (
        ws_values,
        cp_values,
        ct_values,
        power_values,
    ) = read_cp_ct_power_curve_data_from_specs(specs)

    radius = get_radius(specs)
    rated_power_kw = None
    if not power_values:
        rated_power_kw = get_rated_power_kw(specs, guess_unit=False)

    if not (ws_values and cp_values and ct_values):
        # Didn't manage to collect all necessary data
        missing_fields = []
        if not ws_values:
            missing_fields.append("wind_speeds")
        if not cp_values:
            missing_fields.append("cp")
        if not ct_values:
            missing_fields.append("ct")
        logger.warning(
            f"Error collecting necessary data for model designation "
            f"'{specs['model_designation']}': "
            f"missing: {', '.join(str(field) for field in missing_fields)}"
        )

        # Try to match an alternative model designation to provide cp/ct curves
        if model_designation_deriver is not None:
            alternative_model_designation = (
                model_designation_deriver.get_closest_powered_windturbine_with_ct(
                    specs["model_designation"]
                )
            )
            if alternative_model_designation != specs["model_designation"]:
                logger.info(
                    f"Using fallback {alternative_model_designation} as source "
                    f"for cp/ct/power-data for {specs['model_designation']}"
                )
                fallback = model_designation_deriver.get_specs(
                    alternative_model_designation
                )
                return get_cp_ct_power_curves(
                    fallback,
                    matcher=None,
                    windspeed_subset=windspeed_subset,
                    extend_to_35ms=extend_to_35ms,
                    bypass_cutout=bypass_cutout,
                )

        # Use Enercon E101 as reference if there is no valid cp or ct data
        fallback = specs_enercon_e101()
        model_designation = fallback["turbine_model"]

        logger.info(
            f"Using fallback {model_designation} as source for cp/ct/power-data "
            f"for {specs['model_designation']}"
        )

        ws_values = fallback["wind_speeds"]
        cp_values = fallback["cp"]
        ct_values = fallback["ct"]
        power_values = fallback["power_curve"]

    if not power_values:
        power_values = calculate_power_curve(ws_values, cp_values, radius, rated_power_kw)

    # Derive cut in based on zero cp for low wind_speeds
    cut_in = next((idx for idx, cp in enumerate(cp_values) if cp > 0), None)
    cut_in = ws_values[cut_in - 1 if cut_in > 0 else 0]

    max_ct = max(ct_values)
    max_power = max(power_values)
    ws_max_ct = next((ws for ws, ct in zip(ws_values, ct_values) if ct == max_ct), None)
    ws_max_pwr = next(
        (ws for ws, pwr in zip(ws_values, power_values) if pwr == max_power), None
    )

    # Derive cut out based on zero ct or power for high wind_speeds
    cut_out = next(
        (
            idx
            for idx, (ws, ct, pwr) in enumerate(zip(ws_values, ct_values, power_values))
            if (ct == 0 and ws > ws_max_ct) or (pwr == 0 and ws > ws_max_pwr)
        ),
        None,
    )
    cut_out = ws_values[cut_out - 1 if cut_out else -1]

    logger.debug(
        f"For model_designation={model_designation} approximated "
        f"cut_in={cut_in}, cut_out={cut_out}"
    )

    ws_range_start = None
    ws_range_stop = None
    ws_range_step = None

    if isinstance(windspeed_subset, str):
        ws_range = windspeed_subset.split(":")
        if len(ws_range) in [2, 3]:
            if ws_range[0].lower() in ["cut-in", "cutin", "cut_in"]:
                ws_range_start = cut_in
            elif ws_range[0].isdigit():
                ws_range_start = float(ws_range[0])

            try:
                if len(ws_range) == 3:
                    ws_range_step = float(ws_range[1])
            except ValueError:
                pass

            if ws_range[-1].lower() in ["cut-out", "cutout", "cut_out"]:
                ws_range_stop = cut_out
            elif ws_range[-1].isdigit():
                ws_range_stop = float(ws_range[-1])

    if ws_range_start and ws_range_stop:
        if not ws_range_step:
            ws_range_step = 1

        logger.debug(
            f"Create windspeed subset range: start={ws_range_start}, "
            f"stop={ws_range_stop}, step={ws_range_step}"
        )

        windspeed_subset = [cut_in, cut_out] + [
            x * ws_range_step
            for x in range(
                math.floor(ws_range_start / ws_range_step),
                math.ceil(ws_range_stop / ws_range_step),
            )
        ]
        windspeed_subset = sorted(set(windspeed_subset))

    if isinstance(windspeed_subset, list):
        if len(windspeed_subset) < len(ws_values):
            cp_values_subset = np.interp(windspeed_subset, ws_values, cp_values).tolist()
            ct_values_subset = np.interp(windspeed_subset, ws_values, ct_values).tolist()
            if len(power_values) > 0:
                power_values_subset = np.interp(
                    windspeed_subset, ws_values, power_values
                ).tolist()
            else:
                power_values_subset = []

            ws_values = windspeed_subset
            cp_values = cp_values_subset
            ct_values = ct_values_subset
            power_values = power_values_subset
        else:
            logger.debug(
                f"Creating a windspeed subset of the ct/cp data yields "
                f"{len(windspeed_subset)} records, while the source contains "
                f"only {len(ws_values)} records."
                "Don't increase data points when creating a subset."
            )

    if extend_to_35ms:
        # Ensure there's data for wind speeds up to 35 m/s
        max_ws = max(ws_values) if ws_values else 0
        if max_ws < 35:
            # Get the last values
            last_wind_speed = max_ws
            last_cp = cp_values[-1] if cp_values else 0.0
            last_ct = ct_values[-1] if ct_values else 0.0
            last_power = power_values[-1] if power_values else 0.0

            # Progressive decay for higher wind speeds
            for ws in range(int(last_wind_speed) + 1, 36):
                ws_values.append(float(ws))

                # Gradually decrease coefficients
                steps_beyond_max = ws - last_wind_speed
                decay_factor = 0.9**steps_beyond_max  # 10% decay per step

                # Assume ws > cut-out; so cp/power need to be zero
                ct_values.append(last_ct * decay_factor)
                if bypass_cutout:
                    cp_values.append(last_cp * decay_factor)
                    power_values.append(
                        last_power
                    )  # Power typically stays constant at rated value
                else:
                    cp_values.append(0)
                    power_values.append(0)

    # Make sure all lists are the same length by truncating to shortest
    min_length = min(
        len(ws_values),
        len(cp_values),
        len(ct_values),
        len(power_values) if power_values else float("inf"),
    )
    ws_values = ws_values[:min_length]
    cp_values = cp_values[:min_length]
    ct_values = ct_values[:min_length]

    # Handle case where power_values might be empty
    power_values = [0.0] * min_length if not power_values else power_values[:min_length]

    return (
        ws_values,
        cp_values,
        ct_values,
        power_values,
        model_designation,
        cut_in,
        cut_out,
    )
