"""Module to read pandas dataframe with wind turbine location data from file."""

import json
import os
from typing import Optional

import pandas as pd

from ..logs import logger
from ..Turbine import Turbine


def read_locationdata_as_dataframe(
    input_filename: str,
    ext: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a file.

    Args:
        input_filename (str):    Filename with wind turbine location data
        ext (str):               Extension used to determine reader, default: None(=auto)
        rename_rules (str|dict): Rename rules to rename columns in read data

    Returns:
        pandas.DataFrame with wind turbine location data
    """
    if ext is None:
        _, ext = os.path.splitext(input_filename)

    if ext.lower() in ["csv", ".csv"]:
        data = read_locationdata_from_csv_as_dataframe(input_filename)

    elif ext.lower() in ["json", ".json", "geojson", ".geojson"]:
        data = read_locationdata_from_geojson_as_dataframe(input_filename)

    elif ext.lower() in ["tab", ".tab"]:
        data = read_locationdata_from_tab_as_dataframe(input_filename)

    elif ext.lower() in ["txt", ".txt"]:
        data = read_locationdata_from_txt_as_dataframe(input_filename)

    else:
        data = None

    # Apply rename rules (if applicable)
    if data is not None:
        data = data.rename(columns=parse_rename_rules(rename_rules))

    return data


def read_locationdata_from_txt_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a (wf101) TXT file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data
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
        logger.error(f"Error reading TXT file: {e}")
        logger.exception("Detailed error information:")


def read_locationdata_from_tab_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a (KNMI's) TAB file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data
    """
    try:
        logger.debug(f"Read inputfile '{input_filename}' as tab-file")
        data = pd.read_table(input_filename, sep=r"\s+", comment="#", header=None)

        knmi_cols = ["lon", "lat", "type", "r", "z"]
        if len(data.columns) == len(knmi_cols):
            data.columns = knmi_cols
            data["type"] = f"KN_{int(data['type'])}"

        if "source" not in data.columns:
            _, data["source"] = os.path.split(input_filename)

        logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")
        return data

    except Exception as e:
        logger.error(f"Error reading TAB file: {e}")
        logger.exception("Detailed error information:")


def read_locationdata_from_csv_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a CSV file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data
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

    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        logger.exception("Detailed error information:")


def read_locationdata_from_geojson_as_dataframe(input_filename: str) -> pd.DataFrame:
    """Reads dataframe with wind turbine location data from a GeoJSON file.

    Args:
        input_filename (str): Filename with wind turbine location data

    Returns:
        pandas.DataFrame with wind turbine location data
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
                turbines.append(Turbine.from_dict(props))

            data_df = pd.DataFrame(turbines)

            if "source" not in data_df.columns:
                _, data_df["source"] = os.path.split(input_filename)

            logger.info(f"Loaded {len(data_df.index)} turbines from {input_filename}")
            return data_df

    except Exception as e:
        logger.error(f"Error reading GeoJSON file: {e}")
        logger.exception("Detailed error information:")


def parse_rename_rules(rules: str | dict) -> dict:
    """Parses a rename rules string to a dicationay."""
    if rules is None:
        return {}

    if isinstance(rules, dict):
        return rules

    syms = "'\" "
    rule_dict = {}

    rule_list = rules.split(",")
    for rule in rule_list:
        [key, value] = rule.split("=")
        rule_dict[key.strip(syms)] = value.strip(syms)

    if len(rule_dict) > 0:
        logger.info(f"Parsed column rename rules: {rule_dict}")

    return rule_dict
