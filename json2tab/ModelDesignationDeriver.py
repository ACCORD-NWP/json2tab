"""Module with enhanced model designation deriver."""

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

    def get_specs(self, model_designation: str):
        """Get turbine type specification by model designation.

        Args:
            model_designation (str): The model_designation to get turbine type specs from

        Returns:
            The turbine type specs or None
        """
        _, line = self.by_turbine_type(model_designation, fields=["model_designation"])
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
            fields = ["type_id", "type_code", "turbine_model", "model_designation"]

        if not sort_field:
            if fields != ["model_designation"]:
                sort_field = "model_designation"
            else:
                sort_field = "wind_speeds"

        links = []

        specs_df = self.turbine_type_manager.get_specs_dataframe(filtered=filtered)

        for field in fields:
            if field in specs_df.columns:
                # Get model_designation from specs df
                turbine_specs = specs_df[
                    specs_df[field].astype(str).str.lower() == str(turbine_type).lower()
                ]

                if len(turbine_specs) == 0 and field == "model_designation":
                    turbine_type_with_manufacturer_prefix = ensure_manufacturer_prefix(
                        turbine_type
                    )
                    turbine_specs = specs_df[
                        specs_df[field].astype(str).str.lower()
                        == str(turbine_type_with_manufacturer_prefix).lower()
                    ]

                if len(turbine_specs) > 0:
                    logger.debug(
                        f"Found {len(turbine_specs)} turbine specs with "
                        f"{field}={turbine_type}"
                    )
                    # Remove results with empty model_designation
                    turbine_specs_filtered = turbine_specs[
                        turbine_specs["model_designation"] != ""
                    ]

                    if len(turbine_specs_filtered) > 0:
                        # We have still results if we remove the forbidden values,
                        # so remove them
                        turbine_specs = turbine_specs_filtered
                        logger.debug(
                            f"Filtered results to {len(turbine_specs)} turbine specs "
                            f"with {field}={turbine_type} and a given model_designation."
                        )

                        if "is_manufacturer_data" in turbine_specs.columns:
                            turbine_specs_filtered = turbine_specs[
                                turbine_specs["is_manufacturer_data"] == True
                            ]
                            if len(turbine_specs_filtered) > 0:
                                # We have still results
                                # if we filter on only manufacturer data
                                turbine_specs = turbine_specs_filtered
                                logger.debug(
                                    f"Filtered results to {len(turbine_specs)} "
                                    f"turbine specs with {field}={turbine_type} "
                                    "and a given model_designation with ct/cp curves "
                                    "from manufacterer."
                                )

                        if sort_field in self.precomputed_length_fields:
                            turbine_specs = turbine_specs.sort_values(
                                by=self.precomputed_length_fields[sort_field],
                                ascending=False,
                            )
                        else:
                            turbine_specs = turbine_specs.sort_values(
                                by=sort_field,
                                key=lambda x: x.str.len(),
                                ascending=False,
                            )

                        model_designation = turbine_specs.iloc[0]["model_designation"]
                        matched_line_index = turbine_specs.index.tolist()[0]

                        if len(turbine_specs) > 1:
                            logger.debug(
                                f"Model_designation = {model_designation} on line "
                                f"{matched_line_index} is the richest result; "
                                f"i.e. value of {sort_field} is longest in length."
                            )

                        is_enriched_model_designation = False

                        if (
                            turbine_specs.iloc[0]["rated_power"] is None
                            or float(turbine_specs.iloc[0]["rated_power"]) == 0
                            or turbine_specs.iloc[0]["wind_speeds_length"] == 0
                        ):
                            # Try to enrich model_designation to get model_designation
                            # with rated power or with wind_speeds
                            (
                                model_designation_rich,
                                local_row_data_used,
                            ) = self.enrich_model_designation(
                                model_designation,
                                additional_data=row_data,
                                filtered=filtered,
                            )
                            if model_designation_rich != model_designation:
                                model_designation = model_designation_rich
                                is_enriched_model_designation = True
                                row_data_used |= local_row_data_used

                        if (
                            not (
                                field.lower() == "model_designation"
                                and sort_field.lower() == "wind_speeds"
                            )
                            or is_enriched_model_designation
                        ):
                            logger.debug(
                                f"Get richest wind_speeds dataset for "
                                f"model_designation = {model_designation}."
                            )
                            # Get the entry for this model_designation with the
                            # richest wind_speeds data
                            return self.by_turbine_type(
                                model_designation,
                                fields=["model_designation"],
                                sort_field="wind_speeds",
                                filtered=filtered,
                            )

                        return model_designation, matched_line_index, row_data_used

                    # This spec doesn't result in a model designation directly;
                    # store it for further investigation if no direct matches
                    # can be found
                    links.append(
                        {
                            "field": field,
                            "turbine_type": turbine_type,
                            "result": turbine_specs,
                        }
                    )

        if links:
            logger.debug(
                f"No direct match for a model designation found based on "
                f"'{turbine_type}' in {fields}, but found potenitial links"
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
                            ) = self.by_turbine_type(
                                new_turbine_type, fields=[field], filtered=filtered
                            )

                            if model_designation:
                                return model_designation, matched_line_index

        if not model_designation:
            logger.debug(
                f"Cannot find a valid model_designation from the specs table for "
                f"turbine_type='{turbine_type}' in fields {fields}, "
                "try to enrich turbine_type to model_designation with exact power match."
            )
            model_designation, local_row_data_used = self.enrich_model_designation(
                turbine_type,
                additional_data=row_data,
                exact_power_match=True,
                filtered=filtered,
            )

            # If enriching failed, try without an exact power match
            if model_designation == turbine_type:
                logger.debug(
                    f"Cannot find a valid model_designation from the specs table for "
                    f"turbine_type='{turbine_type}' in fields {fields}, try to enrich "
                    f"turbine_type to model_designation with non-exact power match."
                )
                model_designation, _ = self.enrich_model_designation(
                    turbine_type,
                    additional_data=row_data,
                    exact_power_match=False,
                    filtered=filtered,
                )
                local_row_data_used = True

            row_data_used |= local_row_data_used

            # If enriching still failed, no valid model_designation was found;
            # don't restart by_turbine_type with already failed
            # turbine_type
            if model_designation == turbine_type:
                model_designation = None

            if model_designation:
                (
                    model_designation,
                    matched_line_index,
                    _,
                ) = self.by_turbine_type(
                    model_designation,
                    fields=["model_designation"],
                    sort_field="wind_speeds",
                    filtered=filtered,
                )
                return model_designation, matched_line_index, row_data_used

            logger.debug(
                f"Cannot find a valid model_designation from the specs table for "
                f"turbine_type='{turbine_type}' in fields {fields}, stop using "
                f"turbine_type-based search on turbine_type={turbine_type}."
            )

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

        manufacturer = data["manufacturer"]
        diameter = get_diameter(data, None)
        power = get_rated_power_kw(data, None)
        row_data_used = False

        if not power:
            power = get_rated_power_kw(additional_data, None)
            row_data_used |= power is not None

        if not diameter:
            diameter = get_diameter(additional_data, None)
            row_data_used |= diameter is not None

        manufacturer_pattern = data.get("manufacturer_pattern", None)

        # Filtering will not result in anything, so enriching failed,
        # just return input model_designation
        if not manufacturer and not diameter and not power:
            logger.debug(
                f"Enriching failed due to missing filters; "
                f"return input model_designation={model_designation}."
            )
            return model_designation, row_data_used

        turbine_types = self.turbine_type_manager.get_specs_dataframe(filtered)

        # Remove all FO_00000 types, so enriching cannot introduce wf101-types
        turbine_types = turbine_types[~(turbine_types["model_designation"].str.match(r"FO_\d+", na=False))]

        filter_string = ""
        if manufacturer_pattern:
            turbine_types = turbine_types[
                turbine_types["manufacturer"].str.match(
                    manufacturer_pattern, case=False, na=False
                )
            ]
            filter_string = (
                filter_string + f"manufacturer should match = {manufacturer_pattern}, "
            )
        elif manufacturer:
            turbine_types = turbine_types[
                turbine_types["manufacturer"].str.lower() == str(manufacturer).lower()
            ]
            filter_string = filter_string + f"manufacturer = {manufacturer}, "

        if diameter:
            # Match on the approximate integer-values of the diameter
            turbine_types = turbine_types[
                abs(turbine_types["diameter"].astype(float) - float(diameter)) < 5
            ]
            filter_string = filter_string + f"diameter = {diameter} +/- 5, "

        if power and power > 0 and exact_power_match:
            thresshold = (float(power) / 750) / 100
            turbine_types = turbine_types[
                abs(turbine_types["rated_power"].astype(float) - float(power))
                / float(power)
                < thresshold
            ]
            filter_string = (
                filter_string + f"power = {power} +/- {int(thresshold * 100)}%, "
            )

        if len(turbine_types) > 1:
            turbine_types_positive_power = turbine_types[
                turbine_types["rated_power"].astype(float) > 0
            ]
            if len(turbine_types_positive_power) > 0:
                turbine_types = turbine_types_positive_power
                filter_string = filter_string + "power > 0, "

        if len(turbine_types) > 1:
            turbine_types_with_ws = turbine_types[turbine_types["wind_speeds_length"] > 0]
            if len(turbine_types_with_ws) > 0:
                turbine_types = turbine_types_with_ws
                filter_string = filter_string + "wind_speeds_length > 0, "

        if len(turbine_types) > 1 and diameter:
            stricter_filter = None
            for thresshold in [3, 1]:
                # Match on the integer-values of the diameter
                turbine_types_prep = turbine_types[
                    abs(turbine_types["diameter"].astype(float) - float(diameter)) < thresshold
                ]

                if len(turbine_types_prep) > 0:
                    turbine_types = turbine_types_prep
                    stricter_filter = thresshold
            
            if stricter_filter is not None:
                filter_string += f"diameter = {diameter} +/- {stricter_filter}, "
        

        if len(turbine_types) > 1 and power and power > 0 and exact_power_match:
            thresshold = (float(power) / 750) / 100
            while len(turbine_types) > 1 and int(thresshold * 100) > 0:
                thresshold /= 2
                turbine_types_prep = turbine_types[
                    abs(turbine_types["rated_power"].astype(float) - float(power))
                    / float(power)
                    < thresshold
                ]

                if len(turbine_types_prep) > 0:
                    turbine_types = turbine_types_prep
                    thresshold /= 2
                    logger.debug(f"Set stronger thresshold={thresshold} for power delta")
                else:
                    break

            filter_string = (
                filter_string + f"power = {power} +/- {int(thresshold * 100)}%, "
            )

        if len(turbine_types) > 0 and power and not exact_power_match:
            logger.debug(
                f"Derterime possible model_designation based on "
                f"{len(turbine_types)} turbine types with filters on "
                f"{filter_string[:-2]}, power closest to {power}."
            )

            # Add column power_delta;
            # note this might raise an false positive SettingWithCopyWarning
            turbine_types["power_delta"] = turbine_types["rated_power"].map(
                lambda x: float(x) - float(power)
            )
            turbine_types = turbine_types.sort_values(by="power_delta", key=abs)
            model_designation_enriched = turbine_types.iloc[0]["model_designation"]
            logger.debug(
                f"Approximated model_designation='{model_designation}' "
                f"by '{model_designation_enriched}'"
            )
        elif len(turbine_types) == 1:
            logger.debug(
                f"Found possible model_designation with filters on {filter_string[:-2]}."
            )
            model_designation_enriched = turbine_types.iloc[0]["model_designation"]
            logger.debug(
                f"Enriched model_designation='{model_designation}' "
                f"to '{model_designation_enriched}'"
            )

        elif len(turbine_types) > 1:
            logger.debug(
                f"Derterime possible model_designation based on {len(turbine_types)} "
                f"turbines with filters on {filter_string[:-2]}."
            )

            # Get most frequent listed model_designation
            modes = turbine_types["model_designation"].mode()

            if len(modes) > 1:
                additional_data_dict = additional_data
                if not isinstance(additional_data_dict, dict):
                    additional_data_dict = additional_data_dict.to_dict()
                    
                logger.debug(
                    f"Found {len(modes)} possible model_designations; "
                    f"all are most frequent in database based on parameters "
                    f"given in {data} and {additional_data_dict}."
                )

            if len(modes) > 0:
                model_designation_enriched = modes.iloc[0]
            else:
                logger.debug(
                    f"Found {len(modes)} possible mode model_designations for "
                    f"{len(turbine_types['model_designation'])} found tubines."
                )
                logger.info(
                    f"Cannot determine model_designation and return input "
                    f"model_designation={model_designation}."
                )
                model_designation_enriched = model_designation

            logger.debug(
                f"Enriched model_designation='{model_designation}' "
                f"to '{model_designation_enriched}'"
            )
        else:
            logger.debug(
                f"Enriching failed due to too strict filters: "
                f"{filter_string[:-2]}; "
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
