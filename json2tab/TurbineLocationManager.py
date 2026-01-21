"""Module for reading and processing wind turbine location data from file(s)."""

from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from .io.readers import read_locationdata_as_dataframe
from .turbine_utils import standarize_dataframe
from .logs import logger
from .utils import unify_file_list


class TurbineLocationManager:
    """Main class for reading and processing wind turbine location data from file(s)."""

    def __init__(
        self, location_data_file: Optional[Path | List[Path] | str | List[str]] = None
    ):
        """Initialize turbine location loader.

        Args:
            location_data_file: (Optional) one or more files with turbine location data
        """
        self.reset_turbines()

        if location_data_file is not None:
            self.load_turbines(location_data_file)

    def reset_turbines(self):
        """Reset turbine location data."""
        self.turbines = None
        self.location_files = []

    def load_turbines(self, location_data_file: Path | List[Path] | str | List[str]):
        """Load turbine location data from file(s).

        Args:
            location_data_file: one or more files with turbine location data

        Raises:
            FileNotFoundError: if a single provided location file cannot be found
        """
        location_files = unify_file_list(location_data_file)

        logger.debug(
            "Loading windturbine location data from the following "
            f"file{'(s)' if len(location_files) > 1 else ''}: "
            f"{' '.join(str(p) for p in location_files)}"
        )

        for location_file in location_files:
            if location_file.exists():
                self.location_files.append(location_file)

                df_file = read_locationdata_as_dataframe(location_file)
                if df_file is not None:
                    df_file = standarize_dataframe(df_file)
                    self.turbines = pd.concat([self.turbines, df_file])
            elif len(location_files) == 1:
                raise FileNotFoundError(
                    f"Turbine location file '{location_file!s}' not found."
                )
            else:
                logger.error(
                    f"Turbine location file '{location_file!s}' not found, "
                    "multiple files provided. Let's skip this file"
                )

        # Set all nan's to None in specs table
        self.turbines = self.turbines.replace({np.nan: None})

    def filter_turbines(self, filterer):
        """Appy a turbine filter to to managed turbines.

        Args:
            filterer: A TurbineFilterer to filter wind turbines
        """
        self.turbines = filterer.apply(self.turbines)
