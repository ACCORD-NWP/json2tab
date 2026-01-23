"""Module for simplified visualization of wind turbine locations."""


import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from .turbine_filters.subsetting_handlers.DomainHandler import DomainHandler


class SimpleVisualizer:
    """Simplified visualization class for wind turbine locations."""

    def __init__(self, config):
        """Init simplified visualization for wind turbine locations."""
        self.config = config
        self.domain_handler = None

        # Initialize domain handler if using domain method
        if config["subsetting"]["method"] == "domain":
            self.domain_handler = DomainHandler(config["subsetting"]["domain"])

        self.bounds = self._get_bounds()

    def _get_bounds(self):
        """Get domain bounds from config."""
        if self.config["subsetting"]["method"] == "bbox":
            return tuple(self.config["subsetting"]["bbox"])

        # Use domain handler to get bounds
        if self.domain_handler:
            lons, lats = self.domain_handler.get_domain_points()
            return (min(lons), min(lats), max(lons), max(lats))

        # Fallback to config bbox if something goes wrong
        return tuple(
            self.config["subsetting"].get("bbox", [-180, -90, 180, 90])
        )  # Default to global extent

    def create_map(self, turbines: pd.DataFrame, output_path: str):
        """Create stable visualization with proper domain boundary."""
        # Use a simple font configuration to avoid hanging
        mpl.rcParams["font.family"] = ["sans-serif"]
        mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]

        try:
            # Create figure with specified size
            fig, ax = plt.subplots(
                figsize=(12, 8), subplot_kw={"projection": ccrs.PlateCarree()}, dpi=300
            )

            # Add map features with improved styling
            ax.add_feature(cfeature.LAND, facecolor="#f2f2f2")
            ax.add_feature(cfeature.OCEAN, facecolor="#ffffff")
            ax.add_feature(cfeature.COASTLINE, edgecolor="#404040", linewidth=0.5)
            ax.add_feature(
                cfeature.BORDERS, linestyle=":", linewidth=0.5, edgecolor="#606060"
            )

            # Plot turbines
            turbine_lons = turbines["longitude"].tolist()
            turbine_lats = turbines["latitude"].tolist()

            # Plot all turbines at once for better performance
            ax.plot(
                turbine_lons,
                turbine_lats,
                "o",
                color="#ff4444",
                markersize=3,
                transform=ccrs.PlateCarree(),
                label="Turbines",
            )

            if self.domain_handler:
                # Plot domain boundary
                try:
                    lons, lats = self.domain_handler.get_domain_points(resolution=200)
                    ax.plot(
                        lons,
                        lats,
                        "--",
                        color="#202020",
                        linewidth=1.5,
                        transform=ccrs.PlateCarree(),
                        label="Domain",
                        dashes=(5, 5),
                    )

                    # Set extent with padding
                    padding = 0.5
                    ax.set_extent(
                        [
                            min(lons) - padding,
                            max(lons) + padding,
                            min(lats) - padding,
                            max(lats) + padding,
                        ]
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
                        ]
                    )
            else:
                bounds = self.bounds
                ax.set_extent(
                    [bounds[0] - 0.5, bounds[2] + 0.5, bounds[1] - 0.5, bounds[3] + 0.5]
                )

            # Add gridlines with simple styling
            gl = ax.gridlines(
                draw_labels=True, linewidth=0.5, color="gray", alpha=0.5, linestyle="-"
            )
            gl.top_labels = False
            gl.right_labels = False
            gl.xlines = True
            gl.ylines = True

            # Simple title and legend
            ax.set_title("Wind Turbine Locations", fontsize=12)
            ax.legend(loc="upper right")

            # Save figure
            plt.savefig(output_path, bbox_inches="tight", dpi=300)
            plt.close()

        except Exception as e:
            print(f"Error during visualization: {e}")
            plt.close()  # Ensure figure is closed even if there's an error
            raise
