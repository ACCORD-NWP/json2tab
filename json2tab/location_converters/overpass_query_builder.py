"""Module with overpass api query builder."""


from datetime import date, datetime
from typing import List, Optional

from dateutil import parser


def build_query(
    windturbine: bool = True,
    windfarm: bool = False,
    area_limit: Optional[List[float] | str] = None,
    requested_date: Optional[datetime | date | str] = None,
) -> str:
    """Returns the overpass query to request data from OSM."""
    # Process area limit
    if area_limit is not None:
        if isinstance(area_limit, str):
            area_limit = area_limit.strip("()")
        elif isinstance(area_limit, list):
            area_limit = ", ".join(str(f) for f in area_limit)
        else:
            area_limit = ""
    else:
        area_limit = ""

    if area_limit != "":
        area_limit = f"({area_limit})"

    # Processing requested date
    if requested_date is not None:
        if isinstance(requested_date, str):
            requested_date = parser.parse(requested_date)

        if isinstance(requested_date, (date, datetime)):
            requested_date = f"{requested_date:%Y-%m-%dT%H:%M:%SZ}"
        else:
            requested_date = ""
    else:
        requested_date = ""

    if requested_date != "":
        requested_date = f'[date:"{requested_date}"]'

    # Header
    query = f"[out:json]{requested_date};"

    if windturbine and windfarm:
        query += "\n("

    if windturbine:
        query += "\n"
        query += f'nwr["power"="generator"]["generator:source"="wind"]{area_limit};'

    if windfarm:
        query += "\n"
        query += f'nwr["power"="plant"]["plant:source"="wind"]{area_limit};'

    if windturbine and windfarm:
        query += "\n);"

    # Footer
    # Get also the turbines marked as way (i.e. a list of grouped nodes)
    query += "\n(._;>;);"
    query += "\nout body;"

    return query
