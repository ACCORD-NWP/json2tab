"""Module for filtering wind turbine location data to a specific spatial domain."""

from typing import Any, Dict

import pandas as pd

from ..logs import logger
from ..turbine_filters.subsetting_handlers.BoundingBoxHandler import BoundingBoxHandler
from ..turbine_filters.subsetting_handlers.CountryHandler import CountryHandler
from ..turbine_filters.subsetting_handlers.DomainHandler import DomainHandler
from ..turbine_filters.subsetting_handlers.TrueHandler import TrueHandler


class TurbineGeoFilterer:
    """Main class for filtering wind turbine location data to a specific domain."""

    def __init__(self, subsetting_config: Dict[str, Any]):
        """Initialize turbine filterer with subsetting configuration.

        Args:
            subsetting_config (dict): config dict specifying subsetting section
        """
        # Validate spatial subsetting configuration
        self.method = subsetting_config["method"]
        if self.method not in subsetting_config:
            raise ValueError(f"{self.method} configuration missing")

        self.config = subsetting_config

        if self.method == "domain":
            self.subsetting_handler = DomainHandler(self.config["domain"])
        elif self.method == "bbox":
            self.subsetting_handler = BoundingBoxHandler(self.config["bbox"])
        elif self.method == "country":
            self.subsetting_handler = CountryHandler(self.config["country"])
        elif self.method == "true":
            self.subsetting_handler = TrueHandler()
        else:
            logger.error(
                f"Subsetting method must be either 'bbox, 'country' or 'domain', "
                f"found method = {self.method}."
            )
            self.subsetting_handler = None

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
