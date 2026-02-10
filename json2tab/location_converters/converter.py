"""Module containing front end of windturbine location file converters."""

from typing import List, Optional

from ..location_converters.convert_between_csv_geojson import convert_between_csv_geojson
from ..location_converters.country_data.austria import austria
from ..location_converters.country_data.denmark import denmark
from ..location_converters.country_data.finland import finland
from ..location_converters.country_data.flanders import flanders
from ..location_converters.country_data.germany import germany
from ..location_converters.country_data.italy import italy
from ..location_converters.country_data.netherlands import netherlands
from ..location_converters.country_data.sweden import sweden
from ..location_converters.country_data.thewindpower import thewindpower
from ..location_converters.country_data.united_kingdom import united_kingdom
from ..location_converters.country_filters import (
    remove_from_countries,
    select_from_countries,
    select_offshore,
    select_onshore,
)
from ..location_converters.country_offshore_flag_fixer import fix_country_offshore
from ..location_converters.csv_to_csv import csv_to_csv
from ..location_converters.osm_data_fetcher import osm_data_fetcher
from ..location_converters.short_distance_remover import short_distance_remover
from ..location_converters.wf101_location_converter import wf101_location_converter

supported_conversion_types: List[str] = sorted(
    [
        "fix_country",
        "fix_onshore",
        "fix_offshore",
        "fix_is_offshore",
        "fix_country_offshore",
        "fix_country_is_offshore",
        "netherlands",
        "osm",
        "osm_windturbine",
        "osm_windfarm",
        "osm_windturbine_windfarm",
        "csv2geojson",
        "csv_to_geojson",
        "geojson2csv",
        "geojson_to_csv",
        "tab2csv",
        "tab_to_csv",
        "txt2csv",
        "txt_to_csv",
        "csv2csv",
        "csv_to_csv",
        "austria",
        "denmark",
        "finland",
        "flanders",
        "germany",
        "italy",
        "sweden",
        "uk",
        "uk",
        "unitedkingdom",
        "united_kingdom",
        "twp",
        "thewindpower",
        "thewindpower.net",
        "wf2csv",
        "wf101_to_csv",
        "wf2geojson",
        "wf101_to_geojson",
        "remove_short_distance",
        "select_country",
        "remove_country",
        "select_onshore",
        "select_offshore",
    ]
)
"""Supported `convert_type` that the converter can process. """


def converter(
    convert_type: str,
    input_filenames: str | List[str],
    output_filename: Optional[str] = None,
    country: Optional[str | List[str]] = None,
    rename_rules: Optional[str | dict] = None,
    write_columns: Optional[str | dict] = None,
    min_distance: Optional[float] = None,
):
    """Entry point for different converters.

    Args:
        convert_type (str):                Type of converter,
                                           should be in `supported_conversion_types`
        input_filenames (str | list[str]): Input file or list of files for converter
        output_filename (str):             Output file for converter
        country (str | list[str]):         Country or list of countries as used in
                                           `select_country` and `remove_country`
        rename_rules (str | dict):         Rename rules to rename columns in input
        write_columns (str | dict):        Inject rules to write columns in output
        min_distance (float):              Min distance for remove_short_distance
    """
    # Process first multi-input file converters
    if convert_type in ["fix_country_offshore", "fix_country_is_offshore"]:
        fix_country_offshore(
            input_filenames, output_filename, update_country=True, update_is_offshore=True
        )
    elif convert_type == "fix_country":
        fix_country_offshore(input_filenames, output_filename, update_country=True)
    elif convert_type in ["fix_offshore", "fix_onshore", "fix_is_offshore"]:
        fix_country_offshore(input_filenames, output_filename, update_is_offshore=True)
    elif convert_type == "netherlands":
        rivm_file = input_filenames[0]
        rws_file = input_filenames[1]
        if "rivm" in rws_file and "rivm" not in rivm_file:
            # Swap arguments as the second argument seems to be the RIVM file
            rivm_file, rws_file = rws_file, rivm_file
        netherlands(rivm_file, rws_file, output_filename, min_distance=min_distance)
    elif convert_type == "osm":
        osm_data_fetcher(output_filename, input_filenames[0])
    elif convert_type == "osm_windturbine":
        osm_data_fetcher(
            output_filename,
            input_filenames[0],
            query_windturbine=True,
            query_windfarm=False,
        )
    elif convert_type == "osm_windfarm":
        osm_data_fetcher(
            output_filename,
            input_filenames[0],
            query_windturbine=False,
            query_windfarm=True,
        )
    elif convert_type == "osm_windturbine_windfarm":
        osm_data_fetcher(
            output_filename,
            input_filenames[0],
            query_windturbine=True,
            query_windfarm=True,
        )

    else:
        # Only support for explicit output argument if converter converts a single file
        if len(input_filenames) > 1:
            output_filename = None

        for input_filename in input_filenames:
            if convert_type in [
                "csv2geojson",
                "csv_to_geojson",
                "geojson2csv",
                "geojson_to_csv",
                "tab2csv",
                "tab_to_csv",
                "txt2csv" "txt_to_csv",
            ]:
                convert_between_csv_geojson(
                    input_filename, output_filename, rename_rules=rename_rules
                )

            elif convert_type in ["csv2csv", "csv_to_csv"]:
                csv_to_csv(
                    input_filename,
                    output_filename,
                    rename_rules=rename_rules,
                    write_columns=write_columns,
                )

            elif convert_type in ["twp", "thewindpower", "thewindpower.net"]:
                thewindpower(input_filename, output_filename, rename_rules=rename_rules)

            elif convert_type == "austria":
                austria(input_filename, output_filename)

            elif convert_type == "denmark":
                denmark(input_filename, output_filename)

            elif convert_type == "finland":
                finland(input_filename, output_filename)

            elif convert_type == "flanders":
                flanders(input_filename, output_filename, min_distance=min_distance)

            elif convert_type == "germany":
                germany(input_filename, output_filename)

            elif convert_type == "italy":
                italy(input_filename, output_filename)

            elif convert_type == "sweden":
                sweden(input_filename, output_filename)

            elif convert_type in ["uk", "unitedkingdom", "united_kingdom"]:
                united_kingdom(input_filename, output_filename)

            elif convert_type in [
                "wf2csv",
                "wf101_to_csv",
                "wf2geojson",
                "wf101_to_geojson",
            ]:
                wf101_location_converter(input_filename, output_filename)

            elif convert_type == "remove_short_distance":
                short_distance_remover(
                    input_filename, output_filename, min_distance=min_distance
                )

            elif convert_type == "select_country":
                select_from_countries(input_filename, output_filename, country)

            elif convert_type == "remove_country":
                remove_from_countries(input_filename, output_filename, country)

            elif convert_type == "select_offshore":
                select_offshore(input_filename, output_filename)

            elif convert_type == "select_onshore":
                select_onshore(input_filename, output_filename)
