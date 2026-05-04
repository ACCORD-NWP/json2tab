"""Module for simple domain handler based on turbine country field."""
from typing import Optional


class CountryHandler:
    """Simple domain handler based on turbine country field."""

    def __init__(self, country_config):
        """Initialize country box handler with config.

        Args:
            country_config: country subsetting configuration

        """
        self.selected_countries = country_config.get("selected_countries", [])

    def point_in_domain(
        self,
        lon: Optional[float] = None,
        lat: Optional[float] = None,
        country: Optional[str] = None,
    ) -> bool:
        """Check if point lies within selected countries.

        Args:
            lon (float):   (not used) Longitude in degrees
            lat (float):   (not used) Latitude in degrees
            country (str): Country where the turbine is located

        Returns:
            bool: True if point is inside countries
        """
        del lon, lat
        if len(self.selected_countries) > 0:
            return country in self.selected_countries

        return True

    def display_name(self):
        """Gets a display name for readable subsetting filtering."""
        method = "countr" + ("y" if len(self.selected_countries) == 1 else "ies")
        return f"{method}: {', '.join(self.selected_countries)}"
