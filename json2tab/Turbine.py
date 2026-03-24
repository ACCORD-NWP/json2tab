"""Main data description that describes a turbine."""

import inspect
from dataclasses import asdict, dataclass, field
from datetime import date

try:
    from shapely.geometry import Point
except ImportError:
    # Use TurbinePoint as backup for point
    from .TurbinePoint import TurbinePoint as Point


@dataclass
class Turbine:
    """Turbine description in location database."""

    id: str = None
    turbine_id: str = None
    name: str = None
    latitude: float = None
    longitude: float = None
    hub_height: float = None
    power_rating: float = None
    radius: float = None
    diameter: float = None

    manufacturer: str = None
    type: str = None

    rated_speed: str = None
    cut_in_speed: str = None
    cut_out_speed: str = None

    height_offset: float = None
    wind_farm: str = None
    n_turbines: int = None
    operator: str = None

    start_date: date = None
    end_date: date = None

    source: str = None
    is_offshore: str = None
    country: str = None

    geometry: Point
    _geometry: Point = field(init=False, repr=False)

    @property
    def geometry(self) -> Point:
        """Get geometry for Turbine."""
        if not isinstance(self._geometry, property):
            return self._geometry

        if self.latitude is not None and self.longitude is not None:
            return Point(self.longitude, self.latitude)

        return None

    @geometry.setter
    def geometry(self, value: Point):
        """Set geometry for Turbine."""
        self._geometry = value

        if (
            isinstance(self._geometry, Point)
            and self.latitude is None
            and self.longitude is None
        ):
            self.longitude = self._geometry.x
            self.latitude = self._geometry.y

    def to_dict(self):
        """Converts a Turbine to a dict."""
        turbine_as_dict = dict(asdict(self).items())

        private_keys = [k for k in turbine_as_dict if k.startswith("_")]
        for private_key in private_keys:
            turbine_as_dict.pop(private_key)

        return turbine_as_dict

    def is_valid(self):
        """Checks if turbine has valid coordinates."""
        if self.latitude is None or self.longitude is None:
            return False

        return self.latitude == self.latitude and self.longitude == self.longitude

    @classmethod
    def from_dict(cls, data: dict):
        """Gets a Turbine from a dict."""
        params = inspect.signature(cls).parameters

        return cls(**{k: v for k, v in data.items() if k in params})
