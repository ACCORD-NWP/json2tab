"""Module to write pandas dataframe with wind turbine locations as geojson-file."""

import os

import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

try:
    from shapely.geometry import Point
except ImportError:
    Point = None

from ..location_converters.get_lat_lon_matrix import get_lat_lon_matrix
from ..logs import logger


def save_dataframe_as_geojson(
    data: pd.DataFrame, output_file: str = "wind_turbines.geojson"
) -> None:
    """Save dataframe with wind turbine data as a GeoJSON file.

    Args:
        data (pandas.DataFrame): DataFrame containing wind turbine data
        output_file (str):       Path for the output GeoJSON file


    """
    if gpd is None or Point is None:
        logger.error("Missing python packages: 'geopandas' and/or 'shapely' not found")
        print(
            "Python package(s) 'geopandas' and/or 'shapely' not found, "
            "please load this optional package to run LocationMerger."
        )
        print("Please run")
        print("    poetry install --with locationmerger")
        print("to install the necessary packages for LocationMerger")

        return

    try:
        logger.info("Converting data to GeoJSON format...")

        # Create geometry column
        geometry = [
            Point(xy) for xy in get_lat_lon_matrix(data, return_in_lat_lon_order=False)
        ]

        # Convert to GeoDataFrame
        gdf = gpd.GeoDataFrame(
            data, geometry=geometry, crs="EPSG:4326"  # WGS84 coordinate system
        )

        # Remove duplicate geometry column if it exists in the data
        if "geometry" in data.columns:
            gdf = gdf.drop(columns=["geometry"])

        # Convert numeric columns to float where possible for better JSON compatibility
        numeric_columns = [
            "hub_height",
            "power_rating",
            "diameter",
            "cut_in_speed",
            "rated_speed",
            "cut_out_speed",
        ]

        for col in numeric_columns:
            if col in gdf.columns:
                gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

        logger.info("Writing data to GeoJSON file...")

        # Save to GeoJSON
        gdf.to_file(output_file, driver="GeoJSON")

        # Log success and file size
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # Convert to MB
        logger.info(
            f"Successfully saved GeoJSON file to {output_file} "
            f"(File size: {file_size:.2f} MB)"
        )

        # Validate the saved file
        validate_geojson(output_file)

    except Exception as e:
        logger.error(f"Error saving GeoJSON file: {e}")
        logger.exception("Detailed error information:")


def validate_geojson(filename: str) -> bool:
    """Validate a saved geojson file, check if it can be read.

    Args:
        filename (str): Filename of file to check

    Returns:
        True if reading datafile was successful

    """
    try:
        # Try reading back the file to ensure it's valid
        data = gpd.read_file(filename)
        logger.info(f"GeoJSON validation successful: {len(data)} features loaded")

        return True
    except Exception as e:
        logger.exception(f"GeoJSON validation warning: {e}")
        return False
