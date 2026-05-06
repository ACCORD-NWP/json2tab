"""Module with enhanced model designation deriver."""

import re
from typing import Optional, Tuple

from .logs import logger
from .ModelNameBuilder import ensure_manufacturer_prefix
from .ModelNameParser import parse_model_name
from .TurbineTypeManager import TurbineTypeManager
from .utils import get_diameter, get_rated_power_kw


class ModelDesignationDeriver:
    """Enhanced model designation deriver."""

    def __init__(self, turbine_type_manager: TurbineTypeManager):
        """Initialize model designation deriver.

        Args:
            turbine_type_manager: The TurbineTypeManager with known turbine types
        """
        self.turbine_type_manager = turbine_type_manager

        self.precomputed_length_fields = {
            "model_designation": "model_designation_length",
            "wind_speeds": "wind_speeds_length",
        }

    def get_specs(self, model_designation: str, row_data: Optional[dict] = None):
        """Get turbine type specification by model designation.

        Args:
            model_designation (str): The model_designation to get turbine type specs from
            row_data (dict): Optional location specific properties for turbine type

        Returns:
            The turbine type specs or None
        """
        _, line, _ = self.by_turbine_type(
            model_designation, fields=["model_designation"], row_data=row_data
        )
        if line is not None:
            return self.turbine_type_manager.get_specs_by_line_index(line)

        return None

    def by_turbine_type(
        self,
        turbine_type: str,
        fields=None,
        sort_field=None,
        row_data: Optional[dict] = None,
        filtered: bool = False,
    ) -> Tuple[str, int, bool]:
        """Get model designation by turbine_type.

        Args:
            turbine_type (str): Input string as turbine type to find model designation
            fields (list):      (Optional) List of fields to check as turbine_type
            sort_field:         (Optional) Field on which results should be sorted
            row_data:           (Optional) Location specific properties for turbine type
            filtered:           (Optional) Flag specifying the use of filtered type specs

        Returns:
            model_designation:  The model_designation of the matched tubine type
            matched_line_index: The line index of the match in the turbine_type_manager
            row_data_used:      Flag indicating if row-data from turbine is used
        """
        model_designation = None
        matched_line_index = None
        row_data_used = False

        if fields is None:
            fields = ["model_designation", "type_id", "type_code"]

        input_sort_field = sort_field

        links = []

        specs_df = self.turbine_type_manager.get_specs_dataframe(filtered=filtered)

        # Remove all FO_00000 types, so model designation cannot introduce wf101-types
        specs_df = specs_df[
            ~(specs_df["model_designation"].str.match(r"FO_\d+", na=False))
        ]

        for field in fields:
            if field in specs_df.columns:
                sort_field = input_sort_field
                if not sort_field:
                    sort_field = (
                        "model_designation"
                        if field != "model_designation"
                        else "wind_speeds"
                    )

                # logger.debug(f"Search for {field} = {turbine_type}, sort: {sort_field}")

                # Get model_designation from specs df
                specs = specs_df[
                    specs_df[field].astype(str).str.lower() == str(turbine_type).lower()
                ]

                # Allow on-the-fly generation of manufacturer prefix for model_designation
                if len(specs) == 0 and field == "model_designation":
                    type_with_prefix = ensure_manufacturer_prefix(turbine_type)
                    specs = specs_df[
                        specs_df[field].astype(str).str.lower()
                        == str(type_with_prefix).lower()
                    ]

                if len(specs) > 0:
                    # Remove results with empty model_designation
                    specs_filtered = specs[
                        (specs["model_designation"] != "")
                        & ~(specs["model_designation"].isna())
                    ]
                    if len(specs_filtered) > 0:
                        specs = specs_filtered
                        msg = (
                            f"Found {len(specs)} type specifications "
                            f"with {field}={turbine_type} "
                            "and a given model_designation."
                        )

                        # Filter on only manufacturer data, when possible
                        if "is_manufacturer_data" in specs.columns:
                            specs_filtered = specs[specs["is_manufacturer_data"] == True]
                            if len(specs_filtered) > 0:
                                specs = specs_filtered
                                msg = (
                                    f"Found {len(specs)} type specifications "
                                    f"with {field}={turbine_type}, a given "
                                    "model_designation, and manufacturer provided data."
                                )

                        logger.debug(msg)

                        if len(specs) > 1:
                            # Sort specs
                            if sort_field in self.precomputed_length_fields:
                                specs = specs.sort_values(
                                    by=self.precomputed_length_fields[sort_field],
                                    ascending=False,
                                )
                            else:
                                specs = specs.sort_values(
                                    by=sort_field,
                                    key=lambda x: x.str.len(),
                                    ascending=False,
                                )

                        # Select first resulting model designation
                        model_designation = specs.iloc[0]["model_designation"]
                        matched_line_index = specs.index.tolist()[0]

                        if len(specs) > 1:
                            logger.debug(
                                f"Model_designation = '{model_designation}' on line "
                                f"{matched_line_index} is the richest TOP-1 result; "
                                f"i.e. value of {sort_field} is longest in length."
                            )

                        if (
                            specs.iloc[0]["wind_speeds_length"] == 0  # Type aliasses
                            or specs.iloc[0]["rated_power"] is None  # FO_*-types
                            or re.match(r"FO_\d+", model_designation)  # FO_*-types
                            or re.match(r"FO_\d+", turbine_type)  # FO_*-types
                        ):
                            if not (
                                turbine_type == model_designation
                                and field == "model_designation"
                            ):
                                # Follow link
                                return self.by_turbine_type(
                                    model_designation,
                                    fields=["model_designation"],
                                    row_data=row_data,
                                )

                            # No match found
                            return None, -1, False

                        return model_designation, matched_line_index, row_data_used

                    logger.debug(
                        f"Found {len(specs)} specs with {field}={turbine_type} "
                        "but non with a given model_designation."
                    )

                    # This spec doesn't result in a model designation directly;
                    # store for further investigation if no direct matches can be found
                    if len(specs) > 1:
                        link = {
                            "field": field,
                            "turbine_type": turbine_type,
                            "result": specs,
                        }
                        logger.debug(f"Added link; {link}")
                        links.append(link)

        if links:
            logger.debug(
                f"No direct match for a model designation found based on "
                f"'{turbine_type}' in {fields}, but found {len(links)} potenitial links."
            )

        for link in links:
            for _, spec in link["result"].iterrows():
                for field in fields:
                    if field != link["field"]:
                        new_turbine_type = spec[field]
                        logger.debug(
                            f"Following link from {turbine_type} via "
                            f"{field} = {new_turbine_type}"
                        )
                        if new_turbine_type:
                            (
                                model_designation,
                                matched_line_index,
                                row_data_used,
                            ) = self.by_turbine_type(
                                new_turbine_type,
                                fields=[field],
                                filtered=filtered,
                                row_data=row_data,
                            )

                            if model_designation:
                                return (
                                    model_designation,
                                    matched_line_index,
                                    row_data_used,
                                )

        # if not model_designation:
        #     logger.debug(
        #         f"Cannot find a valid model_designation from the specs table for "
        #         f"turbine_type='{turbine_type}' in fields {fields}, "
        #         "try to enrich turbine_type to model_designation with exact pwr match."
        #     )
        #     model_designation, local_row_data_used = self.enrich_model_designation(
        #         turbine_type,
        #         additional_data=row_data,
        #         exact_power_match=True,
        #         filtered=filtered,
        #     )

        #     # If enriching failed, try without an exact power match
        #     if model_designation == turbine_type:
        #         logger.debug(
        #             f"Cannot find a valid model_designation from the specs table for "
        #             f"turbine_type='{turbine_type}' in fields {fields}, try to enrich "
        #             f"turbine_type to model_designation with non-exact power match."
        #         )
        #         model_designation, _ = self.enrich_model_designation(
        #             turbine_type,
        #             additional_data=row_data,
        #             exact_power_match=False,
        #             filtered=filtered,
        #         )
        #         local_row_data_used = True

        #     row_data_used |= local_row_data_used

        #     # If enriching still failed, no valid model_designation was found;
        #     # don't restart by_turbine_type with already failed
        #     # turbine_type
        #     if model_designation == turbine_type:
        #         model_designation = None

        #     if model_designation:
        #         (
        #             model_designation,
        #             matched_line_index,
        #             _,
        #         ) = self.by_turbine_type(
        #             model_designation,
        #             fields=["model_designation"],
        #             sort_field="wind_speeds",
        #             filtered=filtered,
        #         )
        #         return model_designation, matched_line_index, row_data_used

        #     logger.debug(
        #         f"Cannot find a valid model_designation from the specs table for "
        #         f"turbine_type='{turbine_type}' in fields {fields}, stop using "
        #         f"turbine_type-based search on turbine_type={turbine_type}."
        #     )

        return model_designation, matched_line_index, row_data_used

    def enrich_model_designation(
        self,
        model_designation: str,
        additional_data: Optional[dict] = None,
        exact_power_match: bool = True,
        filtered: bool = True,
    ):
        """Enrich a general model designation to a more specific model designation."""
        if additional_data is None:
            additional_data = {}
        data = parse_model_name(model_designation)

        if not data["is_matched"]:
            # Parsing input model_designation as model name failed; don't continue
            return model_designation, False

        manufacturer = data["manufacturer"]
        diameter = get_diameter(data)
        power = get_rated_power_kw(data, guess_unit=False)
        row_data_used = False

        if not power:
            power = get_rated_power_kw(additional_data, None, guess_unit=False)
            row_data_used |= power is not None

        if not diameter:
            diameter = get_diameter(additional_data, None)
            row_data_used |= diameter is not None

        manufacturer_pattern = data.get("manufacturer_pattern", None)

        # Filtering will not result in anything, so enriching failed,
        # just return input model_designation
        if not manufacturer and not diameter and not power:
            logger.debug(
                f"Enriching failed due to lack of filters; "
                f"return input model_designation={model_designation}."
            )
            return model_designation, row_data_used

        turbine_types = self.turbine_type_manager.get_specs_dataframe(filtered)

        # Remove all FO_00000 types, so enriching cannot introduce wf101-types
        turbine_types = turbine_types[
            ~(turbine_types["model_designation"].str.match(r"FO_\d+", na=False))
        ]

        filter_str = ""
        if manufacturer_pattern:
            turbine_types = turbine_types[
                turbine_types["manufacturer"].str.match(
                    manufacturer_pattern, case=False, na=False
                )
            ]
            filter_str += f"manufacturer should match {manufacturer_pattern}, "

        elif manufacturer:
            turbine_types = turbine_types[
                turbine_types["manufacturer"].str.lower() == str(manufacturer).lower()
            ]
            filter_str += f"manufacturer = {manufacturer}, "

        if diameter:
            # Match on the approximate integer-values of the diameter
            turbine_types = turbine_types[
                abs(turbine_types["diameter"].astype(float) - float(diameter)) < 5
            ]
            filter_str += f"diameter = {diameter} +/- 5, "

        if power and power > 0 and exact_power_match:
            thresshold = (float(power) / 750) / 100
            if int(thresshold * 100) > 0:
                turbine_types = turbine_types[
                    abs(turbine_types["rated_power"].astype(float) - float(power))
                    / float(power)
                    < thresshold
                ]
                filter_str += f"power = {power} +/- {int(thresshold * 100)}%, "
            else:
                turbine_types = turbine_types[
                    abs(turbine_types["rated_power"].astype(float) - float(power)) < 1
                ]
                filter_str += f"power = {power} +/- 1, "

        if len(turbine_types) > 1:
            filtered = turbine_types[turbine_types["rated_power"].astype(float) > 0]
            if len(filtered) > 0:
                turbine_types = filtered
                filter_str += "power > 0, "

        if len(turbine_types) > 1:
            filtered = turbine_types[turbine_types["wind_speeds_length"] > 0]
            if len(filtered) > 0:
                turbine_types = filtered
                filter_str += "wind_speeds_length > 0, "

        if len(turbine_types) > 1 and diameter:
            stricter_filter = None
            for thresshold in [3, 1]:
                # Match on the integer-values of the diameter
                filtered = turbine_types[
                    abs(turbine_types["diameter"].astype(float) - float(diameter))
                    < thresshold
                ]

                if len(filtered) > 0:
                    turbine_types = filtered
                    stricter_filter = thresshold

            if stricter_filter is not None:
                filter_str += f"diameter = {diameter} +/- {stricter_filter}, "

        if len(turbine_types) > 1 and power and power > 0 and exact_power_match:
            thresshold = (float(power) / 750) / 100
            while len(turbine_types) > 1 and int(thresshold * 100) > 0:
                filtered = turbine_types[
                    abs(turbine_types["rated_power"].astype(float) - float(power))
                    / float(power)
                    < thresshold
                ]

                if len(filtered) > 0:
                    turbine_types = filtered
                    thresshold /= 2
                else:
                    break

            filter_str += f"power = {power} +/- {int(thresshold * 100)}%, "

        if len(turbine_types) > 1 and manufacturer is not None:
            filtered = turbine_types[
                turbine_types["manufacturer"].str.match(
                    manufacturer, case=False, na=False
                )
            ]
            if len(filtered) > 0:
                turbine_types = filtered
                filter_str += f"manufacturer = {manufacturer}, "

        # Strip off final ', ' part of filter_str
        if len(filter_str) > 2:
            filter_str = filter_str[:-2]

        if len(turbine_types) == 1:
            model_designation_enriched = turbine_types.iloc[0]["model_designation"]

            logger.debug(
                f"Enriched model_designation='{model_designation}' "
                f"to '{model_designation_enriched}' where {filter_str}."
            )
        elif len(turbine_types) > 1:
            if power and not exact_power_match:
                # This might raise a false positive SettingWithCopyWarning
                turbine_types["power_delta"] = turbine_types["rated_power"].map(
                    lambda x: float(x) - float(power)
                )
                turbine_types = turbine_types.sort_values(by="power_delta", key=abs)
                model_designation_enriched = turbine_types.iloc[0]["model_designation"]
                logger.debug(
                    f"Approximated model_designation='{model_designation}' "
                    f"by '{model_designation_enriched}' based on "
                    f"{len(turbine_types)} turbine types with where "
                    f"{filter_str}, power closest to {power}."
                )
            else:
                # Get most frequent listed model_designation
                modes = turbine_types["model_designation"].mode()

                if len(modes) > 0:
                    model_designation_enriched = modes.iloc[0]
                    logger.debug(
                        f"Enriched model_designation='{model_designation}' to "
                        f"'{model_designation_enriched}' based on {len(modes)} modal "
                        f"turbine types where {filter_str}."
                    )
                else:
                    logger.error("WHY ARE WE HERE?? (from enrich_model_designation)")
                    model_designation_enriched = model_designation
                    logger.debug(
                        f"Cannot determine model_designation and return input "
                        f"model_designation={model_designation}."
                    )

        else:
            logger.debug(
                f"Enriching failed due to too strict filters: "
                f"{filter_str}; "
                f"return input model_designation={model_designation}."
            )
            model_designation_enriched = model_designation

        return model_designation_enriched, row_data_used

    def get_closest_powered_windturbine_with_ct(self, model_designation: str):
        """Get a model designation close to the given one that has ct-data."""
        model_designation, _ = self.enrich_model_designation(
            model_designation, exact_power_match=False, filtered=False
        )
        return model_designation
