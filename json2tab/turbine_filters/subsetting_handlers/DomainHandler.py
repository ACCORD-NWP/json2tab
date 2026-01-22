"""Domain handler for selecting points in domain based on lat/lon."""

from typing import Optional

import numpy as np
import tomli as toml
from pyproj import CRS, Transformer

from ...DomainConfig import DomainConfig


class DomainHandler:
    """Enhanced domain handler with proper projection support."""

    def __init__(self, domain_config):
        """Initialize domain handler with config.

        Args:
            domain_config: Dictionary from TOML file or Domain object
        """
        if "file" in domain_config:
            domain_file = domain_config["file"]
            with open(domain_file) as stream:
                self.config = toml.loads(stream.read())["domain"]
        else:
            self.config = domain_config

        self.projection = self._setup_projection()
        self.transformer = self._setup_transformer()
        self._extent = None

    def _setup_projection(self):
        """Setup projection based on domain configuration."""
        # Create proj string for Lambert Conformal Conic projection
        proj_string = (
            f"+proj=lcc +lat_0={self.config['xlat0']} "
            f"+lon_0={self.config['xlon0']} "
            f"+lat_1={self.config['xlat0']} "
            f"+lat_2={self.config['xlat0']} "
            "+units=m +no_defs +R=6371000"
        )
        return CRS.from_string(proj_string)

    def _setup_transformer(self):
        """Setup coordinate transformer."""
        return Transformer.from_crs("EPSG:4326", self.projection, always_xy=True)  # WGS84

    @property
    def extent(self):
        """Calculate domain extent in projected coordinates."""
        if self._extent is None:
            # Get center point in projected coordinates
            xc, yc = self.transformer.transform(
                self.config["xloncen"], self.config["xlatcen"]
            )

            # Calculate domain size
            x_range = (float(self.config["njmax"]) - 1.0) * float(self.config["xdx"])
            y_range = (float(self.config["nimax"]) - 1.0) * float(self.config["xdy"])

            # Calculate corners
            self._extent = (
                xc - x_range / 2,  # xmin
                yc - y_range / 2,  # ymin
                xc + x_range / 2,  # xmax
                yc + y_range / 2,  # ymax
            )
        return self._extent

    def get_bounds(self):
        """Get domain bounds based on center coordinates and grid specifications."""
        return DomainConfig.from_config(self.config).get_bounds()

    def point_in_domain(
        self, lon: float, lat: float, country: Optional[str] = None
    ) -> bool:
        """Check if point lies within projected domain.

        Args:
            lon (float):   Longitude in degrees
            lat (float):   Latitude in degrees
            country (str): (not used) Country where the turbine is located

        Returns:
            bool: True if point is inside domain
        """
        del country

        # Transform point to projected coordinates
        x, y = self.transformer.transform(lon, lat)

        # Get domain extent
        xmin, ymin, xmax, ymax = self.extent

        # Check if point is inside rectangle in projected space
        return (xmin <= x <= xmax) and (ymin <= y <= ymax)

    def get_domain_points(self, resolution: int = 100) -> tuple:
        """Get points defining domain boundary in lat/lon.

        Args:
            resolution: Number of points per side

        Returns:
            tuple: Lists of lons, lats defining domain boundary
        """
        # Get inverse transformer
        inv_transformer = Transformer.from_crs(
            self.projection, "EPSG:4326", always_xy=True
        )

        # Get extent
        xmin, ymin, xmax, ymax = self.extent

        # Create arrays of points along boundary
        np.linspace(0, 1, resolution)

        # Create boundary points in projected coordinates
        x_points = []
        y_points = []

        # Bottom edge
        x_points.extend(np.linspace(xmin, xmax, resolution))
        y_points.extend([ymin] * resolution)

        # Right edge
        x_points.extend([xmax] * resolution)
        y_points.extend(np.linspace(ymin, ymax, resolution))

        # Top edge
        x_points.extend(np.linspace(xmax, xmin, resolution))
        y_points.extend([ymax] * resolution)

        # Left edge
        x_points.extend([xmin] * resolution)
        y_points.extend(np.linspace(ymax, ymin, resolution))

        # Transform back to lat/lon
        lons, lats = inv_transformer.transform(x_points, y_points)

        return lons, lats


def filter_points_by_domain(points, domain_handler):
    """Filter points based on domain boundary.

    Args:
        points: List of (lon, lat) tuples
        domain_handler: DomainHandler instance

    Returns:
        list: Filtered points inside domain
    """
    return [
        point for point in points if domain_handler.point_in_domain(point[0], point[1])
    ]
