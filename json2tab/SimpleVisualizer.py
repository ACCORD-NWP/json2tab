"""Module for simplified visualization of wind turbine locations."""

import contextlib

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer

from .turbine_filters.subsetting_handlers.BoundingBoxHandler import BoundingBoxHandler
from .turbine_filters.subsetting_handlers.parse_subsetting_handler import (
    parse_subsetting_handler,
)


class SimpleVisualizer:
    """Simplified visualization class for wind turbine locations."""

    def __init__(self, config):
        """Initialize simple visualizer with configuration.

        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.viz_config = config.get("visualization", {})
        self.subsetting_handler = parse_subsetting_handler(config["subsetting"])

        self._setup_projection()

    def _setup_projection(self):
        """Setup projection used in simple visualizer."""

        self.projection = ccrs.PlateCarree()

    def _get_bounds(self):
        """Get domain bounds from config."""

        with contextlib.suppress(Exception):
            bounds = self.subsetting_handler.get_bounds()
            if bounds:
                return bounds + (self.subsetting_handler.display_name(),)

        # Fallback to config bbox (or global extend) if something went wrong
        default_global = [-180, -90, 180, 90]

        with contextlib.suppress(Exception):
            bbox = BoundingBoxHandler(self.config["subsetting"]["bbox"])
            bounds = bbox.get_bounds()
            if bounds:
                return bounds + (bbox.display_name(),)

        return tuple(default_global) + ("Global extend",)

    def _get_extent(self):
        """Get domain extent from config."""

        with contextlib.suppress(Exception):
            extent = self.subsetting_handler.extent
            if extent:
                return extent + (
                    self.subsetting_handler.display_name(),
                    self.subsetting_handler.projection,
                )

        # Fallback to converted bounds
        return self._get_bounds() + (self.projection,)

    def _compute_domain_boundary(self, resolution: int = 100) -> tuple:
        """Get points defining domain boundary in lat/lon.

        Args:
            resolution: Number of points per side

        Returns:
            tuple: Lists of lons, lats defining domain boundary
        """

        # Get extent
        xmin, ymin, xmax, ymax, domain_name, projection = self._get_extent()

        # Get inverse transformer
        inv_transformer = Transformer.from_crs(projection, "EPSG:4326", always_xy=True)

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

        return lons, lats, domain_name

    def create_map_plot(self, turbines: pd.DataFrame, output_path: str):
        """Create stable visualization with proper domain boundary."""
        # Use a simple font configuration to avoid hanging

        try:
            # Create figure with specified size

            figure_viz = self.viz_config.get("figure", {})
            width = figure_viz.get("width", 12)
            height = figure_viz.get("height", 8)
            dpi = figure_viz.get("dpi", 300)

            fig, ax = plt.subplots(
                figsize=(width, height),
                subplot_kw={"projection": self.projection},
                dpi=dpi,
            )

            basemap_viz = self.viz_config.get("basemap", {})

            # Add map features with improved styling
            ax.add_feature(
                cfeature.LAND,
                facecolor=basemap_viz.get("land", {}).get("color", "#f2f2f2"),
            )
            ax.add_feature(
                cfeature.OCEAN,
                facecolor=basemap_viz.get("ocean", {}).get("color", "#ffffff"),
            )
            ax.add_feature(
                cfeature.LAKES,
                facecolor=basemap_viz.get("lake", {}).get("color", "#fcfcfc"),
            )
            ax.add_feature(
                cfeature.COASTLINE,
                edgecolor=basemap_viz.get("coastline", {}).get("color", "#404040"),
                linewidth=basemap_viz.get("coastline", {}).get("linewidth", 0.5),
            )
            ax.add_feature(
                cfeature.BORDERS,
                linestyle=basemap_viz.get("border", {}).get("linestyle", ":"),
                linewidth=basemap_viz.get("border", {}).get("linewidth", 0.5),
                edgecolor=basemap_viz.get("border", {}).get("color", "#606060"),
            )

            turbine_viz = self.viz_config.get("turbines", {})

            # Plot domain boundary
            domain_viz = self.viz_config.get("domain", {})
            try:
                lons, lats, domain_name = self._compute_domain_boundary(resolution=200)
                ax.plot(
                    lons,
                    lats,
                    domain_viz.get("linestyle", "--"),
                    color=domain_viz.get("color", "#202020"),
                    linewidth=domain_viz.get("linewidth", 1.5),
                    transform=self.projection,
                    label=domain_name,
                    dashes=(5, 5),
                )

                # Set extent with padding
                padding_lon = (max(lons) - min(lons)) * 0.05
                padding_lat = (max(lats) - min(lats)) * 0.05
                ax.set_extent(
                    [
                        min(lons) - padding_lon,
                        max(lons) + padding_lon,
                        min(lats) - padding_lat,
                        max(lats) + padding_lat,
                    ],
                    crs=self.projection,
                )
            except Exception as e:
                print(f"Warning: Could not plot domain boundary: {e}")
                # Fall back to data extent
                ax.set_extent(
                    [
                        min(turbine_lons) - 0.5,
                        max(turbine_lons) + 0.5,
                        min(turbine_lats) - 0.5,
                        max(turbine_lats) + 0.5,
                    ],
                    crs=self.projection,
                )

            # Plot turbines
            if len(turbines) > 0:
                turbine_lons = turbines["longitude"].tolist()
                turbine_lats = turbines["latitude"].tolist()

                # Plot all turbines at once for better performance
                ax.plot(
                    turbine_lons,
                    turbine_lats,
                    turbine_viz.get("marker", {}).get("symbol", "o"),
                    color=turbine_viz.get("marker", {}).get("color", "#ff4444"),
                    markersize=turbine_viz.get("marker", {}).get("size", 3),
                    transform=self.projection,
                    label=f"Turbines (#{len(turbines)})",
                )

            grid_viz = self.viz_config.get("gridlines", {})
            # Add gridlines with simple styling
            gl = ax.gridlines(
                draw_labels=grid_viz.get("draw_labels", True),
                linewidth=grid_viz.get("linewidth", 0.5),
                color=grid_viz.get("color", "gray"),
                alpha=grid_viz.get("alpha", 0.5),
                linestyle=grid_viz.get("linestyle", "-"),
            )

            gl.top_labels = False
            gl.right_labels = False
            gl.xlines = True
            gl.ylines = True

            # Simple title and legend
            title_viz = self.viz_config.get("title", {})
            ax.set_title("Wind Turbine Locations", fontsize=title_viz.get("fontsize", 12))

            legend_loc = figure_viz.get("legend", "upper right")
            if legend_loc:
                ax.legend(loc=legend_loc)

            # Save figure
            plt.savefig(output_path, bbox_inches="tight", dpi=dpi)
            plt.close()

        except Exception as e:
            print(f"Error during visualization: {e}")
            plt.close()  # Ensure figure is closed even if there's an error
            raise
