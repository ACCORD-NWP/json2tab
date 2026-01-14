"""Module with Fixer to derive country and is_offshore field for turbine locations."""

import os
import shutil
from typing import List, Optional, Tuple

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..logs import logger
from ..tools.Location2CountryConverter import Location2CountryConverter


def country_offshore_flag_fixer(
    input_filename: List[str] | str | pd.DataFrame,
    eez_file: str,
    land_file: str,
    output_filename: Optional[str] = None,
) -> pd.DataFrame:
    """Fixer to derive country and is_offshore field for turbine locations."""
    print("Country and is_offshore Flag Fixer")
    print(f" > Country EEZ-file: {eez_file}")
    print(f" > Country land border-file: {land_file}")

    loc2eez = Location2CountryConverter(eez_file)
    loc2land = Location2CountryConverter(land_file)

    data = None
    if isinstance(input_filename, str):
        input_filenames = [input_filename]
    if isinstance(input_filename, list):
        input_filenames = input_filename
    elif isinstance(input_filename, pd.DataFrame):
        data = input_filename
        input_filenames = [None]
    else:
        logger.error(
            f"Cannot interpret input = {input_filename} as a filename or pandas.DataFrame"
        )

    for input_filename in input_filenames:
        if input_filename is not None:
            if output_filename is None or len(input_filenames) > 1:
                input_filename_base, input_filename_ext = os.path.splitext(input_filename)
                backup_input_filename = f"{input_filename_base}{input_filename_ext}.orig"

                shutil.copyfile(input_filename, backup_input_filename)
                logger.info(
                    f"Copied original input-file {input_filename} to "
                    f"{backup_input_filename}, set output-file to {input_filename}"
                )
                output_filename = input_filename
            else:
                backup_input_filename = None
        # else: data is already set by direct feed-in

        print(f"Country Fixer converts {input_filename} -> {output_filename}")

        logger.debug(f"input filename: {backup_input_filename or input_filename}")
        logger.debug(f"output filename: {output_filename}")

        if input_filename is not None:
            data = read_locationdata_as_dataframe(input_filename)

        if data is not None:
            logger.info(f"Loaded {len(data.index)} turbines from {input_filename}")

            data["is_offshore"], data["country"] = zip(
                *data.apply(
                    lambda row: get_offshore_and_country(
                        loc2eez, loc2land, lon=row["longitude"], lat=row["latitude"]
                    ),
                    axis=1,
                )
            )

            if output_filename is not None:
                save_dataframe(data, output_filename)

    return data


def get_offshore_and_country(
    location_to_eez: Location2CountryConverter,
    location_to_land: Location2CountryConverter,
    lon: float,
    lat: float,
) -> Tuple[bool, float]:
    """Computes country and is_offshore for a given lat/lon.

    Args:
        location_to_eez (Location2CountryConverter):  Converter to derive EEZ country
        location_to_land (Location2CountryConverter): Converter to derive land country
        lon (float):                                  The longitude of the point
        lat (float):                                  The latitude of the point

    Returns:
        is_offshore: Flag indicating if point is an offshore location
        country:     The name of the country (EEZ based) of this location
    """
    country = location_to_eez.get_country(lon, lat)
    land = location_to_land.get_country(lon, lat)

    is_offshore = country is not None and land is None

    return is_offshore, country
