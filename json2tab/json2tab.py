"""JSON-2-TAB main function-call entry point."""

import glob
import os
import traceback
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .AutoIncrementTypeIndexGenerator import AutoIncrementTypeIndexGenerator
from .io.writers import save_dataframe
from .logs import logger
from .turbine_filters.TurbineGeoFilterer import TurbineGeoFilterer
from .turbine_filters.TurbineTimeFilterer import TurbineTimeFilterer
from .TurbineLocationManager import TurbineLocationManager
from .TurbineLocationTabFileWriter import TurbineLocationTabFileWriter
from .TurbineMatcher import TurbineMatcher
from .TurbineTypeManager import TurbineTypeManager
from .TurbineTypeTabFileWriter import TurbineTypeTabFileWriter

try:
    from .SimpleVisualizer import SimpleVisualizer
except ImportError:
    # Loading optional package SimpleVisualizer failed
    # (probably due to missing the optional packages matplotlib and/or cartopy)
    SimpleVisualizer = None


def json2tab(
    config_path: str = "config.yaml",
    turbine_databases: Optional[List[str]] = None,
    turbine_locations: Optional[str] = None,
    domain_file: Optional[str] = None,
    domain_dict: Optional[Dict[str, Any]] = None,
    situation_date: Optional[date] = None,
    output_dir: Optional[str] = None,
    location_file: Optional[str] = None,
    type_file_prefix: Optional[str] = None,
):
    """JSON-2-TAB; function call entry point.

    Wrapper around WindTurbineLocationProcessor(Visualizer) to inject custom paths.
    """
    # Load configuration
    logger.debug(f"config_path = {config_path}")
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as file:
        config = yaml.safe_load(file)

    logger.debug(f"config = {config}")

    # Override custom arguments
    if turbine_databases is not None:
        if isinstance(turbine_databases, str):
            turbine_databases = [turbine_databases]

        config["input"]["turbine_database"] = turbine_databases

    if turbine_locations is not None:
        config["input"]["turbine_locations"] = turbine_locations

    if domain_file is not None:
        config["subsetting"]["method"] = "domain"
        config["subsetting"]["domain"]["file"] = domain_file

    if domain_dict is not None:
        config["subsetting"]["method"] = "domain"
        config["subsetting"]["domain"] = domain_dict

    if situation_date is not None:
        config["subsetting"]["situation_date"] = situation_date

    if output_dir is not None:
        config["output"]["directory"] = output_dir

    if location_file is not None:
        config["output"]["files"]["location_tab"] = location_file

    if type_file_prefix is not None:
        config["output"]["files"]["type_tab_prefix"] = type_file_prefix

    # Dump the (modified) config to output_dir
    Path(config["output"]["directory"]).mkdir(parents=True, exist_ok=True)
    with open(f"{config['output']['directory']}/processed_config.yaml", "w") as outfile:
        yaml.dump(config, outfile, default_flow_style=False)

    logger.debug(
        f"Preprocessing done. "
        f"Calling WindTurbineLocationProcessorVisualizer with config={config}"
    )

    try:
        main(config)

    except Exception as e:
        logger.error(f"Error during processing: {e}")

        traceback.print_exc()
        raise


def main(config: Dict[str, Any]):
    """Main function for processing wind turbine data."""
    type_databases = config["input"]["turbine_database"]

    # Handle optional (but depricated) input.turbine_specs field
    # as additional database source
    if "turbine_specs" in config["input"]:
        logger.warning(
            "The config field input.turbine_specs is depricated, "
            "it can be added as additional item to the input.turbine_database list."
        )
        turbine_specs = config["input"]["turbine_specs"]

        if turbine_specs and turbine_specs not in type_databases:
            if isinstance(type_databases, str):
                type_databases = [type_databases, turbine_specs]
            else:
                type_databases.append(turbine_specs)

    # Initialize turbine type manager
    type_manager = TurbineTypeManager(type_databases)

    # Read/filter windturbine locations
    turbine_location_files = config["input"]["turbine_locations"]
    location_manager = TurbineLocationManager(turbine_location_files)

    # Apply cropping to subdomain
    location_manager.filter_turbines(TurbineGeoFilterer(config["subsetting"]))

    # Apply selecting turbines respecting installation date
    location_manager.filter_turbines(TurbineTimeFilterer(config["subsetting"]))

    # Create output directory
    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup turbine matcher
    model_designation_key = "model_designation"
    type_index_key = "type_index"
    turbine_matcher = TurbineMatcher(
        config,
        location_manager,
        type_manager,
        model_designation_key=model_designation_key,
    )

    # Perform the actual match between turbine locations and turbine types
    matched_turbines = turbine_matcher.match()

    # Apply a type_index generator to get integer-valued types
    type_index_generator = AutoIncrementTypeIndexGenerator(
        matched_line_index_key=turbine_matcher.matched_line_index_key,
        type_idx_key=type_index_key,
    )
    matched_turbines = type_index_generator.apply(matched_turbines)
    matched_turbines = matched_turbines.drop(
        columns=[turbine_matcher.matched_line_index_key], axis=1
    )

    # Initialize location tab-file writer and write location tab-file
    location_tab_writer = TurbineLocationTabFileWriter(config, turbine_matcher)
    location_tab_writer.write(matched_turbines, type_idx_key=type_index_key)

    # Save enhanced filtered location data before processing tab files
    output_filtered_data = output_dir / config["output"]["files"]["filtered_geojson"]
    save_dataframe(matched_turbines, output_filtered_data)

    # Remove all old tab-files
    type_tab_prefix = config["output"]["files"]["type_tab_prefix"]
    tab_file_pattern = str(output_dir / f"{type_tab_prefix}*.tab")

    logger.info(f"Remove all tab-files with pattern: '{tab_file_pattern}'")
    for file in glob.glob(tab_file_pattern):
        os.remove(file)

    # Process all turbine types and create the tab files
    logger.info("Generating new turbine type tab files")
    type_tab_writer = TurbineTypeTabFileWriter(
        config, turbine_matcher, type_index_generator
    )
    type_tab_writer.write(matched_turbines, output_dir, type_tab_prefix)

    location_tab_writer.write_installed_capacity_table(matched_turbines)

    if SimpleVisualizer is not None:
        # Create visualization using simplified visualizer
        visualizer = SimpleVisualizer(config)
        map_output = output_dir / "turbine_map.png"
        visualizer.create_map_plot(matched_turbines, map_output)
        print(f"Created map visualization: {map_output}")

    print(f"\nOutput directory: {output_dir}")
    print("Processing completed successfully!")
