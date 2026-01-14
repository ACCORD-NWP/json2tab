"""Main data description that describes a turbine."""

import inspect
from dataclasses import asdict, dataclass
from datetime import date


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

    def to_dict(self):
        """Converts a Turbine to a dict."""
        return dict(asdict(self).items())

    @classmethod
    def from_dict(cls, data: dict):
        """Gets a Turbine from a dict."""
        params = inspect.signature(cls).parameters

        return cls(**{k: v for k, v in data.items() if k in params})
