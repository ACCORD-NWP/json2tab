"""Converter to generate wind turbine location files for Austria.

Input data based on IG windkraft windrad karte.
Website: https://www.igwindkraft.at/aktuelles/windrad-karte
"""

import contextlib
import json
import os
import re
from typing import Optional

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

from ...io.writers import save_dataframe
from ...logs import logger, logging
from ...Turbine import Turbine


def austria(
    input_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Austria."""
    turbine_json = None
    if input_filename.lower().startswith(("http://", "https://", "www.igwindkraft.at")):
        # Load data directly from igwindkraft website
        turbine_json = get_igwindkraft_windrad_karte(input_filename)
        if label_source is None:
            label_source = "IG Windkraft Windradlandkarte"

        if turbine_json is not None:
            input_filename = "igwindkraft-windrad-karte.json"

            with contextlib.suppress(Exception), open(input_filename, "w") as dump_file:
                # Dump the fetched data to a file
                dump_file.write(turbine_json)

    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"Austria Json Converter ({input_filename} -> {output_filename})")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    data = None
    if turbine_json is None:
        with open(input_filename, "r") as input_file:
            data = json.load(input_file)
    else:
        data = json.loads(turbine_json)

    if data is not None:
        turbines = []
        skipped_turbines = []
        for properties_list in data.values():
            idx = 0
            for properties in properties_list:
                idx += 1

                prop_id = properties["id"]

                lon = properties["x"]
                try:
                    if isinstance(lon, str):
                        lon = float(lon.replace(",", "."))
                except (ValueError, TypeError):
                    pass

                lat = properties["y"]
                try:
                    if isinstance(lat, str):
                        lat = float(lat.replace(",", "."))
                except (ValueError, TypeError):
                    pass

                rated_power = properties["mweinzeln"]
                try:
                    if isinstance(rated_power, float):
                        # Convert MW powers to kW powers
                        rated_power *= 1000
                    if isinstance(rated_power, str):
                        rated_power = float(rated_power.replace(",", ".")) * 1000
                except (ValueError, TypeError):
                    pass

                facilityInfo = properties["facilityInfo"]

                n_turbines = 1
                match = re.search(r"(?P<n_turbines>\d+) Anlage(n)", facilityInfo)
                if match:
                    with contextlib.suppress(ValueError, TypeError):
                        n_turbines = int(match.group("n_turbines"))

                start_date = None
                match = re.search(r"errichtet: (?P<start_year>\d+)", facilityInfo)
                if match:
                    with contextlib.suppress(ValueError, TypeError):
                        start_date = int(match.group("start_year"))

                typeInfo = properties["typeInfo"].split("<br>")
                match = re.search(r"Type: (?P<man>[^,]*), (?P<type>.*)", typeInfo[0])
                if match:
                    manufacturer = match.group("man")
                    turbine_type = match.group("type")
                else:
                    manufacturer = None
                    turbine_type = None

                hub_height = None
                match = re.search(r"Nabenh.*he: (?P<hub_height>\d+)", typeInfo[1])
                if match:
                    with contextlib.suppress(ValueError, TypeError):
                        hub_height = float(match.group("hub_height"))

                diameter = None
                radius = None
                match = re.search(r"Rotordurchmesser: (?P<diameter>\d+)", typeInfo[1])
                if match:
                    try:
                        diameter = float(match.group("diameter"))
                        radius = diameter / 2
                    except (ValueError, TypeError):
                        pass

                project = properties["project"]

                turbine = Turbine(
                    id=prop_id,
                    turbine_id=idx,
                    latitude=lat,
                    longitude=lon,
                    name=f"Turbine {idx} in '{project}'",
                    country="Austria",
                    source=label_source,
                    hub_height=hub_height,
                    power_rating=rated_power,
                    radius=radius,
                    diameter=diameter,
                    manufacturer=manufacturer,
                    type=turbine_type,
                    wind_farm=project,
                    n_turbines=n_turbines,
                    start_date=start_date,
                    is_offshore=False,
                )

                if lat is not None and lon is not None:
                    turbines.append(turbine)
                else:
                    logger.warning(
                        f"Skipped turbine {turbine.name} (id={turbine.id}) "
                        "due to invalid lat/lon."
                    )
                    skipped_turbines.append(turbine)

        data = pd.DataFrame(turbines)
        save_dataframe(data, output_filename)

        logger.warning(f"Skipped {len(skipped_turbines)} turbines")
        if len(skipped_turbines) > 0 and logger.getEffectiveLevel() <= logging.DEBUG:
            save_dataframe(
                pd.DataFrame(skipped_turbines), f"{output_filename}.skipped.csv"
            )

        return data
    return None


def get_igwindkraft_windrad_karte(url: str) -> str:
    """Gets the json-string with windturbine data from igwindkraft website."""
    if requests is not None:
        logger.info(f"Fetch windturbine data from {url}")
        windrad_karte = requests.get(url).text

        parts = windrad_karte.split("wheels='", 1)
        if len(parts) == 2:
            parts = parts[1].split("'", 1)
            return parts[0]

    else:
        logger.error("Python module requests not loaded, so no web requests possible.")

    return None
