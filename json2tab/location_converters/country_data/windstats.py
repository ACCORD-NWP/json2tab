"""Converter to generate windfarm location file from WindStats data."""

import os
from typing import Optional

import pandas as pd

from ...io.readers import read_locationdata_as_dataframe
from ...io.writers import save_dataframe
from ...turbine_utils import datarow_to_turbine


def windstats(
    input_filename: str,
    output_filename: Optional[str] = None,
    sheet_name: Optional[str] = None,
    label_source: Optional[str] = None,
    rename_rules: Optional[str | dict] = None,
    write_rules: Optional[str | dict] = None,
    filter_rules: Optional[str | dict] = None,
) -> pd.DataFrame:
    """Converter to generate windfarm location file from WindStats data."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(f"WindStat Windfarm Converter ({input_filename} -> {output_filename})")

    data = read_locationdata_as_dataframe(
        input_filename=input_filename,
        rename_rules=rename_rules,
        write_rules=write_rules,
        filter_rules=filter_rules,
        sheet_name=sheet_name,
    )

    data.columns = data.columns.str.strip()

    if label_source is not None:
        data["source"] = label_source

    windfarms = []
    for _, row in data.iterrows():
        windfarm = datarow_to_turbine(row)
        windfarms.append(windfarm)

    data = pd.DataFrame(windfarms)
    save_dataframe(data, output_filename)
    return data
