"""Utility for dict-list handling for radius, diameter, power."""

import contextlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logs import logger


def print_processing_status(
    counter: int,
    total: int,
    label: str = "Processing turbines",
    step: int = 10,
    thresshold: int = 1000,
):
    """Print status during processing of items (i.e. turbines).

    Args:
        counter (int):    Counter of current item processing
        total (int):      Total number of items to process
        label (str):      Label used to describe activity
        step (int):       Print output for each step-increment in percentage
        thresshold (int): Minimal number of items before printing status

    """
    with contextlib.suppress(Exception):
        if total > thresshold:
            percent_prev = float(counter - 1) / total
            percent = float(counter) / total

            if int(percent_prev * step) != int(percent * step):
                msg = f"{label}: {counter} out of {total} " f"({int(percent*100)}%)"
                logger.log(logger.getEffectiveLevel(), f"[STATUS] {msg}")


def unify_file_list(file_or_files: Path | List[Path] | str | List[str]) -> List[Path]:
    """Unifies a a str, Path or list[str|Path] to a list[Path].

    Args:
        file_or_files: One or more files represented as string or Path

    Returns:
        A list of Paths representing all files
    """
    if isinstance(file_or_files, (list, tuple)):
        specs_file_list = [
            file if isinstance(file, Path) else Path(file) for file in file_or_files
        ]
    elif isinstance(file_or_files, Path):
        specs_file_list = [file_or_files]
    elif isinstance(file_or_files, str):
        specs_file_list = [Path(file_or_files)]
    else:
        logger.warning(
            f"Unexpected file_or_files provided; "
            f"type(file_or_files) = {type(file_or_files)}, "
            f"file_or_files = {file_or_files}."
        )
        specs_file_list = file_or_files

    return specs_file_list


def zero_to_none(data: float) -> float:
    """Converts data to None if it has zero value.

    Args:
        data (float): The data to check

    Returns:
        The data (or None if the data was 0)
    """
    if data is None:
        return data

    try:
        if not isinstance(data, float):
            data = float(data)
    except (ValueError, TypeError):
        data = None

    return None if data == 0 else data


def empty_to_none(data):
    """Converts data to None if it has length zero.

    Args:
        data: The data to check

    Returns:
        The data (or None if the data was 0)
    """
    if data is None:
        return data

    return None if len(data) == 0 else data


def get_value_from_dict(keys: str | List[str], data: Dict, default: None):
    """Gets the value from data[key] where key is an element of the keys list.

    Args:
        keys:    List of keys to check (in order)
        data:    The dict-like object to fetch the key from
        default: Default value to return, default None

    Returns:
        A valid (not None, empty or NaN) value of dict[key] for key in keys,
        otherwise default
    """
    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if data is not None and key in data:
            value = data[key]
            if value not in [None, "", "NaN"]:
                return value

    return default


def get_float_from_dict(
    keys: str | List[str],
    data: Dict,
    default: float = 0.0,
    require_positive: bool = False,
) -> Tuple[float, str]:
    """Gets the float value from data[key] where key is an element of the keys list.

    Args:
        keys:             List of keys to check (in order)
        data:             The dict-like object to fetch the key from
        default:          Default value to return, default 0.0
        require_positive: Flag indicating if match should be positive

    Returns:
        output:   A valid (not None, empty or NaN) float value of data[key]
                  for key in keys, otherwise default
        key:      The matched key
    """
    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        if data is not None and key in data:
            value = data[key]
            if value not in [None, "", "NaN"]:
                try:
                    output = float(value)
                    if not require_positive or (require_positive and output > 0):
                        return output, key
                except (ValueError, TypeError):
                    pass

    return default, None


def get_float_from_dict_list(
    keys: str | List[str],
    dict_list: List[Dict],
    default: float = 0.0,
    require_positive: bool = False,
) -> Tuple[float, str]:
    """Gets the float value from data[key].

       Where key is an element of the keys list and dict an element of dict list

    Args:
        keys:             List of keys to check (in order)
        dict_list:        A list of dict-like object to fetch the key from
        default:          Default value to return, default 0.0
        require_positive: Flag indicating if match should be positive

    Returns:
        output:  A valid (not None, empty or NaN) float value of dict[key]
                 for key in keys and dict in dict_list, otherwise default
        key:     The matched key
    """
    for data in dict_list:
        value, key = get_float_from_dict(keys, data, default, require_positive)
        if value and value > 0:
            return value, key

    return default, None


def get_radius_from_dict(data: Dict, default: float = 0.0) -> float:
    """Try to get field like radius from dict (as alternative diameter will be used).

    Args:
        data (dict):      The dict-like object to fetch the readius from
        default (float):  Default value to return, default 0.0

    Returns:
        A valid (not None, empty or NaN) float value for radius, otherwise default
    """
    radius, _ = get_float_from_dict(
        ["radius", "radius (m)"], data, default, require_positive=True
    )
    if radius and radius > 0:
        return radius

    diameter, _ = get_float_from_dict(
        [
            "diameter",
            "diameter (m)",
            "rotor_diameter",
            "rotor diameter",
            "rotor diameter (m)",
            "Rotor diameter (m)",
            "Rotordiameter (m)",
            "diam",
        ],
        data,
        default,
        require_positive=True,
    )

    if diameter is not None:
        return diameter / 2

    return default


def get_radius_from_dict_list(dict_list: List[Dict], default: float = 0.0) -> float:
    """Try to get field like radius from dict (as alternative diameter will be used).

    Args:
        dict_list (list[dict]): A list of dict-like object to fetch the readius from
        default (float):        Default value to return, default 0.0

    Returns:
        A valid (not None, empty or NaN) float value for radius, otherwise default
    """
    for data in dict_list:
        radius = get_radius_from_dict(data, default)
        if radius and radius > 0:
            return radius

    return default


def get_diameter(specs: Dict | List[Dict], default: float = 0.0) -> float:
    """Try to get field like diameter from dict or a dict_list.

       Note: as alternative radius will be used.

    Args:
        specs (dict or list[dict]): A list or dict-like object to fetch the diameter from
        default (float): Default value to return

    Returns:
        A valid (not None, empty or NaN) float value for diameter, otherwise default
    """
    radius = get_radius(specs, default)
    if radius is not None:
        return 2 * radius

    return None


def get_radius(specs: Dict | List[Dict], default: float = 0.0) -> float:
    """Try to get field like radius from dict or a dict_list.

       Note: as alternative diameter will be used.

    Args:
        specs (dict or dict_list): A list or dict-like object to fetch the radius from
        default (float):           Default value to return, default 0.0

    Returns:
        A valid (not None, empty or NaN) float value for radius, otherwise default
    """
    if isinstance(specs, list):
        return get_radius_from_dict_list(specs, default)

    return get_radius_from_dict(specs, default)


def get_height(specs: Dict | List[Dict], default: float = 0.0) -> float:
    """Try to get field like height from dict or a dict_list.

    Args:
        specs (dict or dict_list): A list or dict-like object to fetch the readius from
        default (float):           Default value to return, default 0.0

    Returns:
        A valid (not None, empty or NaN) float value for height, otherwise default
    """
    fields = [
        "hubheight",
        "hub_height",
        "hub height",
        "Hub height",
        "hub height (m)",
        "Hub height",
        "Hub height (m)",
        "height",
        "z_height (m)",
        "z_height",
        "ash",
        "hoogte_paa",
        "Navhöjd (m)",
    ]

    if isinstance(specs, list):
        height, _ = get_float_from_dict_list(
            fields, specs, default, require_positive=True
        )
    else:
        height, _ = get_float_from_dict(fields, specs, default, require_positive=True)

    return height


def get_rated_power_kw(specs: Dict[str, Any] | List[Dict], default: float = 0) -> float:
    """Get rated power of wind turbine, given in kW.

    Args:
        specs (dict):    Dictionary with turbine specifications
        default (float): Default value to return, default 0.0

    Returns:
        Rated power (in kW)
    """
    power_fields = [
        "rated_power",
        "rated_power_kw",
        "rated_power_mw",
        "rated power",
        "Rated power",
        "power_rating",
        "power_rating_kw",
        "power_rating_mw",
        "power",
        "kw",
        "power_kw",
        "power_mw",
        "vermogen_m",
        "P_rated",
        "nominal_power",
        "nominal power",
        "nominal power (kW)",
        "capacity",
        "Capacity (kW)",
        "Capacity",
        "Maxeffekt (MW)",
    ]

    diameter = None
    if isinstance(specs, list):
        rated_power, key = get_float_from_dict_list(
            power_fields, specs, default, require_positive=True
        )
        radius = get_radius_from_dict_list(specs, None)
        if radius is not None:
            diameter = 2 * radius
    else:
        rated_power, key = get_float_from_dict(
            power_fields, specs, default, require_positive=True
        )
        radius = get_radius_from_dict(specs, None)
        if radius is not None:
            diameter = 2 * radius

    unit = None
    if isinstance(key, str):
        key = key.upper()
        if "MW" in key:
            unit = "MW"
        elif "KW" in key:
            unit = "KW"

    return power_to_kw(rated_power, known_unit=unit, diameter=diameter) or default


def get_installed_power(specs: Dict[str, Any] | List[Dict], default: float = 0) -> float:
    """Get installed power of wind turbine/windfarm.

    Args:
        specs (dict):    Dictionary with turbine specifications
        default (float): Default value to return, default 0.0

    Returns:
        Installed power
    """
    power_fields = [
        "installed_power",
        "installed_power_mw",
        "installed_power_kw",
        "installed power",
        "Installed power",
        "Installed power [MW]",
        "Installed power [KW]",
        "installed_capacity",
        "installed capacity",
        "Installed capacity [MW]",
        "Installed capacity [KW]",
        "Total power",
        "Total power [kW]",
        "Total power [MW]",
    ]

    if isinstance(specs, list):
        installed_power, key = get_float_from_dict_list(
            power_fields, specs, default, require_positive=True
        )
    else:
        installed_power, key = get_float_from_dict(
            power_fields, specs, default, require_positive=True
        )

    return installed_power or default


def power_to_kw(
    power: float, known_unit: Optional[str] = None, diameter: Optional[float] = None
) -> float:
    """Guess if a given power is given in kW or MW and convert it to kW.

    Args:
        power: A given power of a wind turbine
        known_unit: Optional, the unit (kW or MW) of the power
            (otherwise it will be guessed by power-value)
        diameter: Optional, the diameter of the wind turbine

    Returns:
        Power in kW
    """
    # Try to convert possible non-float typed power to float
    if not isinstance(power, float):
        try:
            power = float(power)
        except TypeError:
            return power

    # Try to convert possible non-float typed diameter to float
    if diameter is not None and not isinstance(diameter, float):
        with contextlib.suppress(TypeError):
            diameter = float(diameter)

    # Guess based on large_turbine flag,
    # i.e. power of large turbines assumed to be in MW scale
    if known_unit is None and diameter is not None:
        if diameter >= 35 and power < 1:
            known_unit = "MW"
        elif power < 450:
            known_unit = "MW" if diameter >= 60 else "kW"

    if known_unit is None:
        if power > 1e6:
            known_unit = "W"
        elif power > 1e3:
            known_unit = "kW"

    if known_unit is not None:
        if known_unit.upper() == "KW":
            return power
        if known_unit.upper() == "MW":
            return power * 1000
        if known_unit.upper() == "W":
            return power / 1000

    # Start guessing of unit of power,
    # low power is likely in MW (common industry standard)
    if power > 0 and power < 20:  # Most turbines are under 20 MW
        return power * 1000  # Convert MW to kW

    return power  # Assume already in kW
