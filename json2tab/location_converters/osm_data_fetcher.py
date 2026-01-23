"""Module with OpenStreetMap wind turbine location data fetcher."""

import contextlib
import json
import os
import re

try:
    import requests
except ImportError:
    requests = None
from typing import Optional, Tuple

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..location_converters.overpass_query_builder import build_query
from ..logs import logger
from ..Turbine import Turbine
from ..utils import power_to_kw
from .cleanup_short_distance_turbines import cleanup_short_distance_turbines


def osm_data_fetcher(
    output_filename: str,
    input_filename: Optional[str] = None,
    query_windturbine: bool = True,
    query_windfarm: bool = True,
) -> pd.DataFrame:
    """OpenStreetMap wind turbine location data fetcher.

    Args:
        output_filename (str): Filename to write the processed OSM wind turbine data to
        input_filename (str):  (Optional) Filename of overpass_output.json to bypass
                               OverpassAPI call (i.e. use local/cached OSM data)
        query_windturbine (bool): Query wind_turbine data from OSM (default: True)
        query_windfarm (bool):    Query wind_farm data from OSM (default: True)

    Returns:
        pandas.DataFrame with windturbine location data
    """
    print(
        f"OSM (windturbine location) Data Fetcher ({input_filename} -> {output_filename})"
    )

    logger.debug(f"input filename: {input_filename}")
    logger.debug(f"output filename: {output_filename}")

    output_filename_base = os.path.splitext(output_filename)[0]

    overpass_dump_file = (
        f"{output_filename_base}.overpass_output_"
        f"windturbine={str(query_windturbine).lower()}_"
        f"windfarm={str(query_windfarm).lower()}.json"
    )

    output_filename_turbine = f"{output_filename_base}.turbines.csv"
    output_filename_windfarm = f"{output_filename_base}.windfarms.csv"

    if requests is not None:
        if not os.path.exists(output_filename):
            data = None

            if input_filename is not None and os.path.exists(input_filename):
                logger.debug(
                    f"Process inputfile '{input_filename}' as Overpass API results"
                )
                with open(input_filename, "r") as input_file:
                    data = json.load(input_file)

            if data is None and os.path.exists(overpass_dump_file):
                logger.debug(
                    f"Process dumpfile '{overpass_dump_file}' as Overpass API results"
                )
                with open(overpass_dump_file, "r") as input_file:
                    data = json.load(input_file)

            if not data:
                # Overpass API URL
                overpass_url = "http://overpass-api.de/api/interpreter"
                logger.debug(f"Using overpass API url: '{overpass_url}'")

                # Overpass QL query for wind turbines and windfarms
                overpass_query = build_query(
                    windturbine=query_windturbine, windfarm=query_windfarm
                )
                logger.debug(f"Using overpass query: '{overpass_query}'")

                print("Executing request to fetch OSM data...")

                response = requests.get(overpass_url, params={"data": overpass_query})
                data = response.json()

                # Dump overpass api response data to file
                with open(overpass_dump_file, "w") as dump_file:
                    json.dump(data, dump_file, indent=2)
                    logger.debug(
                        f"Dumped overpass query output to '{overpass_dump_file}'"
                    )

                print("... got response for query")

            if not data:
                logger.error("No data to process, reading aborted.")
                return None

            # Initialize a list to hold the data
            turbines = []
            windfarms = []

            logger.info(f"Received {len(data['elements'])} elements")

            osm_types = ["relation", "node", "way"]
            elements = {}

            for osm_type in osm_types:
                elements[osm_type] = [
                    nwr for nwr in data["elements"] if nwr["type"] == osm_type
                ]
                logger.info(f"Found {len(elements[osm_type])} {osm_type}s in data")

            elements["node_wo_tags"] = [
                n for n in elements["node"] if n.get("tags") is None
            ]
            logger.info(f"Found {len(elements['node_wo_tags'])} nodes w/o tags in data")

            # Process each element, grouped by osm_type
            for osm_type in osm_types:
                logger.info(f"Start processing osm type {osm_type}")

                for element in elements[osm_type]:
                    if element.get("tags") is None:
                        if element.get("windturbine_via_wf"):
                            element["tags"] = {}
                        else:
                            # Skip elements without tags
                            continue

                    # Basic turbine information
                    osm_id = get_osm_id(element)
                    name = get_osm_name(element)

                    # Parse manufacturer and turbine type model
                    manufacturer = element["tags"].get("manufacturer")
                    model_type = get_model_type_from_element(element)

                    # Parse wind turbine specs
                    hub_height = get_hub_height_from_element(element)
                    rotor_diameter = parse_length(element["tags"].get("rotor:diameter"))
                    rated_power = parse_power_to_kw(
                        element["tags"].get("generator:output:electricity")
                    )

                    if isinstance(rotor_diameter, str):
                        logger.warning(
                            f"Failed to parse rotor_diameter='{rotor_diameter}' as "
                            f"valid diameter for {osm_id}"
                        )
                        rotor_diameter = None

                    # Parse some additional optional information
                    operator = element["tags"].get("operator")
                    start_date = element["tags"].get("start_date")
                    site = element["tags"].get("site")
                    is_offshore = element["tags"].get("offshore")

                    # Read more data from linked wind_farm
                    windfarm_osm_id = element.get("windfarm_osm_id")
                    if windfarm_osm_id is not None:
                        windfarm = get_element_by_id(
                            elements, "relation", windfarm_osm_id
                        )

                        if windfarm is not None:
                            if site is None:
                                site = get_osm_name(windfarm)

                            # Append relation info
                            site = f"{site} [{get_osm_id(windfarm)}]"
                            manufacturer = manufacturer or windfarm["tags"].get(
                                "manufacturer"
                            )
                            model_type = model_type or get_model_type_from_element(
                                windfarm
                            )
                            hub_height = hub_height or get_hub_height_from_element(
                                windfarm
                            )
                            rated_power = rated_power or element.get("rated_power_via_wf")
                            start_date = start_date or windfarm["tags"].get("start_date")

                    turbine = Turbine(
                        turbine_id=osm_id,
                        name=name,
                        latitude=None,  # lat/lon set before adding to turbine line
                        longitude=None,  # lat/lon set before adding to turbine line
                        manufacturer=manufacturer,
                        type=model_type,
                        hub_height=hub_height,
                        radius=float(rotor_diameter) / 2
                        if rotor_diameter is not None
                        else None,
                        diameter=rotor_diameter,
                        power_rating=rated_power,
                        operator=operator,
                        start_date=start_date,
                        wind_farm=site,
                        is_offshore=is_offshore,
                        source="OSM",
                    )

                    if is_windturbine(element) and element["type"] == "relation":
                        # Don't trust this element as windturbine, process as windfarm
                        windfarm = process_wf_info(turbine.to_dict(), element, elements)

                        # Append to the windfarm list
                        windfarms.append(windfarm)

                    elif is_windturbine(element) or element.get("windturbine_via_wf"):
                        if not is_windturbine(element):
                            logger.info(
                                f"Interpreted node '{turbine.name}' ({osm_id}) "
                                "as windturbine due to its wind_turbine "
                                f"relation to '{turbine.wind_farm}'"
                            )

                        # Add location information
                        turbine.latitude, turbine.longitude = get_lat_lon_from_element(
                            element, elements
                        )

                        # Append to the windturbine list
                        turbines.append(turbine)

                    elif (
                        element["tags"].get("power") == "plant"
                        and element["tags"].get("plant:source") == "wind"
                    ):
                        # Parse windfarm information
                        windfarm = process_wf_info(turbine.to_dict(), element, elements)

                        # Append to the windfarm list
                        windfarms.append(windfarm)

            # Create a DataFrame with turbines
            df_turbines = pd.DataFrame(turbines)
            logger.info(f"Generated dataframe with {len(df_turbines.index)} turbines")
            if len(df_turbines.index) > 0:
                save_dataframe(df_turbines, output_filename_turbine)

            if len(windfarms) > 0 or query_windfarm:
                df_windfarms = pd.DataFrame(windfarms)
                logger.info(
                    f"Generated dataframe with {len(df_windfarms.index)} "
                    f"windfarms with "
                    f"{int(sum(df_windfarms['n_turbines'].fillna(0)))} turbines "
                    f"({int(sum(df_windfarms['mapped_turbines'].fillna(0)))} "
                    "included in turbines)."
                )
                save_dataframe(df_windfarms, output_filename_windfarm)

            # Cleanup short distance turbines
            df_turbines, min_dist, _ = cleanup_short_distance_turbines(df_turbines)
            logger.info(
                f"Filtered dataframe to {len(df_turbines.index)} turbines with "
                f"at least ~{int(111 * 1000 * min_dist)} meter "
                f"(i.e. {min_dist} degree) distance."
            )

            save_dataframe(df_turbines, output_filename)
            data = df_turbines

        else:
            data = read_locationdata_as_dataframe(output_filename)

        return data

    print(
        "Python package 'requests' not found, "
        "please load this optional package to run OsmDataFetcher."
    )
    print("Please run")
    print("    poetry install --with osmrequest")
    print("to install the necessary packages for OsmDataFetcher")

    return None


def process_wf_info(windfarm, element, elements):
    """Process windfarm info from osm element."""
    n_turbines = parse_turbines_from_str(element["tags"].get("seamark:information"))

    if n_turbines is not None and not isinstance(n_turbines, int):
        logger.warning(f"Cannot parse number of turbines from '{n_turbines}'")
        n_turbines = None

    installed_capacity = parse_power_to_kw(
        element["tags"].get("plant:output:electricity"), unit_fallback="MW"
    )

    mapped_turbines = None

    if installed_capacity is not None and not isinstance(installed_capacity, float):
        logger.warning(f"Cannot parse installed capacity from '{installed_capacity}'")
        installed_capacity = None

    if element["type"] == "relation":
        if is_windturbine(element):
            node_ids = [mbr["ref"] for mbr in element["members"] if mbr["type"] == "node"]
            way_ids = [mbr["ref"] for mbr in element["members"] if mbr["type"] == "way"]
            wf_turbines = [n for n in elements["node"] if n["id"] in set(node_ids)] + [
                w for w in elements["way"] if w["id"] in set(way_ids)
            ]
        else:
            wf_ids = [
                mbr["ref"]
                for mbr in element["members"]
                if mbr["type"] == "node" and mbr["role"] in ["generator", "wind_turbine"]
            ]
            mbr_ids = [
                mbr["ref"]
                for mbr in element["members"]
                if mbr["type"] == "node" and mbr["role"] in ["", "inner", "node"]
            ]
            wf_turbines = [
                n
                for n in elements["node"]
                if n["id"] in set(mbr_ids) and is_windturbine(n) or n["id"] in set(wf_ids)
            ]

        n_turbines = len(wf_turbines)
        mapped_turbines = n_turbines

        if n_turbines > 0 and installed_capacity is not None:
            power_rating = installed_capacity / n_turbines
        else:
            power_rating = None

        if power_rating is None:
            power_rating = parse_power_to_kw(
                element["tags"].get("generator:output:electricity")
            )

            if n_turbines > 7 and power_rating is not None:
                power_rating_v2 = power_rating / n_turbines
                if power_rating_v2 > 2e3:
                    logger.info(
                        f"Windfarm {get_osm_id(element)} with "
                        f"{n_turbines} turbines has unlikely high rated power "
                        f"(={power_rating} kW), "
                        "lets assume it is installed capacity; "
                        f"i.e. reset rated power to {power_rating_v2} kW"
                    )
                    power_rating = power_rating_v2

        for wf_turbine in wf_turbines:
            wf_turbine["windfarm_osm_id"] = element["id"]
            wf_turbine["windturbine_via_wf"] = True

            if power_rating is not None:
                wf_turbine["rated_power_via_wf"] = power_rating

            if is_windturbine(element):
                logger.info(
                    f"Relation '{get_osm_id(element)}' seems to be an as "
                    "wind_turbine tagged wind_farm; "
                    f"mark member '{get_osm_id(wf_turbine)}' as wind_turbine."
                )
                # Copy windfarm info to members; skip this relation
                if "tags" not in wf_turbine:
                    wf_turbine["tags"] = {}

                for key, val in element["tags"].items():
                    if (
                        key not in ["plant:source", "plant:output:electricity"]
                        and key not in wf_turbine["tags"]
                    ):
                        wf_turbine["tags"][key] = val

                if "power" not in wf_turbine["tags"]:
                    wf_turbine["tags"]["power"] = "generator"

                if "generator:source" not in wf_turbine["tags"]:
                    wf_turbine["tags"]["generator:source"] = "wind"

                if (
                    "generator:output:electricity" not in wf_turbine["tags"]
                    and power_rating is not None
                ):
                    wf_turbine["tags"][
                        "generator:output:electricity"
                    ] = f"{power_rating} kW"

    windfarm["n_turbines"] = n_turbines
    windfarm["installed_capacity"] = installed_capacity
    windfarm["mapped_turbines"] = mapped_turbines

    if windfarm["wind_farm"] == "wind_farm":
        windfarm["wind_farm"] = None

    if mapped_turbines != n_turbines:
        # Add location for this windfarm
        windfarm["latitude"], windfarm["longitude"] = get_lat_lon_from_element(
            element, elements
        )

    return windfarm


def get_osm_id(element) -> str:
    """Gets the id of an OSM element."""
    return f"{element['type']}-{element['id']}"


def get_osm_name(element) -> str:
    """Gets name from OSM element."""
    name = element["tags"].get("name")
    alt_name = element["tags"].get("alt_name")

    if alt_name is not None:
        if str(alt_name).lower().startswith(str(name).lower()):
            name = alt_name
        else:
            name = f"{name} ({alt_name})"

    return name


def get_lat_lon_from_element(element, elements) -> Tuple[float, float]:
    """Gets lat/lon from OSM element."""
    if element["type"] == "node":
        return get_lat_lon_from_node(element)

    if element["type"] == "way":
        return get_lat_lon_from_way(element, elements)

    if element["type"] == "relation":
        return get_lat_lon_from_relation(element, elements)

    return None, None


def get_model_type_from_element(element) -> str:
    """Gets model_type from osm element."""
    # Parse turbine type model
    model_type = element["tags"].get("model")

    if model_type in [None, ""]:
        # Note manufacturer:type is deprecated
        model_type = element["tags"].get("manufacturer:type")

    if model_type in [None, ""]:
        model_type = element["tags"].get("generator:model")

    return model_type


def get_hub_height_from_element(element) -> float:
    """Gets hub height from osm element."""
    hub_height = parse_length(element["tags"].get("height:hub"))
    if hub_height in [None, "", 0]:
        # est_hub:height is estimated hub:height
        hub_height = parse_length(element["tags"].get("est_height:hub"))

    if hub_height in [None, "", 0]:
        # Use height as fallback to get hub height information of turbine
        hub_height = parse_length(element["tags"].get("height"))

    return hub_height


def get_lat_lon_from_node(node) -> Tuple[float, float]:
    """Gets lat/lon from OSM node."""
    lat = node.get("lat")
    lon = node.get("lon")

    return lat, lon


def get_lat_lon_from_way(way, elements) -> Tuple[float, float]:
    """Gets lat/lon from OSM way."""
    # Fix lat/lon of way by taking the average of the lat/lons of nodes
    nodes = [n for n in elements["node_wo_tags"] if n["id"] in set(way["nodes"])]
    if len(nodes) != len(set(way["nodes"])):
        nodes = [n for n in elements["node"] if n["id"] in set(way["nodes"])]

    lat_lon = [get_lat_lon_from_node(node) for node in nodes]

    lat = sum(lat for lat, lon in lat_lon) / len(nodes) if len(nodes) > 0 else None
    lon = sum(lon for lat, lon in lat_lon) / len(nodes) if len(nodes) > 0 else None

    logger.debug(
        f"Defined lat/lon coordinates for {get_osm_id(way)} "
        f"based on {len(nodes)} nodes; lat={lat}, lon={lon}"
    )

    return lat, lon


def get_element_by_id(elements, osm_type, elemet_id):
    """Get osm element from elements libary by id."""
    result = [nwr for nwr in elements[osm_type] if nwr["id"] == elemet_id]
    if len(result) > 0:
        return result[0]

    return None


def get_lat_lon_from_relation(relation, elements) -> Tuple[float, float]:
    """Gets lat/lon from OSM relation."""
    # Fix lat/lon of relation by taking the average of the lat/lons of members
    way_ids = [mbr["ref"] for mbr in relation["members"] if mbr["type"] == "way"]
    node_ids = [mbr["ref"] for mbr in relation["members"] if mbr["type"] == "node"]

    ways = [w for w in elements["way"] if w["id"] in set(way_ids)]
    nodes = [n for n in elements["node"] if n["id"] in set(node_ids)]
    members = ways + nodes

    lat_lon = [get_lat_lon_from_element(mbr, elements) for mbr in members]
    lat = sum(lat for lat, lon in lat_lon) / len(members) if len(members) > 0 else None
    lon = sum(lon for lat, lon in lat_lon) / len(members) if len(members) > 0 else None

    logger.debug(
        f"Defined lat/lon coordinates for {get_osm_id(relation)} "
        f"based on {len(members)} members; lat={lat}, lon={lon}"
    )

    return lat, lon


def parse_length(length_str: str):
    """Try to convert length string to distance in meter."""
    if length_str is None:
        return None

    # Try kW match
    match = re.search(
        r"(?P<length>\d+(\.\d+)?)\s*(m)?", length_str.replace(",", "."), re.IGNORECASE
    )
    if match:
        with contextlib.suppress(Exception):
            length = float(match.group("length"))
            return length

    if length_str not in ["yes", "yes [m]", "m"]:
        return length_str

    return None


def is_windturbine(node) -> bool:
    """Check if an OSM node is a wind turbine."""
    if "tags" in node:
        return (
            node["tags"].get("power") == "generator"
            and node["tags"].get("generator:source") == "wind"
        )

    return False


def parse_turbines_from_str(turbine_str: str):
    """Try to convert turbine string to number of turbines."""
    if turbine_str is None:
        return None

    match = re.search(r"(?P<n_turbines>\d+)\s?\w*", turbine_str, re.IGNORECASE)
    if match:
        with contextlib.suppress(Exception):
            return int(match.group("n_turbines"))

    return turbine_str


def parse_power_to_kw(
    power_str: str, unit_fallback: Optional[str] = None, diameter: Optional[float] = None
):
    """Try to convert power string to power in kW."""
    if power_str is None:
        return None

    # Try to match power and unit
    match = re.search(
        r"(?P<power>\d+(\.\d+)?)\s*(?P<unit>(kW)|(MW))?",
        power_str.replace(",", "."),
        re.IGNORECASE,
    )
    if match:
        try:
            power = float(match.group("power"))
        except (ValueError, KeyError, TypeError):
            power = None

        try:
            unit = str(match.group("unit"))
        except (ValueError, KeyError, TypeError):
            unit = unit_fallback

        return power_to_kw(power, unit, diameter)

    if power_str not in [
        "yes",
        "no",
        "*",
        "yes/kW",
        "no/kW",
        "yes/MW",
        "no/MW",
        "kW",
        "MW",
    ]:
        return power_str

    return None
