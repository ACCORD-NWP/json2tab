"""Module with get_lat_lon_matrix for wind turbine location data convertion."""

import numpy as np
import pandas as pd

try:
    import geopandas as gpd
except ImportError:
    gpd = None

try:
    import shapely
except ImportError:
    shapely = None

from ..logs import logger


def get_lat_lon_matrix(data: pd.DataFrame | dict, return_in_lat_lon_order: bool = True):
    """Get matrix with two columns containing lat and lon for all turbines in data

    Args:
        data: DataFrame containing wind turbine data
        return_in_lat_lon_order: Specify if output should be [lat, lon] or [lon, lat]

    Returns:
        matrix with two columns containing lat and lon for all turbines in data

    """

    def get_values(x):
        return x

    if isinstance(data, pd.DataFrame):
        cols = data.columns

        def get_values(x):
            return x.to_numpy()

    elif isinstance(data, dict):
        cols = data.keys()

    # Get latitude data
    latitude = None
    longitude = None

    if "geometry" in cols:
        if isinstance(data["geometry"], str) and shapely is not None:
            geo_data = data
            geo_data["geometry"] = shapely.from_wkt(data["geometry"])
        elif isinstance(data["geometry"], pd.Series) and isinstance(
            data["geometry"].iloc[0], str
        ) and gpd is not None:
            geometry = gpd.GeoSeries.from_wkt(data["geometry"])
            geo_data = gpd.GeoDataFrame(data, geometry=geometry)
        else:
            geo_data = data

        try:
            longitude = geo_data["geometry"].x
            latitude = geo_data["geometry"].y
        except AttributeError:
            longitude = None
            latitude = None

    if latitude is None:
        lat_fields = ["latitude", "lat", "Latitude", "N"]
        for field in lat_fields:
            if field in cols:
                latitude = get_values(data[field])
                break

    if latitude is None:
        logger.error(f"Cannot find latitude-data in {cols}")

    # Get longitude data
    if longitude is None:
        lon_fields = ["longitude", "lon", "Longitude", "E"]
        for field in lon_fields:
            if field in cols:
                longitude = get_values(data[field])
                break

    if longitude is None:
        logger.error(f"Cannot find longitude-data in {cols}")

    if return_in_lat_lon_order:
        return np.column_stack((latitude, longitude))

    return np.column_stack((longitude, latitude))
