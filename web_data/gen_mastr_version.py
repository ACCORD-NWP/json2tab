"""Util for fetching version of MaStR data."""

import time
from typing import Optional


def gen_mastr_version(
    when: Optional[time.struct_time] = None, use_version: Optional[str] = "current"
) -> str:
    """Generates the current MaStR version.

    The version number is determined according to a fixed release cycle,
    which is by convention in sync with the changes to other german regulatory
    frameworks of the energy such as GeLI Gas and GPKE.

    The release schedule is twice per year on 1st of April and October.
    The version number is determined by the year of release and the running
    number of the release, i.e. the release on April 1st is release 1,
    while the release in October is release 2.

    Further, the release happens during the day, so on the day of the
    changeover, the exported data will still be in the old version/format.

    see <https://www.marktstammdatenregister.de/MaStRHilfe/files/webdienst/Release-Termine.pdf>

    Args:
        when: date for MaStR request
        use_version: use current, previous or next version

    Returns:
        MaStR version

    Examples:
    2024-01-01 = version 23.2
    2024-04-01 = version 23.2
    2024-04-02 = version 24.1
    2024-09-30 = version 24.1
    2024-10-01 = version 24.1
    2024-10-02 = version 24.2
    2024-31-12 = version 24.2

    Function taken from https://github.com/OpenEnergyPlatform/open-MaStR/blob/develop/open_mastr/xml_download/utils_download_bulk.py
    """
    if when is None:
        when = time.localtime()

    year = when.tm_year
    release = 1

    if when.tm_mon < 4 or (when.tm_mon == 4 and when.tm_mday == 1):
        year = year - 1
        release = 2
    elif when.tm_mon > 10 or (when.tm_mon == 10 and when.tm_mday > 1):
        release = 2

    # Change to MaStR version number that was used before
    # For example: 24.1 -> 23.2
    if use_version == "before":
        if release == 1:
            year = year - 1
            release = 2
        else:
            release = 1
    # Change to MaStR version number that was used afterwards
    # For example: 24.1 -> 24.2
    elif use_version == "after":
        if release == 2:
            year = year + 1
            release = 1
        else:
            release = 2

    # only the last two digits of the year are used
    year = str(year)[-2:]
    return f"{year}.{release}"
