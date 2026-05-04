"""Domain handler for selecting points in bounding box based on lat/lon."""
from typing import Optional


class BoundingBoxHandler:
    """Simple domain handler based on lat/lon bounding box."""

    def __init__(self, bbox_config):
        """Initialize bounding box handler with config.

        Args:
            bbox_config: list of bounds in the following order
                             [min_longitude, min_latitude, max_longitude, max_latitude]

        """
        self.min_lon, self.min_lat, self.max_lon, self.max_lat = bbox_config

    def get_bounds(self):
        """Get bounds of bounding box.

        Returns:
            list of bounds in the following order
            [min_longitude, min_latitude, max_longitude, max_latitude]
        """
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def point_in_domain(
        self, lon: float, lat: float, country: Optional[str] = None
    ) -> bool:
        """Check if point lies within lat/lon bounding box.

        Args:
            lon (float):   Longitude in degrees
            lat (float):   Latitude in degrees
            country (str): (not used) Country where the turbine is located

        Returns:
            bool: True if point is inside domain
        """
        del country

        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat

    def display_name(self):
        """Gets a display name for readable subsetting filtering."""
        return f"bbox: [{self.min_lon}, {self.min_lat}, {self.max_lon}, {self.max_lat}]"
