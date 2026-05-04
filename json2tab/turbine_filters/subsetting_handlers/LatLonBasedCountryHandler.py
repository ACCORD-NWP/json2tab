"""Module for expensive domain handler based on lat/lon coodinates to get country."""

from typing import Optional

from ...tools.Location2CountryConverter import Location2CountryConverter


class LatLonBasedCountryHandler:
    """Expensive domain handler based on lat/lon coodinates to determine country."""

    def __init__(self, country_config):
        """Initialize country handler with config.

        Args:
            country_config: dictionary from TOML file
        """
        mode = country_config.get("mode", None)
        level = None
        layer = None

        if mode in ["country", "eez", "provincie", "gemeente"]:
            country_border_file = country_config["files"][mode]

            levels = country_config.get("levels", None)
            if levels is not None:
                level = levels.get(mode, None)
        else:
            country_border_file = country_config["country_border_file"]
            level = country_config.get("level", None)
            layer = country_config.get("layer", None)

        # Load location to country converter
        if level is None and layer is None:
            self.l2c = Location2CountryConverter(country_border_file)
        elif level is not None:
            self.l2c = Location2CountryConverter(country_border_file, level=level)
        else:
            self.l2c = Location2CountryConverter(country_border_file, layer=layer)

        self.selected_countries = country_config.get("selected_countries", [])

    def point_in_domain(
        self, lon: float, lat: float, country: Optional[str] = None
    ) -> bool:
        """Check if point lies within specified country.

        Args:
            lon (float):   Longitude in degrees
            lat (float):   Latitude in degrees
            country (str): (not used) Country where the turbine is located

        Returns:
            bool: True if point is inside domain
        """
        del country
        country = self.l2c.get_country(lon, lat)
        return country in self.selected_countries

    def display_name(self):
        """Gets a display name for readable subsetting filtering."""
        method = "countr" + ("y" if len(self.selected_countries) == 1 else "ies")
        return f"{method}: {', '.join(self.selected_countries)}"
