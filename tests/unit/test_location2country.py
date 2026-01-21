from pathlib import Path

import pytest

from json2tab.tools.Location2CountryConverter import Location2CountryConverter

COUNTRY_BORDER_FILE = "static_data/worldmap/country_borders/countries.geojson"
EEZ_BORDER_FILE = "static_data/worldmap/EEZ/EEZ_land_union_v4_202410.shp"
GADM_NETHERLANDS_FILE = "static_data/worldmap/Netherlands/gadm41_NLD_fixZH.gpkg"


@pytest.mark.skipif(
    not Path(COUNTRY_BORDER_FILE).is_file(), reason="Country land border file not found"
)
@pytest.mark.skipif(
    not Path(EEZ_BORDER_FILE).is_file(), reason="Country EEZ border file not found"
)
@pytest.mark.parametrize(
    ("country_border_file", "lon", "lat", "expected"),
    [
        (COUNTRY_BORDER_FILE, 4.8944, 52.3722, "NLD"),
        (COUNTRY_BORDER_FILE, 4.3523, 50.8484, "BEL"),
        (COUNTRY_BORDER_FILE, 16.3717, 48.2087, "AUT"),
        (COUNTRY_BORDER_FILE, 2.36342, 48.82634, "FRA"),
        (COUNTRY_BORDER_FILE, 2.9772590, 51.6698336, None),
        (COUNTRY_BORDER_FILE, 2.9120371, 51.6446948, None),
        (EEZ_BORDER_FILE, 4.8944, 52.3722, "NLD"),
        (EEZ_BORDER_FILE, 4.3523, 50.8484, "BEL"),
        (EEZ_BORDER_FILE, 16.3717, 48.2087, "AUT"),
        (EEZ_BORDER_FILE, 2.36342, 48.82634, "FRA"),
        (EEZ_BORDER_FILE, 2.9772590, 51.6698336, "NLD"),
        (EEZ_BORDER_FILE, 2.9120371, 51.6446948, "BEL"),
    ],
)
def test_country_borders_iso3(country_border_file, lon, lat, expected):
    l2c = Location2CountryConverter(country_border_file, prefer_iso3=True)
    country = l2c.get_country(lon, lat)
    assert country == expected


@pytest.mark.skipif(
    not Path(GADM_NETHERLANDS_FILE).is_file(), reason="Netherlands border file not found"
)
@pytest.mark.parametrize(
    ("country_border_file", "lon", "lat", "expected"),
    [
        (GADM_NETHERLANDS_FILE, 2.9772590, 51.6698336, [None, None]),
        (GADM_NETHERLANDS_FILE, 2.9120371, 51.6446948, [None, None]),
        (GADM_NETHERLANDS_FILE, 5.2591827, 52.9995252, ["NLD", "IJsselmeer"]),
        (GADM_NETHERLANDS_FILE, 5.6307759, 52.6390398, ["NLD", "IJsselmeer"]),
        (GADM_NETHERLANDS_FILE, 5.25940, 52.99968, ["NLD", "IJsselmeer"]),
        (GADM_NETHERLANDS_FILE, 5.5773504, 52.5881853, ["NLD", "NL-FL"]),
        (GADM_NETHERLANDS_FILE, 5.3314740, 52.3565186, ["NLD", "NL-FL"]),
        (GADM_NETHERLANDS_FILE, 5.119280, 52.013647, ["NLD", "NL-UT"]),
        (GADM_NETHERLANDS_FILE, 3.9753655, 51.9780770, ["NLD", "NL-ZH"]),
    ],
)
def test_netherlands_iso3(country_border_file, lon, lat, expected):
    for level in [0, 1]:
        l2c = Location2CountryConverter(country_border_file, level, prefer_iso3=True)
        country = l2c.get_country(lon, lat)
        assert country == expected[level]


@pytest.mark.skipif(
    not Path(COUNTRY_BORDER_FILE).is_file(), reason="Country land border file not found"
)
@pytest.mark.skipif(
    not Path(EEZ_BORDER_FILE).is_file(), reason="Country EEZ border file not found"
)
@pytest.mark.parametrize(
    ("country_border_file", "lon", "lat", "expected"),
    [
        (COUNTRY_BORDER_FILE, 4.8944, 52.3722, "Netherlands"),
        (COUNTRY_BORDER_FILE, 4.3523, 50.8484, "Belgium"),
        (COUNTRY_BORDER_FILE, 16.3717, 48.2087, "Austria"),
        (COUNTRY_BORDER_FILE, 2.36342, 48.82634, "France"),
        (COUNTRY_BORDER_FILE, 2.9772590, 51.6698336, None),
        (COUNTRY_BORDER_FILE, 2.9120371, 51.6446948, None),
        (EEZ_BORDER_FILE, 4.8944, 52.3722, "Netherlands"),
        (EEZ_BORDER_FILE, 4.3523, 50.8484, "Belgium"),
        (EEZ_BORDER_FILE, 16.3717, 48.2087, "Austria"),
        (EEZ_BORDER_FILE, 2.36342, 48.82634, "France"),
        (EEZ_BORDER_FILE, 2.9772590, 51.6698336, "Netherlands"),
        (EEZ_BORDER_FILE, 2.9120371, 51.6446948, "Belgium"),
    ],
)
def test_country_borders_name(country_border_file, lon, lat, expected):
    l2c = Location2CountryConverter(country_border_file, prefer_iso3=False)
    country = l2c.get_country(lon, lat)
    assert country == expected


@pytest.mark.skipif(
    not Path(GADM_NETHERLANDS_FILE).is_file(), reason="Netherlands border file not found"
)
@pytest.mark.parametrize(
    ("country_border_file", "lon", "lat", "expected"),
    [
        (GADM_NETHERLANDS_FILE, 2.9772590, 51.6698336, [None, None, None]),
        (GADM_NETHERLANDS_FILE, 2.9120371, 51.6446948, [None, None, None]),
        (
            GADM_NETHERLANDS_FILE,
            5.2591827,
            52.9995252,
            ["Netherlands", "IJsselmeer", "IJsselmeer"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            5.6307759,
            52.6390398,
            ["Netherlands", "IJsselmeer", "IJsselmeer"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            5.25940,
            52.99968,
            ["Netherlands", "IJsselmeer", "IJsselmeer"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            5.5773504,
            52.5881853,
            ["Netherlands", "Flevoland", "Lelystad"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            5.3314740,
            52.3565186,
            ["Netherlands", "Flevoland", "Almere"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            5.119280,
            52.013647,
            ["Netherlands", "Utrecht", "Nieuwegein"],
        ),
        (
            GADM_NETHERLANDS_FILE,
            3.9753655,
            51.9780770,
            ["Netherlands", "Zuid-Holland", "Rotterdam"],
        ),
    ],
)
def test_netherlands_name(country_border_file, lon, lat, expected):
    for level in [0, 1, 2]:
        l2c = Location2CountryConverter(country_border_file, level, prefer_iso3=False)
        country = l2c.get_country(lon, lat)
        assert country == expected[level]
