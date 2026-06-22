"""Module to read pandas dataframe with wind turbine location data from file."""

import contextlib
import json
import os
from typing import Optional

import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

try:
    from shapely.geometry import shape
except ImportError:
    shape = None

from ..logs import logger


def read_locationdata_as_dataframe(
    input_filename: str,
    ext: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
    write_rules: Optional[str | dict] = None,
    filter_rules: Optional[str | dict] = None,
    **kwargs,
) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a file.

    Args:
        input_filename (str):    Filename with wind turbine location data
        ext (str):               Extension used to determine reader, default: None(=auto)
        rename_rules (str|dict): Rename rules to rename columns in read data
        write_rules (str|dict):  Write rules to (conditional) write columns in read data
        filter_rules (str|dict): Filter rules to filter columns based on value
        **kwargs:                Variable named arguments (i.e. sheet_name for Excel)

    Returns:
        pandas.DataFrame with wind turbine location data

    """
    if ext is None:
        _, ext = os.path.splitext(input_filename)

    if ext.lower() in ["csv", ".csv"]:
        data = read_locationdata_from_csv_as_dataframe(input_filename)

    elif ext.lower() in ["xls", ".xls", "xlsx", ".xlsx"]:
        data = read_locationdata_from_excel_as_dataframe(input_filename, **kwargs)

    elif ext.lower() in ["json", ".json", "geojson", ".geojson"]:
        data = read_locationdata_from_geojson_as_dataframe(input_filename)

    elif ext.lower() in ["tab", ".tab"]:
        data = read_locationdata_from_tab_as_dataframe(input_filename)

    elif ext.lower() in ["txt", ".txt"]:
        data = read_locationdata_from_txt_as_dataframe(input_filename)

    elif ext.lower() in ["shp", ".shp"]:
        data = read_locationdata_from_shape_as_dataframe(input_filename)

    else:
        data = None

    data = apply_rename_rules(data, rename_rules)
    data = apply_write_rules(data, write_rules)
    data = apply_filter_rules(data, filter_rules)

    return data


def apply_rename_rules(
    data: pd.DataFrame, rename_rules: Optional[str | dict] = None
) -> pd.DataFrame:
    """Applies rename rules to rename columns in data."""
    if data is not None and rename_rules is not None:
        data = data.rename(columns=parse_rules(rename_rules))

    return data


def apply_write_rules(
    data: pd.DataFrame, write_rules: Optional[str | dict] = None
) -> pd.DataFrame:
    """Applies write rules to conditional write columns based on value."""
    # Apply rewrite rules (if applicable)
    if data is not None and write_rules is not None:
        for item_key, item_val in parse_rules(write_rules).items():
            val_dict = item_val if isinstance(item_val, dict) else {None: item_val}
            writeOnlyMissing = item_key[0] == "+"

            key = item_key[1:] if writeOnlyMissing else item_key

            for value1, value2 in val_dict.items():
                if (
                    isinstance(value2, tuple)
                    and len(value2) == 2
                    and value2[0] in data.columns
                ):
                    # Filtered write
                    filter_key, filter_value = value2
                    new_value = value1
                else:
                    # Translate
                    filter_key = key
                    filter_value = value1
                    new_value = value2

                write_method = (
                    "write only missing data"
                    if writeOnlyMissing
                    else "overwrite written data"
                )
                if filter_value is not None:
                    filter_cond = data[filter_key] == filter_value
                    if writeOnlyMissing:
                        filter_cond = (filter_cond) & pd.isna(data[key])

                    data.loc[filter_cond, key] = new_value

                    logger.info(
                        f"Write data[{key}] = {new_value} "
                        f"(where data[{filter_key}] = {filter_value}, {write_method})"
                    )
                else:
                    if writeOnlyMissing:
                        data.loc[pd.isna(data[key]), key] = new_value
                    else:
                        data[key] = new_value

                    logger.info(f"Write data[{key}] = {new_value} ({write_method})")

    return data


def apply_filter_rules(
    data: pd.DataFrame, filter_rules: Optional[str | dict] = None
) -> pd.DataFrame:
    """Applies filter rules to filter columns based on value."""
    # Apply filter rules (if applicable)
    if data is not None and filter_rules is not None:
        for collumn, value in parse_rules(filter_rules).items():
            if collumn in data:
                data = data[data[collumn] == value]
                logger.info(f"Filter data on {collumn}={value}.")
            else:
                logger.warning(
                    f"Collumn {collumn} not present in data, "
                    f"skip filtering on {collumn}={value}"
                )

    return data


def read_locationdata_from_txt_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a (wf101) TXT file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    try:
        logger.debug(f"Read inputfile '{input_filename}' as wf101.txt-file")
        data = pd.read_csv(
            input_filename,
            sep=r"\s+",
            comment="#",
            names=[
                "longitude",
                "latitude",
                "height_offset",
                "hub_height",
                "wf101_type",
                "country",
            ],
        )

        data["wf101_type"] = "FO_" + data["wf101_type"].astype(str)

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except Exception as e:
        logger.exception(f"Error reading TXT file: {e}")
        raise e


def read_locationdata_from_tab_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a (KNMI's) TAB file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    try:
        logger.debug(f"Read inputfile '{input_filename}' as tab-file")
        data = pd.read_table(input_filename, sep=r"\s+", comment="#", header=None)

        knmi_cols = ["lon", "lat", "type", "r", "z"]
        if len(data.columns) == len(knmi_cols):
            data.columns = knmi_cols
            data["type"] = [f"KN_{kn_id:03n}" for kn_id in data["type"].astype(int)]

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except Exception as e:
        logger.exception(f"Error reading TAB file: {e}")
        raise e


def read_locationdata_from_csv_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a CSV file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    try:
        logger.debug(f"Read inputfile '{input_filename}' as csv-file")
        data = pd.read_csv(input_filename)

        if len(data.columns) == 1:
            # Probably a wrong separator, let Python guess a proper separator
            data = pd.read_csv(input_filename, sep=None, engine="python")

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except pd.errors.EmptyDataError:
        logger.warning(f"Empty data error for reading CSV file {input_filename}.")
        return None
    except Exception as e:
        logger.exception(f"Error reading CSV file: {e}")
        raise e


def read_locationdata_from_excel_as_dataframe(
    input_filename: str, **kwargs
) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a Excel file.

    Args:
        input_filename (str): Filename with wind turbine location data
        **kwargs:             Variable named arguments (i.e. sheet_name for Excel)

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    try:
        logger.debug(
            f"Read inputfile '{input_filename}' as Excel-file with args = {kwargs}"
        )

        data = pd.read_excel(input_filename, **kwargs)

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except Exception as e:
        logger.exception(f"Error reading Excel file: {e}")
        raise e


def read_locationdata_from_shape_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a shape file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    if gpd is None:
        logger.error("Missing python packages: 'geopandas' not found.")
        logger.error(
            "Please run '"
            "poetry install --with geojson"
            "' to install the necessary packages for loading shapefiles."
        )

        logger.warning("Skip reading data from Shape-file.")

        return None

    try:
        logger.debug(f"Read inputfile '{input_filename}' as shape-file")
        data = gpd.read_file(input_filename)

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except Exception as e:
        logger.exception(f"Error reading Shape-file: {e}")
        raise e


def read_locationdata_from_geojson_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a GeoJSON file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data

    Raises:
        Exception: when reading data is failed
    """
    try:
        logger.debug(f"Read inputfile '{input_filename}' as geojson-file")
        with open(input_filename, "r") as input_file:
            data = json.load(input_file)

            keys = data.keys()
            known_keys = ["elements", "features"]
            elements = []
            for key in known_keys:
                if key in keys:
                    logger.debug(f"Use key '{key}' to get elements from geojson")
                    elements = data[key]
                    break

            if len(elements) == 0 and len(keys) == 2 and "type" in keys:
                key = next(iter(set(keys) - {"type"}))
                logger.debug(f"Use key '{key}' to get elements from geojson")
                elements = data[key]

            turbines = []
            for element in elements:
                props = element.get("properties") if "properties" in element else element

                geometry = element.get("geometry") if "geometry" in element else None
                if geometry is not None and shape is not None:
                    geometry = shape(geometry)

                if props.get("geometry") is None:
                    props["geometry"] = geometry

                turbines.append(props)

            data_df = pd.DataFrame(turbines)

            if "source" not in data_df.columns:
                _, data_df["source"] = os.path.split(input_filename)

            logger.info(f"Loaded {len(data_df.index)} turbines from {input_filename}")
            return data_df

    except Exception as e:
        logger.exception(f"Error reading GeoJSON file: {e}")
        raise e


def parse_rules(rules: str | dict) -> dict:
    """Parses a rules string to a dicationay."""
    if rules is None:
        return {}

    if isinstance(rules, dict):
        return rules

    syms = "'\" "
    rule_dict = {}

    rule_list = rules.split(",")
    for rule in rule_list:
        [key, val] = rule.split("=", 1)
        key = key.strip(syms)
        val = val.strip(syms)

        with contextlib.suppress(Exception):
            translate_sym = "#->"
            filter_sym = "@("
            if translate_sym in val:
                [old_value, new_value] = val.split(translate_sym)
                old_value = old_value.strip(syms)
                new_value = new_value.strip(syms)

                val = {old_value: new_value}
            elif filter_sym in val and "=" in val and val[-1] == ")":
                [new_value, filter_rule] = val[0:-1].split(filter_sym)
                new_value = new_value.strip(syms)
                filter_rule = filter_rule.strip(syms)

                [filter_key, filter_value] = filter_rule.split("=")
                val = {new_value: (filter_key, filter_value)}

        if key not in rule_dict:
            rule_dict[key] = val
        elif isinstance(rule_dict[key], dict):
            rule_dict[key].update(val)
        else:
            rule_dict[key] = {None: rule_dict[key]} | val

    if len(rule_dict) > 0:
        logger.info(f"Parsed rules: {rule_dict}")

    return rule_dict
