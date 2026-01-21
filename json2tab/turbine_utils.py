"""Basic utils to process dataframe and Turbine-data."""

import contextlib
import math
from typing import Optional

import pandas as pd

from .location_converters.get_lat_lon_matrix import get_lat_lon_matrix
from .logs import logger
from .Turbine import Turbine
from .utils import (
    get_height,
    get_installed_power,
    get_radius,
    get_rated_power_kw,
    get_value_from_dict,
    power_to_kw,
)


def standarize_dataframe(data: pd.DataFrame, always: bool = False) -> pd.DataFrame:
    """Convertion a pandas.DataFrame to a dataframe with standarized turbine fields.

    Args:
        data (pandas.DataFrame): The dataframe containing turbine information
        always: Flag indicating converting is done, even when all columns are mappable

    Returns:
        pandas.DataFrame with standarized turbine information
    """
    turbine_keys = set(Turbine().to_dict().keys())

    if always or (data is not None and len(set(data.columns) - turbine_keys) > 0):
        # Convert data rows to interpret the rows as standarized Turbine
        logger.debug(
            f"Converting info for {len(data.index)} turbines to "
            "standarized turbine data."
        )

        turbines = []
        for _, row in data.iterrows():
            turbines.append(datarow_to_turbine(row))

        data = pd.DataFrame(turbines)
    return data


def datarow_to_turbine(row) -> Turbine:
    """Convert data row to Turbine."""
    return merge_turbine_data(row, None)


def merge_turbine_data(
    preferred_source, alternative_source, merged_source_name: Optional[str] = None
) -> Turbine:
    """Merge turbine data from two sources.

    Args:
        preferred_source:   Preferred source to provide turbine information
        alternative_source: Alternative source to provide turbine information
        merged_source_name: (Optional) Source name when data from two sources is used

    Returns:
        Merged turbine
    """
    alternative_used = False

    id_field, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["id", "ID", "GSRN", "Turbine identifier (GSRN)", "Verk-ID"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    name, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["name", "Name", "naam", "Turbine", "WFNAME", "nr_turbine", "Location"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    name2, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["2nd name", "alt_name", "alt name"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    if name2 is not None and not (isinstance(name2, float) and math.isnan(name2)):
        if str(name2).lower().startswith(str(name).lower()):
            name = name2
        else:
            name = f"{name} ({name2})"

    turbine_id, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            [
                "turbine_id",
                "turbine_nr",
                "nr_turbine",
                "turbine id",
                "Turbine identifier (GSRN)",
            ],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    lat_lon = get_lat_lon_matrix(
        preferred_source
        if isinstance(preferred_source, dict)
        else preferred_source.to_dict()
    )
    lat, lon = lat_lon[0, 0], lat_lon[0, 1]

    manufacturer, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["manufacturer", "Manufacturer", "Manufacture", "Fabrikat"],
            source if isinstance(source, dict) else source.to_dict(),
            default=default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    model_type, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            [
                "type",
                "wt_type",
                "WTYPE",
                "turbine_type",
                "model",
                "Type designation",
                "Model wind turbine",
                "Modell",
                "Turbine",
            ],
            source if isinstance(source, dict) else source.to_dict(),
            default=default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    if model_type is None:
        # Only use WF-101 type if we realy don't have any other type
        model_type, alternative_used = fetch_data(
            lambda source, default=None: get_value_from_dict(
                ["wf101_type"],
                source if isinstance(source, dict) else source.to_dict(),
                default=default,
            ),
            preferred_source,
            alternative_source,
            alternative_used,
        )

    hub_height, alternative_used = fetch_data(
        lambda source, default=None: get_height(source, default=default),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    radius, alternative_used = fetch_data(
        lambda source, default=None: get_radius(source, default=default),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    rated_power, alternative_used = fetch_data(
        lambda source, default=None: get_rated_power_kw(source, default=default),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    is_offshore, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["is_offshore", "ondergrond", "Type of location", "Placering"],
            source if isinstance(source, dict) else source.to_dict(),
            default=default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    wind_farm, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            [
                "nicename",
                "windfarm",
                "wind_farm",
                "WFNAME",
                "site",
                "farm id",
                "name",
                "Name",
                "naam",
                "Location",
                "Projekteringsområde",
            ],
            source if isinstance(source, dict) else source.to_dict(),
            default=default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    n_turbines, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["n_turbines", "Number of turbines", "No. of wind turbines"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    if n_turbines is not None and (not wind_farm):
        wind_farm = name

    if rated_power is None and n_turbines is not None:
        installed_power, alternative_used = fetch_data(
            lambda source, default=None: get_installed_power(source, default=default),
            preferred_source,
            alternative_source,
            alternative_used,
        )
        if installed_power is not None:
            if n_turbines > 0:
                rated_power = power_to_kw(installed_power / n_turbines)
            else:
                logger.warning(
                    f"Installed power is provided for windfarm '{wind_farm}' "
                    f"but n_turbines={n_turbines}; "
                    "so the rated_power for this windfarm is ignored"
                )

    start_date, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            [
                "start_date",
                "commission_date",
                "commissioning",
                "Date of commission",
                "year",
                "Date of original connection to grid",
                "Uppfört",
                "Commissioning date",
            ],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    end_date, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            [
                "end_date",
                "decommission_date",
                "decommissioning",
                "Date of decommissioning",
                "Date of decommissioning",
                "Nedmonterat",
                "Decommissioning date",
            ],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    country, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["country", "Country", "land"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    cut_in_speed, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["cut_in_speed", "v_in"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    cut_out_speed, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["cut_out_speed", "v_out"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    rated_speed, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["rated_speed", "v_rated"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    operator, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["operator"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )
    height_offset, alternative_used = fetch_data(
        lambda source, default=None: get_value_from_dict(
            ["height_offset", "Markhöjd (m)"],
            source if isinstance(source, dict) else source.to_dict(),
            default,
        ),
        preferred_source,
        alternative_source,
        alternative_used,
    )

    # Parse is_offshore field
    if is_offshore is not None:
        if isinstance(is_offshore, str) and is_offshore.lower() in [
            "zee",
            "hav",
            "vatten",
        ]:
            is_offshore = True
        elif isinstance(is_offshore, str) and is_offshore.lower() in ["land"]:
            is_offshore = False
        else:
            with contextlib.suppress(ValueError):
                is_offshore = bool(is_offshore)

    diameter = 2 * radius if radius is not None else None

    # Determine source
    if alternative_used:
        source = (
            merged_source_name
            or f"{preferred_source.get('source')}+{alternative_source.get('source')}"
        )
    else:
        source = preferred_source.get("source")

    if is_offshore and name == wind_farm:
        name = f"{wind_farm} {turbine_id}"

    return Turbine(
        id=id_field,
        name=name,
        turbine_id=turbine_id,
        latitude=lat,
        longitude=lon,
        manufacturer=manufacturer,
        type=model_type,
        hub_height=hub_height,
        radius=radius,
        diameter=diameter,
        power_rating=rated_power,
        is_offshore=is_offshore,
        wind_farm=wind_farm,
        source=source,
        start_date=start_date,
        end_date=end_date,
        n_turbines=n_turbines,
        country=country,
        cut_in_speed=cut_in_speed,
        cut_out_speed=cut_out_speed,
        rated_speed=rated_speed,
        height_offset=height_offset,
        operator=operator,
    )


def fetch_data(
    fetcher, preferred_source, alternative_source, alternative_used: bool = False
):
    """Fetch data from preferred or alternative source using fetcher."""
    ignored_values = [None, "", 0, "NaN"]

    output = fetcher(preferred_source)
    if (
        output in ignored_values or (isinstance(output, float) and math.isnan(output))
    ) and alternative_source is not None:
        output = fetcher(alternative_source, None)
        alternative_used = alternative_used or (output not in ignored_values)

    return output, alternative_used
