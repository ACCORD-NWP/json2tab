"""Module for filtering wind turbine location data to a specific domain and timeframe."""

import contextlib
import re
from datetime import date
from typing import Any, Dict

import pandas as pd
from pandas._libs.tslibs.parsing import DateParseError

from ..logs import logger


class TurbineTimeFilterer:
    """Main class for filtering wind turbine location data to a specific domain."""

    def __init__(self, subsetting_config: Dict[str, Any]):
        """Initialize turbine filterer with subsetting configuration."""
        # Init temporal domain cropper
        self.simulation_date = subsetting_config.get("situation_date")

        if self.simulation_date == "today":
            self.simulation_date = date.today()
        elif self.simulation_date == "all":
            self.simulation_date = None
        elif not isinstance(self.simulation_date, date):
            self.simulation_date = pd.to_datetime(self.simulation_date).date()

    def apply(self, data: pd.DataFrame) -> pd.DataFrame:
        """Filter turbine locations to turbines installed at simulation_date.

        Args:
            data (pandas.DataFrame): pandas.DataFrame with turbine locations to filter

        Returns:
            pandas.DataFrame with filtered turbine locations
        """
        data = data[data.apply(lambda turbine: self._timeframe_check(turbine), axis=1)]

        logger.info(
            f"Filtered turbine locations, "
            f"selected {len(data.index)} turbines installed on {self.simulation_date}"
        )

        return data

    def _timeframe_check(self, turbine) -> bool:
        """Checks if turbine has start_date <= simulation_date <= end_date."""
        if self.simulation_date is None:
            return True

        start_date = turbine.get("start_date")
        end_date = turbine.get("end_date")

        is_active_turbine = True

        with contextlib.suppress(Exception):
            if start_date is not None:
                if not isinstance(start_date, date):
                    if isinstance(start_date, (float, int)):
                        year = int(start_date)
                        start_date = date(year, 1, 1)
                    else:
                        try:
                            start_date = pd.to_datetime(start_date).date()
                        except (DateParseError, ValueError) as e:
                            # Look for something like a year
                            match = re.match(r".*?(\d{4}).*", start_date)
                            if match:
                                year = int(match.group(1))
                                start_date = date(year, 1, 1)
                            else:
                                raise e

                is_active_turbine &= start_date <= self.simulation_date

            if end_date is not None:
                if not isinstance(end_date, date):
                    if isinstance(end_date, (float, int)):
                        year = int(end_date)
                        end_date = date(year, 12, 31)
                    else:
                        try:
                            end_date = pd.to_datetime(end_date).date()
                        except (DateParseError, ValueError) as e:
                            # Look for something like a year
                            match = re.match(r".*(\d{4}).*", end_date)
                            if match:
                                year = int(match.groups(0))
                                end_date = date(year, 12, 31)
                            else:
                                raise e

                is_active_turbine &= self.simulation_date <= end_date

        return is_active_turbine
