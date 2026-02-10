"""Module with Fixer to derive country and is_offshore field for turbine locations."""

import os
import shutil
from typing import List, Optional, Tuple

import pandas as pd

from ..io.readers import read_locationdata_as_dataframe
from ..io.writers import save_dataframe
from ..logs import logger
from ..tools.Location2CountryConverter import Location2CountryConverter


def fix_country_offshore(
    input_filenames: List[str],
    output_filename: str,
    update_country: Optional[bool] = False,
    update_is_offshore: Optional[bool] = False,
):
    """Fixer for country and is_offshore flag.

    Args:
        input_filenames (list[str]): Input files used in country_offshore_flag_fixer
        output_filename (str):       Output csv/geojson-file with fixed turbine data
        update_country (bool):       Flag indicating to fix country
        update_is_offshore (bool):   Flag indicating to fix is_offshore flag
    """
    eez_files = [filename for filename in input_filenames if "eez" in filename.lower()]

    country_border_files = [
        filename for filename in input_filenames if "country_border" in filename.lower()
    ]

    eez_file = eez_files[0] if len(eez_files) > 0 else None
    land_file = country_border_files[0] if len(country_border_files) > 0 else None

    input_files = list(set(input_filenames) - {eez_file, land_file})

    country_offshore_flag_fixer(
        input_files,
        eez_file=eez_file,
        land_file=land_file,
        output_filename=output_filename,
        update_country=update_country,
        update_is_offshore=update_is_offshore,
    )


def country_offshore_flag_fixer(
    input_filename: List[str] | str | pd.DataFrame,
    eez_file: str,
    land_file: str,
    output_filename: Optional[str] = None,
    update_country: Optional[bool] = False,
    update_is_offshore: Optional[bool] = False,
) -> pd.DataFrame:
    """Fixer to derive country and is_offshore field for turbine locations."""
    if update_country and update_is_offshore:
        prog_name = "Country and is_offshore field fixer"
    elif update_country:
        prog_name = "Country field fixer"
    elif update_is_offshore:
        prog_name = "Is-offshore field fixer"
    else:
        logger.warning("Nothing to fix as both update country and is_offshore are False")

    print(f"{prog_name}")
    print(f" > Country EEZ-file: {eez_file}")
    print(f" > Country land border-file: {land_file}")

    loc2eez = Location2CountryConverter(eez_file)
    loc2land = Location2CountryConverter(land_file) if land_file is not None else None

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

        print(f"{prog_name} converts {input_filename} -> {output_filename}")

        logger.debug(f"input filename: {backup_input_filename or input_filename}")
        logger.debug(f"output filename: {output_filename}")

        if input_filename is not None:
            data = read_locationdata_as_dataframe(input_filename)

        if data is not None:
            new_is_offshore, new_country = zip(
                *data.apply(
                    lambda row: get_offshore_and_country(
                        loc2eez, loc2land, lon=row["longitude"], lat=row["latitude"]
                    ),
                    axis=1,
                )
            )

            if update_country:
                data["country"] = new_country
            if update_is_offshore:
                data["is_offshore"] = new_is_offshore

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

    if location_to_land is not None:
        land = location_to_land.get_country(lon, lat)
        is_offshore = country is not None and land is None
    else:
        is_offshore = None

    return is_offshore, country
