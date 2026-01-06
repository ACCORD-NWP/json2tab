"""Wind Turbine Location Processor and Visualizer.

============================================

This module provides comprehensive functionality for processing
wind turbine location data, matching turbine specifications, and
generating standardized output formats for numerical weather
prediction (NWP) models, specifically HARMONIE-AROME.

Key Features:
------------
- Processes GeoJSON wind turbine location data
- Filters turbines based on domain boundaries or bounding boxes
- Matches turbines with specifications from multiple databases
- Generates standardized tab-file outputs for NWP models
- Creates visualizations of turbine distributions
- Handles both onshore and offshore wind turbines
- Provides intelligent defaults based on geographical location

Main Components:
--------------
- TurbineFilterer: Main filtering pipeline
- TurbineMatcher: Matches turbines with specifications
- TabFileWriter: Generates formatted output files
- SimpleVisualizer: Creates map visualizations
- DefaultTurbineSelector: Provides location-based defaults

Configuration:
-------------
The module uses a YAML configuration file that specifies:
- Input/output paths
- Domain boundaries or bounding box
- Processing parameters
- Visualization settings

Example configuration:
```yaml
input:
  turbine_locations: "turbines.geojson"
  turbine_database: "specifications.csv"
subsetting:
  method: "bbox"  # or "domain"
  bbox: [2.8, 51.5, 3.2, 51.8]  # [min_lon, min_lat, max_lon, max_lat]
output:
  directory: "output"
  prefix: "windturbines"
```

Dependencies:
------------
- numpy: Array processing
- pandas: Data manipulation
- matplotlib: Plotting
- cartopy: Geographical plotting
- yaml: Configuration parsing
- json: GeoJSON processing
- pathlib: Path handling
- logging: Error and debug logging

Usage:
-----
1. Prepare configuration file:
   ```bash
   $ cp config.yaml.template config.yaml
   $ edit config.yaml  # Adjust settings as needed
   ```

2. Run the processor:
   ```bash
   $ python wind_turbine_processor.py
   ```

3. Check outputs in specified directory:
   - turbine_locations.tab: Main turbine location file
   - turbine_type_*.tab: Individual turbine specifications
   - turbine_map.png: Visualization of turbine locations

Notes:
-----
- Supports KNMI reference turbine types
- Includes WF101 turbine database integration
- Handles missing data with intelligent defaults
- Provides comprehensive error logging
- Follows HARMONIE-AROME conventions


CHANGES:
03.03.2025:

1. Named model files for recognizable turbine types (V90, E126, etc.)
2. Unique reference files for generic/unknown turbine types (Reference_8021, etc.)
3. Enhanced tab files with model references included as comments
4. Enhanced GeoJSON output with model designation information
5. Complete mapping between type IDs and model designations

Step-by-Step Implementation:

1. Add the extract_model_designation method to the TurbineMatcher class:
   - This helps extract clean model names from turbine specifications
   - Copy the entire method from the "Model Designation Extraction Helper Method" artifact

2. Enhance the TabFileWriter class:
   - Update the __init__ method to include the type_to_model_map
   - Replace the write_turbine_type_tab method with the enhanced version
     - This version handles reference turbines by adding the type ID to the filename
   - Replace the write_location_tab method with the enhanced version
     - This adds model file references as comments to the tab file
     - It also enhances the GeoJSON with model designations

3. Update the main function:
   - Use the enhanced main function to process and save the enhanced GeoJSON
   - Update the output summary to show the mapping between type IDs and model files

20.03.2025:

1. Add Power Curve Values to Tab Files
   - Added a fourth column to the power curve data section showing power output in kW
   - Enhanced tab file header to indicate the new column
   - Added calculations to derive power curves when not directly available
   - Power curves now extend to 35 m/s for all turbines
   - Coefficients (Cp, Ct) use intelligent decay for higher wind speeds
   - Power output maintains the rated value at higher wind speeds

2. Replace KNMI Reference with Enercon E101
   - Added detailed Enercon E101 specifications with power curve data
   - Updated the reference turbine used for fallback cases
   - Maintained the same ID handling for backward compatibility

3. Improved Error Handling
   - Added comprehensive error handling for missing or invalid data
   - Made the code more robust when dealing with incomplete turbine specifications
   - Ensured processing continues even when some turbines have missing data

4. Added Rated Power to Header
   - File headers now include "PR=X.X kW" to indicate rated power
   - Uses the maximum of:
     a) The rated_power value from specifications
     b) The maximum power output in the power curve
   - Ensures consistent power information for all turbine types


Example Tab File Header:
```
# E101 (z=99.0 m, D=101.0 m, ID=15431, PR=3050.0 kW)
```

Authors:
-------
Irene Schicker (GeoSphere Austria)
Dieter van den Bleeken (RMI)
Jacob Snoeijer (KNMI)

References:
----------
1. HARMONIE-AROME Documentation
2. Fitch et al. (2012) - Wind farm parametrization
3. Volker et al. (2015) - Wind farm effects
"""

import glob
import os
from pathlib import Path
from typing import Any, Dict

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


def main(config: Dict[str, Any]):
    """Main function for processing wind turbine data."""
    try:
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

        if SimpleVisualizer is not None:
            # Create visualization using simplified visualizer
            visualizer = SimpleVisualizer(config)
            map_output = output_dir / "turbine_map.png"
            visualizer.create_map(matched_turbines, map_output)
            print(f"Created map visualization: {map_output}")

        location_tab_writer.write_installed_capacity_table(matched_turbines)

        print(f"\nOutput directory: {output_dir}")
        print("Processing completed successfully!")

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
