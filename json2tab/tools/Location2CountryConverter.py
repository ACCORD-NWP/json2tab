"""Converter to convert lat/lon location to country code."""

import json
from pathlib import Path
from typing import Optional

import geopandas as gpd
from shapely.geometry import Point, shape
from shapely.prepared import prep

from ..logs import logger


class Location2CountryConverter:
    """Converts lat/lon locations to country code."""

    def __init__(
        self,
        country_border_file: str,
        level: Optional[int] = None,
        layer: Optional[str] = None,
        prefer_iso3: bool = False,
    ):
        """Initialize location to country converter.

        Args:
            country_border_file: Filename with border information of countries
            level:               (Optional) level 0=Country, 1=Province, 2=Municipality
            layer:               (Optional) layer to load from file_name
            prefer_iso3:         (Optional) Indicate if ISO-3 country codes are prefered,
                                 default: False
        """
        full_name = ["name", "UNION", "NAM_0"]
        iso3_name = ["ISO3166-1-Alpha-3", "ISO_TER1", "ISO_A3"]
        country_field = iso3_name + full_name if prefer_iso3 else full_name + iso3_name

        if Path(country_border_file).suffix.lower() in {".json", ".geojson"}:
            logger.debug(
                f"Load countries using JSON loader from: '{country_border_file}'"
            )
            self.countries = Location2CountryConverter._countries_from_json_file(
                country_border_file, country_field=country_field
            )
        elif Path(country_border_file).suffix.lower() in {".gpkg", ".shp"}:
            logger.debug(
                f"Load countries using GeoPandas loader from: '{country_border_file}'"
            )

            if level is not None:
                logger.debug(f"level = '{level}'")

            if (layer is None and level is not None) and level in {0, 1, 2}:
                # Process layer for GADM map files (https://gadm.org)
                layer = f"ADM_ADM_{level}"

                full_name = [f"NAME_{level}"]
                iso3_name = [f"ISO_{level}"]
                backup_full = ["COUNTRY"]
                backup_iso3 = ["GID_0"]

                if prefer_iso3:
                    country_field = iso3_name + full_name + backup_iso3 + backup_full
                else:
                    country_field = full_name + iso3_name + backup_full + backup_iso3

            if layer is not None:
                logger.debug(f"layer = '{layer}'")

            self.countries = Location2CountryConverter._countries_from_geopandas_file(
                country_border_file, layer=layer, country_field=country_field
            )
        else:
            logger.error(
                f"Unknown file extension in '{country_border_file}'; "
                "supported types .json, .geojson, .gpkg, .shp"
            )
            self.countries = {}

        logger.debug(f"Loaded {len(self.countries)} countries")

    def get_country(self, lon, lat):
        """Gets the country of a lat/lon coordinate."""
        point = Point(lon, lat)
        for country, geom_list in self.countries.items():
            for geom in geom_list:
                if geom.contains(point):
                    return country

        return None

    @staticmethod
    def _countries_from_json_file(
        file_name, country_field="name", geometry_field="geometry"
    ):
        """Load country boarder data from json file.

        Args:
            file_name (str):      Filename of json file with country border information
            country_field (str):  Fieldname in properties for country,
                                  eg 'name', 'ISO3166-1-Alpha-2' or 'ISO3166-1-Alpha-3'
            geometry_field (str): Fieldname containing the geometry

        Returns:
            Dictionary with geometries per country
        """
        # Convert single country_field to list of fields to support alternatives
        if isinstance(country_field, str):
            country_field = [country_field]

        logger.debug(f"country_field = '{country_field}' (len={len(country_field)})")
        logger.debug(f"geometry_field = '{geometry_field}'")

        countries = {}
        with open(file_name) as file:
            data = json.load(file)

            for feature in data["features"]:
                country = None
                for field in country_field:
                    if field in feature["properties"]:
                        country = feature["properties"][field]
                        if country not in [None, "N/A", "NA", "", "-99"]:
                            break

                geometry = feature[geometry_field]

                if country is not None:
                    if country not in countries:
                        countries[country] = []
                    countries[country].append(prep(shape(geometry)))

        return countries

    @staticmethod
    def _countries_from_geopandas_file(
        file_name: str,
        layer: Optional[str] = None,
        country_field: Optional[str] = "ISO_TER1",
        geometry_field: Optional[str] = "geometry",
    ):
        """Load country boarder data using geopandas (shapefile, gpkg, ...).

        Args:
            file_name (str):      Filename of json file with country border information
            layer (str):          (Optional) layer to load from file_name
            country_field (str):  Fieldname in properties for country,
                                  eg 'ISO_TER1', 'TERRITORY1'
            geometry_field (str): Fieldname containing the geometry

        Returns:
            Dictionary with geometries per country
        """
        # Convert single country_field to list of fields to support alternatives
        if isinstance(country_field, str):
            country_field = [country_field]

        logger.debug(f"country_field = '{country_field}' (len={len(country_field)})")
        logger.debug(f"geometry_field = '{geometry_field}'")

        data = gpd.read_file(file_name, layer=layer)

        countries = {}
        for _, row in data.iterrows():
            country = None
            for field in country_field:
                if field in row:
                    country = row[field]
                    if country not in [None, "N/A", "NA", "", "-99"]:
                        break
            geometry = row[geometry_field]

            if country is not None:
                if country not in countries:
                    countries[country] = []
                countries[country].append(prep(shape(geometry)))

        return countries
