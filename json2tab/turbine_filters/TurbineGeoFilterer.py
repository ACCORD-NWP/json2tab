"""Module for filtering wind turbine location data to a specific spatial domain."""

from typing import Any, Dict

import pandas as pd

from ..logs import logger
from ..turbine_filters.subsetting_handlers.parse_subsetting_handler import (
    parse_subsetting_handler,
)


class TurbineGeoFilterer:
    """Main class for filtering wind turbine location data to a specific domain."""

    def __init__(self, subsetting_config: Dict[str, Any]):
        """Initialize turbine filterer with subsetting configuration.

        Args:
            subsetting_config (dict): config dict specifying subsetting section
        """
        self.config = subsetting_config
        self.method = subsetting_config["method"]

        self.subsetting_handler = parse_subsetting_handler(subsetting_config)

    def apply(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter turbine locations with domain awareness.

        Args:
            data (pandas.DataFrame): pandas.DataFrame with turbine locations to filter

        Returns:
            pandas.DataFrame with filtered turbine locations
        """
        data = data[data.apply(lambda turbine: self._location_check(turbine), axis=1)]

        logger.info(
            f"Filtered turbine locations, selected {len(data.index)} turbines "
            f"in {self.subsetting_handler.display_name()}."
        )

        return data

    def _location_check(self, turbine) -> bool:
        """Checks if turbine is in domain specified by subsetting handler."""
        lon = turbine.get("longitude")
        lat = turbine.get("latitude")
        country = turbine.get("country")

        return self.subsetting_handler.point_in_domain(lon=lon, lat=lat, country=country)
