"""Converter to generate wind turbine location files for Germany.

Input data based on MarktStammdatenRegister.
"""

import os
from typing import Optional

import pandas as pd

from ...io.writers import save_dataframe
from ...logs import logger
from ...Turbine import Turbine


def germany(
    input_filename: str,
    output_filename: Optional[str] = None,
    katalog_file: Optional[str] = None,
    label_source: str = "Germany (MaStR)",
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Germany."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(
        f"Germany MarktStammdatenRegister Xml Converter "
        f"({input_filename} -> {output_filename})"
    )

    if katalog_file is None:
        dirname = os.path.dirname(input_filename)
        katalog_file = f"{dirname}/Katalogwerte.xml"
        logger.info(f"No katalog file provided; assuming katalog file is {katalog_file}")

    katalog = pd.read_xml(katalog_file, encoding="utf-16")

    if label_source is None:
        _, label_source = os.path.split(input_filename)
    logger.info(f"Set source-field for {input_filename} to '{label_source}'")

    df_in = pd.read_xml(input_filename, encoding="utf-16")

    turbines = []
    logger.info(f"Processing {len(df_in.index)} wind turbines")

    for _, row in df_in.iterrows():
        manufacturer = get_value_from_catalog(katalog, row.get("Hersteller"))
        if manufacturer == "Sonstige":
            manufacturer = None

        if manufacturer is not None:
            # Cleanup some manufacturer strange values
            manufacturer = manufacturer.replace("Deutschland", "")
            manufacturer = manufacturer.replace("GmbH", "")
            manufacturer = manufacturer.strip()

        diameter = row.get("Rotordurchmesser")

        turbine = Turbine(
            id=row.get("EinheitMastrNummer"),
            turbine_id=row.get("EegMaStRNummer"),
            name=row.get("NameStromerzeugungseinheit"),
            latitude=row.get("Breitengrad"),
            longitude=row.get("Laengengrad"),
            hub_height=row.get("Nabenhoehe"),
            power_rating=row.get("Nettonennleistung") or row.get("Bruttoleistung"),
            diameter=diameter,
            radius=diameter / 2,
            manufacturer=manufacturer,
            type=row.get("Typenbezeichnung"),
            wind_farm=row.get("NameWindpark"),
            start_date=row.get("InbetriebnahmedatumAmAktuellenStandort")
            or row.get("Inbetriebnahmedatum"),
            end_date=row.get("DatumEndgueltigeStilllegung"),
            source=label_source,
            is_offshore=get_value_from_catalog(katalog, row.get("WindAnLandOderAufSee"))
            == "Windkraft auf See",
            country="Germany",
        )

        if (
            (
                turbine.latitude == turbine.latitude
                and turbine.longitude == turbine.longitude
            )
            and turbine.start_date is not None
            and turbine.start_date != ""
        ):
            turbines.append(turbine)

    data = pd.DataFrame(turbines)
    save_dataframe(data, output_filename)
    return data


def get_value_from_catalog(catalog, catalog_id):
    """Gets value from catalog by catalog_id."""
    if catalog_id is None:
        return None

    items = catalog[catalog["Id"] == catalog_id]
    if len(items) > 0:
        return items["Wert"].iloc[0]

    return None
