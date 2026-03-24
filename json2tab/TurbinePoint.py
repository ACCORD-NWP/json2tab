"""Alternative description for a geometry of a turbine."""

import re
from dataclasses import dataclass


@dataclass
class TurbinePoint:
    """Alternative description for a geometry of a turbine."""

    x: float
    y: float

    def centroid(self):
        """Get the centroid of this point."""
        return self

    def __repr__(self):
        return f"POINT ({self.x} {self.y})"

    @classmethod
    def from_wkt(cls, wtk_string: str):
        """Gets the TurbinePoint from a wkt-string."""
        return from_wkt(wtk_string=wtk_string)


def from_wkt(wtk_string: str) -> TurbinePoint:
    """Gets the TurbinePoint from a wkt-string."""
    decimal = r"\d+(\.\d+)?"
    coords = rf"(?P<x>{decimal}) (?P<y>{decimal})"
    match_str = rf"POINT \({coords}\)"
    print(match_str)
    match = re.search(match_str, wtk_string, flags=re.IGNORECASE)

    if match:
        x = float(match.group("x"))
        y = float(match.group("y"))
        return TurbinePoint(x, y)

    return None
