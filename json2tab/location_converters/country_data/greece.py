"""Converter to generate wind turbine location files for Greece."""

import json
import os
from typing import Optional

import pandas as pd
from shapely.geometry import shape

from ...io.readers import read_locationdata_as_dataframe
from ...io.writers import save_dataframe
from ...location_converters.MergeStrategy import MergeStrategy
from ...location_converters.TurbineWindfarmMapper import TurbineWindfarmMapper
from ...logs import logger


def greece(
    input_windfarm_filename: str,
    input_windturbine_filename: str,
    output_filename: Optional[str] = None,
    label_source: Optional[str] = None,
) -> pd.DataFrame:
    """Converter to generate wind turbine location files for Greece."""
    if output_filename is None:
        input_filename_base = os.path.splitext(input_windturbine_filename)[0]
        output_filename = f"{input_filename_base}.csv"

    print(
        f"Greece csv Converter ({input_windfarm_filename} + {input_windturbine_filename} "
        f"-> {output_filename})"
    )

    if label_source is None:
        _, wf_file = os.path.split(input_windfarm_filename)
        _, wt_file = os.path.split(input_windturbine_filename)
        label_source = f"{wf_file}+{wt_file}"
    logger.info(
        f"Set source-field for {input_windfarm_filename}+{input_windturbine_filename} "
        f"to '{label_source}'"
    )

    # Transelate table to convert greece keys to english
    translate = {
        # "OBJECTID": "OBJECTID",
        # "id1": "id1",
        # "aa": "aa",
        "a_m": "windfarm_id",
        # "Κωδικός_Πάρκου": "Park_Code",
        # "Υπο_κωδικός": "Sub_Code",
        "Αριθμός_Α_Γ": "n_turbines",  # noqa: RUF001
        "Ισχύς_Πάρκου": "installed_capacity [MW]",
        # "Θέση_Εγκατάστασης": "Location",
        # "Δήμος___Κοινότητα": "Municipality___Community",
        # "Νομός": "Prefecture",
        "Project_Company": "windfarm",
        "Τύπος_Α_Γ": "turbine_type",  # noqa: RUF001
        "Year": "start_year",
        # "kathestos_enisxisis_mod": "boost_mode",
    }

    # Load windfarm data
    windfarms = []
    with open(input_windfarm_filename) as file:
        wf_data = json.load(file)

        for feature in wf_data["features"]:
            geometry = shape(feature["geometry"])
            props_gr = feature["properties"]

            props_en = {}
            for key, value in props_gr.items():
                key_en = translate.get(key)
                if key_en is not None:
                    props_en[key_en] = value

            props_en["source"] = "Greece windfarm data"
            props_en["country"] = "Greece"
            props_en["geometry"] = geometry
            windfarms.append(props_en)

    df_windfarms = pd.DataFrame(windfarms)
    total_turbines = (
        int(sum(df_windfarms["n_turbines"].fillna(0))) if len(df_windfarms) > 0 else 0
    )
    logger.info(
        f"Loaded {len(df_windfarms.index)} windfarms "
        f"with {total_turbines} turbines "
        f"from {input_windfarm_filename}"
    )

    # Load wind turbine data
    turbine_data = read_locationdata_as_dataframe(input_windturbine_filename)

    # Setup mapper to map turbines to windfarm
    mapper = TurbineWindfarmMapper()
    mapper.dump_temp_files = True
    base_output = os.path.splitext(output_filename)[0]
    mapper.merged_file = f"{base_output}.merged.csv"
    mapper.remaining_windfarm_file = f"{base_output}.remaining_windfarms.csv"
    mapper.remaining_turbine_file = f"{base_output}.remaining_turbines.csv"

    # Use windfarm data to enrich turbine data (but don't extend)
    df_merged = mapper.map_dataframes(
        "by_geometry",
        df_windfarms,
        turbine_data,
        source_label=label_source,
        merge_mode=MergeStrategy.EnrichSet2,
        max_distance=0.01,
    )

    # Save output
    save_dataframe(df_merged, output_filename)
    return df_merged
