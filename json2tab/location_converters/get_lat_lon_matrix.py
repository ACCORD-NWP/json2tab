"""Module to get lat/lon coordinates for wind turbine location data convertion."""

from typing import Tuple

import numpy as np
import pandas as pd

from ..Turbine import Turbine

try:
    from shapely import from_wkt
    from shapely.geometry import Point
except ImportError:
    from ..TurbinePoint import TurbinePoint as Point
    from ..TurbinePoint import from_wkt


def get_lat_lon(turbine: dict | Turbine | Point) -> Tuple[float, float]:
    """Get lat/lon coordinates for a turbine or point.

    Args:
        turbine: dict containing wind turbine data

    Returns:
        lat/lon coordinates of turbine

    """
    out = get_lat_lon_matrix(turbine, return_in_lat_lon_order=True)
    lat, lon = out[0, 0], out[0, 1]
    return lat, lon


def get_lon_lat(turbine: dict | Turbine | Point) -> Tuple[float, float]:
    """Get lon/lat coordinates for a turbine or point.

    Args:
        turbine: dict containing wind turbine data

    Returns:
        lon/lat coordinates of turbine

    """
    out = get_lat_lon_matrix(turbine, return_in_lat_lon_order=False)
    lon, lat = out[0, 0], out[0, 1]
    return lon, lat


def get_lat_lon_matrix(
    data: pd.DataFrame | dict | Turbine | Point,
    return_in_lat_lon_order: bool = True,
    compute_centroid: bool = False,
):
    """Get matrix with two columns containing lat and lon for all turbines in data.

    Args:
        data: DataFrame containing wind turbine data
        return_in_lat_lon_order: Specify if output should be [lat, lon] or [lon, lat]
        compute_centroid: Flag indicating if centroid should be computed for geometries

    Returns:
        matrix with two columns containing lat and lon for all turbines in data

    """

    def get_values(x):
        return x

    if isinstance(data, pd.DataFrame):
        cols = data.columns

        def get_values(x):
            return x.to_numpy()

    elif isinstance(data, (Turbine, pd.Series)):
        data = data.to_dict()

    if isinstance(data, Point):
        data = {"geometry": data}

    if isinstance(data, dict):
        cols = data.keys()

    # Get latitude data
    latitude = None
    longitude = None

    if "geometry" in cols and data["geometry"] is not None:
        geometry = data["geometry"]

        try:

            def safe_from_wkt(x):
                return from_wkt(x) if isinstance(x, str) else x

            if isinstance(geometry, str):
                geometry = safe_from_wkt(geometry)
            elif isinstance(geometry, pd.Series):
                geometry = geometry.apply(safe_from_wkt)

            if compute_centroid:
                geometry = (
                    geometry.centroid
                    if isinstance(geometry, Point)
                    else geometry.apply(lambda x: x.centroid)
                )

            longitude = geometry.x
            latitude = geometry.y

        except (AttributeError, ValueError):
            longitude = None
            latitude = None

    if latitude is None:
        lat_fields = ["latitude", "lat", "Latitude", "N"]
        for field in lat_fields:
            if field in cols:
                latitude = get_values(data[field])
                break

    if longitude is None:
        lon_fields = ["longitude", "lon", "Longitude", "E"]
        for field in lon_fields:
            if field in cols:
                longitude = get_values(data[field])
                break

    if return_in_lat_lon_order:
        return np.column_stack((latitude, longitude))

    return np.column_stack((longitude, latitude))
