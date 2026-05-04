"""Domain handler that always returns True for a requested location."""
from typing import Optional


class TrueHandler:
    """Simple domain handler based on always in domain logic."""

    def __init__(self):
        """Initialize always in domain handler without config."""

    def point_in_domain(
        self,
        lon: Optional[float] = None,
        lat: Optional[float] = None,
        country: Optional[str] = None,
    ) -> bool:
        """No check, always true.

        Args:
            lon (float):   (not used) Longitude in degrees
            lat (float):   (not used) Latitude in degrees
            country (str): (not used) Country where the turbine is located

        Returns:
            bool: True
        """
        del lon, lat, country
        return True

    def display_name(self):
        """Gets a display name for readable subsetting filtering."""
        return "always True"
