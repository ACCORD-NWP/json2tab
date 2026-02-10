#!/usr/bin/env python3
"""JSON-2-TAB command line entry point."""

import argparse
import importlib.metadata
import os

from .json2tab import json2tab

try:
    from .location_converters.converter import converter, supported_conversion_types
except ImportError:
    converter = None
    supported_conversion_types = []

try:
    from .location_converters.LocationMerger import location_merger
except ImportError:
    location_merger = None

try:
    from .location_converters.osm_data_fetcher import osm_data_fetcher
except ImportError:
    osm_data_fetcher = None

try:
    from .location_converters.TurbineWindfarmMapper import turbine_windfarm_mapper
except ImportError:
    turbine_windfarm_mapper = None

from .logs import logger
from .tools.KnmiTurbineDatabaseWriter import knmi_turbine_database_writer

try:
    from .tools.Location2CountryConverter import Location2CountryConverter
except ImportError:
    Location2CountryConverter = None

# some defaults
basedir = os.path.dirname(__file__)


def main(argv=None):
    """Program's main routine."""
    prog = "json2tab"

    parser = argparse.ArgumentParser(prog=prog)

    parser.add_argument(
        "--config-file",
        "-c",
        metavar="filepath",
        type=str,
        help="Path to the config file; Default: config.yaml",
        default="config.yaml",
    )

    parser.add_argument(
        "--turbine-database-file",
        "-tdb",
        metavar="filepath",
        type=str,
        help="Database file with turbine specifications; "
        "Default: None (i.e. as specified in config::input.turbine_database)",
        default=None,
    )

    parser.add_argument(
        "--turbine-location-file",
        "-tloc",
        metavar="filepath",
        type=str,
        help="Main GeoJSON file containing turbine locations; "
        "Default: None (i.e. as specified in config::input.turbine_locations)",
        default=None,
    )

    parser.add_argument(
        "--domain-file",
        "-d",
        metavar="filepath",
        type=str,
        help="Domain configuration file; "
        "Default: None (i.e. as specified in config::subsetting.domain.file)",
        default=None,
    )

    parser.add_argument(
        "--situation-date",
        "-date",
        metavar="date",
        type=str,
        help="Date to filter turbines in temporal domain; "
        "Default: None (i.e. as specified in config::subsetting.situation_date)",
        default=None,
    )

    parser.add_argument(
        "--output-dir",
        "-odir",
        metavar="dir",
        type=str,
        help="Directory for all output files; "
        "Default: None (i.e. as specified in config::output.directory)",
        default=None,
    )

    parser.add_argument(
        "--output-location-filename",
        "-oloc",
        metavar="file",
        type=str,
        help="Filename of the turbine location output tab-file; "
        "Default: None (i.e. as specified in config::output.files.location_tab)",
        default=None,
    )

    parser.add_argument(
        "--output-type-file-prefix",
        "-otype",
        metavar="prefix",
        type=str,
        help="Prefix of the turbine type files; "
        "Default: None (i.e. as specified in config::output.files.type_tab_prefix)",
        default=None,
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s v" + importlib.metadata.version(prog),
    )

    parser.add_argument(
        "--debug-level",
        "-dbg",
        metavar="level",
        type=int,
        help="verbosity level (0...3); Default: 1",
        default=1,
    )

    parser.add_argument(
        "--inverse",
        "-inv",
        metavar="turbine tab-file",
        type=str,
        nargs="+",
        help="Convert turbine tab-file to json turbine-database entry",
        default=None,
    )

    if osm_data_fetcher is not None:
        parser.add_argument(
            "--fetch-osm-data",
            "-osm",
            metavar="filename",
            type=str,
            help="Fetch windturbine location data from OpenStreetMap using Overpass API",
            default=None,
        )

    if location_merger is not None:
        parser.add_argument(
            "--merge",
            metavar="turbine location-files",
            type=str,
            nargs=2,
            help="Merge turbine location files",
            default=None,
        )

    if turbine_windfarm_mapper is not None:
        parser.add_argument(
            "--map",
            metavar="windfarm location-file, turbine location-file",
            type=str,
            nargs=2,
            help="Map windfarm info onto windturbine location info",
            default=None,
        )

    if Location2CountryConverter is not None:
        parser.add_argument(
            "--location2country",
            metavar="Country boarder file, lat, lon",
            type=str,
            nargs="+",
            help="Get country based on lat/lon coordinates",
            default=None,
        )

    if converter is not None:
        parser.add_argument(
            "--convert",
            metavar="input filename(s)",
            type=str,
            nargs="+",
            help="Convert windturbine location file (combined with --type)",
            default=None,
        )

        parser.add_argument(
            "--type",
            metavar="type of input file to convert",
            type=str,
            choices=supported_conversion_types,
            help="Specify converter type to convert input file",
        )

        parser.add_argument(
            "--country",
            metavar="type of merge",
            type=str,
            nargs="+",
            help="Country or list of countries to select/remove from map",
        )

        parser.add_argument(
            "--write-columns",
            metavar="write rule",
            type=str,
            help="Rules to write columns from input data before processing",
            default=None,
        )

    if converter is not None or location_merger is not None:
        parser.add_argument(
            "--min-distance",
            metavar="distance",
            type=float,
            help="Minimum distance (eg for removing duplicate turbines)",
            default=None,
        )

    if converter is not None or turbine_windfarm_mapper is not None:
        parser.add_argument(
            "--rename-columns",
            metavar="rename rule",
            type=str,
            help="Rules to rename columns from input data before processing",
            default=None,
        )

    if location_merger is not None or turbine_windfarm_mapper is not None:
        parser.add_argument(
            "--labels",
            metavar="source labels",
            type=str,
            nargs="+",
            help="Labels to specify source if not definied in files to merge",
            default=None,
        )

        parser.add_argument(
            "--merge-mode",
            metavar="type of merge",
            type=str,
            choices=["common", "enrich_first", "enrich_second", "combine"],
            help="Specify merge type to merge input files",
            default="combine",
        )

    if turbine_windfarm_mapper is not None:
        parser.add_argument(
            "--max-distance",
            metavar="distance",
            type=float,
            help="Maximum distance (eg for mapping turbines to windfarms)",
            default=None,
        )

    parser.add_argument("--output", metavar="output filename", type=str, default=None)

    args = parser.parse_args(argv)

    if args.debug_level == 0:
        logger.setLevel("ERROR")
    elif args.debug_level == 1:
        logger.setLevel("WARNING")
    elif args.debug_level == 2:
        logger.setLevel("INFO")
    elif args.debug_level > 2:
        logger.setLevel("DEBUG")

    logger.debug(f"This is logging from logger {logger.name}")
    logger.debug(f"Binary path: {basedir} ")
    logger.debug(f"Parsed arguments: {args}")

    if args.inverse:
        database_file = args.output or "turbine_database+knmi.json"
        print(
            "Convert turbine tab-file to json turbine-database entry, "
            "dump output database to {database_file}"
        )
        knmi_turbine_database_writer(args.inverse, database_file)
    elif args.fetch_osm_data:
        if osm_data_fetcher is not None:
            output_filename = args.fetch_osm_data
            osm_data_fetcher(output_filename, query_windturbine=True, query_windfarm=True)
        else:
            logger.warning(
                "Loading osm data fetcher failed; please install optional packages."
            )
    elif args.merge:
        if location_merger is not None:
            if args.labels and len(args.labels) == len(args.merge):
                location_merger(
                    args.merge[0],
                    args.merge[1],
                    args.output,
                    merge_mode=args.merge_mode,
                    label_source1=args.labels[0],
                    label_source2=args.labels[1],
                    min_distance=args.min_distance,
                )
            else:
                location_merger(
                    args.merge[0],
                    args.merge[1],
                    args.output,
                    merge_mode=args.merge_mode,
                    min_distance=args.min_distance,
                )
        else:
            logger.warning(
                "Loading location merger failed; please install optional packages."
            )
    elif args.map:
        if turbine_windfarm_mapper is not None:
            max_distance = args.max_distance
            if args.labels and len(args.labels) > 0:
                turbine_windfarm_mapper(
                    args.map[0],
                    args.map[1],
                    args.output,
                    merge_mode=args.merge_mode,
                    source_label=args.labels[0],
                    max_distance=max_distance,
                    rename_rules=args.rename_columns,
                )
            else:
                turbine_windfarm_mapper(
                    args.map[0],
                    args.map[1],
                    args.output,
                    merge_mode=args.merge_mode,
                    max_distance=max_distance,
                    rename_rules=args.rename_columns,
                )
        else:
            logger.warning(
                "Loading turbine windfarm mapper failed; "
                "please install optional packages."
            )

    elif args.location2country:
        if Location2CountryConverter is not None:
            level = (
                int(args.location2country[3]) if len(args.location2country) > 3 else None
            )
            l2c = Location2CountryConverter(args.location2country[0], level=level)
            country = l2c.get_country(
                float(args.location2country[1]), float(args.location2country[2])
            )
            print(country)
        else:
            logger.warning(
                "Loading location2country converter failed; "
                "please install optional packages."
            )
    elif args.convert:
        if converter is not None:
            converter(
                convert_type=args.type,
                input_filenames=args.convert,
                output_filename=args.output,
                country=args.country,
                rename_rules=args.rename_columns,
                write_columns=args.write_columns,
                min_distance=args.min_distance,
            )
        else:
            logger.warning("Loading converter failed; please install optional packages.")

    else:
        print("Run json2tab; default mode")
        json2tab(
            config_path=args.config_file,
            turbine_databases=args.turbine_database_file,
            turbine_locations=args.turbine_location_file,
            output_dir=args.output_dir,
            domain_file=args.domain_file,
            situation_date=args.situation_date,
            location_file=args.output_location_filename,
            type_file_prefix=args.output_type_file_prefix,
        )


if __name__ == "__main__":
    main()
