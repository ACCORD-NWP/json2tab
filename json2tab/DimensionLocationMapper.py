"""Selector for default wind turbine type based on diameter, power and country/region."""
import re
from datetime import datetime
from typing import Any, Dict, Tuple

from .logs import logger
from .utils import get_diameter, get_height, get_rated_power_kw


class DimensionLocationMapper:
    def __init__(self):
        """Initialize dimension location based mapper."""

    def build_dimension_matches(self, diameter: float):
        dimension_matches = []

        # --- Common Vestas turbines ---
        if 88 <= diameter <= 92:  # V90
            dimension_matches.append(("V90", 10, "90m diameter (V90)"))
        elif 98 <= diameter <= 102:  # V100
            dimension_matches.append(("V100", 10, "100m diameter (V100)"))
        elif 110 <= diameter <= 114:  # V112
            dimension_matches.append(("V112", 10, "112m diameter (V112)"))
        elif 116 <= diameter <= 120:  # V117
            dimension_matches.append(("V117", 10, "117-120m diameter (V117)"))
        elif 124 <= diameter <= 128:  # V126
            dimension_matches.append(("V126", 10, "126m diameter (V126)"))
        elif 160 <= diameter <= 168:  # V164
            dimension_matches.append(("V164", 10, "164m diameter (V164)"))

        # --- Common Enercon turbines ---
        if 81 <= diameter <= 83:  # E82
            dimension_matches.append(("E82", 10, "82m diameter (E82)"))
        elif 99 <= diameter <= 103:  # E101
            dimension_matches.append(("E101", 10, "101m diameter (E101)"))
        elif 114 <= diameter <= 118:  # E115
            dimension_matches.append(("E115", 10, "115m diameter (E115)"))
        elif 125 <= diameter <= 130:  # E126
            dimension_matches.append(("E126", 10, "126-130m diameter (E126)"))
        elif 135 <= diameter <= 142:  # E138
            dimension_matches.append(("E138", 10, "138m diameter (E138)"))

        # --- Common Siemens/Siemens-Gamesa turbines ---
        if 106 <= diameter <= 110:  # SWT-3.6-107
            dimension_matches.append(("SWT-107", 10, "107m diameter (SWT-3.6-107)"))
        elif 119 <= diameter <= 123:  # SWT-3.6-120
            dimension_matches.append(("SWT-120", 10, "120m diameter (SWT-3.6-120)"))
        elif 153 <= diameter <= 157:  # SWT-6.0-154
            dimension_matches.append(("SWT-154", 10, "154m diameter (SWT-6.0-154)"))

        # --- Common Nordex turbines ---
        if 130 <= diameter <= 134:  # N131
            dimension_matches.append(("N131", 10, "131m diameter (N131)"))

        return dimension_matches

    def map(self, turbine_props: Dict[str, Any]) -> Tuple[str, str]:
        """Find closest matching type with enhanced criteria and location considerations."""
        is_offshore = turbine_props.get("is_offshore", None)

        try:
            diameter = get_diameter(turbine_props, 0)
            height = get_height(turbine_props, 0)
            power = get_rated_power_kw(turbine_props, 0)

            # Handle year if available (for historical context)
            year = 0
            for key in ["start_date", "year", "installation_year", "commission_date"]:
                if turbine_props.get(key) not in [None, "", "NaN"]:
                    try:
                        year_val = turbine_props.get(key)
                        # Handle date strings
                        if isinstance(year_val, str) and len(year_val) > 4:
                            # Try to extract year from date string
                            year_match = re.search(r"(\d{4})", year_val)
                            if year_match:
                                year = int(year_match.group(1))
                        elif isinstance(year_val, datetime):
                            year = year_val.year
                        else:
                            year = int(year_val)
                        break
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.warning(f"Error extracting properties: {e}")
            logger.debug(f"Raw properties: {turbine_props}")
            diameter = height = power = year = 0

        # Get country for region-specific matching
        country = None
        for key in ["country", "country_code"]:
            if turbine_props.get(key) not in [None, "", "NaN"]:
                country = turbine_props.get(key)
                break

        # Start with dimension-based and location-based matching
        # Enhanced dimension-based matching for specific turbine models
        dimension_matches = self.build_dimension_matches(diameter)

        # --- Adjust confidence based on additional factors ---

        # If we have height data, refine confidence
        if height > 0:
            for i, (model, confidence, reason) in enumerate(dimension_matches):
                # Expected heights for various models
                expected_height = {
                    "V90": 80.0,
                    "V100": 95.0,
                    "V112": 94.0,
                    "V117": 91.5,
                    "V126": 116.5,
                    "V164": 106.0,
                    "E82": 78.0,
                    "E101": 99.0,
                    "E115": 122.0,
                    "E126": 135.0,
                    "E138": 131.0,
                    "SWT-107": 90.0,
                    "SWT-120": 90.0,
                    "SWT-154": 110.0,
                    "N131": 114.0,
                }

                if model in expected_height:
                    confidence_delta, match = self.confidence_height(
                        height,
                        expected_height[model],
                        model=model,
                        confidence=confidence,
                        reason=reason,
                    )
                    if confidence_delta is not None:
                        dimension_matches[i] = match

        # If we have power data, refine confidence
        if power > 0:
            for i, (model, confidence, reason) in enumerate(dimension_matches):
                # Expected power for various models
                expected_power = {
                    "V90": 3.0,
                    "V100": 2.6,
                    "V112": 3.45,
                    "V117": 4.2,
                    "V126": 3.45,
                    "V164": 8.0,
                    "E82": 2.0,
                    "E101": 3.05,
                    "E115": 3.2,
                    "E126": 4.2,
                    "E138": 4.2,
                    "SWT-107": 3.6,
                    "SWT-120": 3.6,
                    "SWT-154": 6.0,
                    "N131": 3.6,
                }

                powerMW = power / 1000
                if model in expected_power:
                    confidence_delta, match = self.confidence_power(
                        powerMW,
                        expected_power[model],
                        model=model,
                        confidence=confidence,
                        reason=reason,
                    )
                    if confidence_delta is not None:
                        dimension_matches[i] = match

        # Offshore-specific adjustments
        if is_offshore:
            # Vestas V164 and SWT-154 are common offshore models
            for i, (model, confidence, reason) in enumerate(dimension_matches):
                if model in ["V164", "SWT-154"]:
                    dimension_matches[i] = (
                        model,
                        confidence + 5,
                        reason + ", offshore location match",
                    )
                elif model in ["E101", "E82"]:  # Uncommon offshore
                    dimension_matches[i] = (
                        model,
                        confidence - 2,
                        reason + ", uncommon offshore",
                    )
        else:
            # Onshore-specific adjustments
            for i, (model, confidence, reason) in enumerate(dimension_matches):
                if model in ["V164", "SWT-154"]:  # Uncommon onshore
                    dimension_matches[i] = (
                        model,
                        confidence - 3,
                        reason + ", uncommon onshore",
                    )

        # Country/region-specific adjustments
        if country:
            country = country.upper()
            for i, (model, confidence, reason) in enumerate(dimension_matches):
                if country in ["DE", "DEU", "GERMANY"] and model.startswith(
                    "E"
                ):  # Enercon common in Germany
                    dimension_matches[i] = (
                        model,
                        confidence + 2,
                        reason + f", common in {country}",
                    )
                elif country in ["DK", "DNK", "DENMARK"] and model.startswith(
                    "V"
                ):  # Vestas common in Denmark
                    dimension_matches[i] = (
                        model,
                        confidence + 2,
                        reason + f", common in {country}",
                    )

        # If we have high-confidence dimension matches, use the best one
        if dimension_matches:
            # Sort by confidence (descending)
            dimension_matches.sort(key=lambda x: x[1], reverse=True)
            best_match, confidence, reason = dimension_matches[0]

            # If confidence is high enough, use the dimension-based match
            if confidence >= 8:
                logger.debug(
                    f"Using dimension-based match: {best_match}"
                    f"(confidence: {confidence}, {reason})"
                )
            else:
                best_match = None
        else:
            best_match = None

        return best_match

    def confidence_height(
        self, height, expected_height, model=None, confidence: int = 0, reason: str = ""
    ):
        height_diff = abs(height - expected_height)
        if height_diff < 5:  # Very close match
            confidence_delta = 5
            match = (
                model,
                confidence + 5,
                reason + f", height match ({height}m vs {expected_height}m)",
            )
        elif height_diff < 15:  # Reasonable match
            confidence_delta = 2
            match = (
                model,
                confidence + 2,
                reason + f", close height ({height}m vs {expected_height}m)",
            )
        elif height_diff > 30:  # Poor height match
            confidence_delta = -3
            match = (
                model,
                confidence - 3,
                reason + f", height mismatch ({height}m vs {expected_height}m)",
            )
        else:
            confidence_delta = None
            match = None

        return confidence_delta, match

    def confidence_power(
        self, powerMW, expected_powerMW, model=None, confidence: int = 0, reason: str = ""
    ):
        power_diff = abs(powerMW - expected_powerMW)
        if power_diff < 0.3:  # Very close match
            confidence_delta = 5
            match = (
                model,
                confidence + 5,
                reason + f", power match ({powerMW}MW vs {expected_powerMW}MW)",
            )
        elif power_diff < 0.8:  # Reasonable match
            confidence_delta = 2
            match = (
                model,
                confidence + 2,
                reason + f", close power ({powerMW}MW vs {expected_powerMW}MW)",
            )
        elif power_diff > 2.0:  # Poor power match
            confidence_delta = -3
            match = (
                model,
                confidence - 3,
                reason + f", power mismatch ({powerMW}MW vs {expected_powerMW}MW)",
            )
        else:
            confidence_delta = None
            match = None

        return confidence_delta, match

    def confidence_diameter(self, diameter, expected_diameter):
        diameter_diff = abs(diameter - expected_diameter)
        if diameter_diff < 1:  # Very close match
            confidence_delta = 10
        elif diameter_diff < 4:  # Reasonable match
            confidence_delta = 5
        elif diameter_diff < 10:  # Poor power match
            confidence_delta = 2
        elif diameter_diff > 15:  # Verry poor power match
            confidence_delta = -3
        else:
            confidence_delta = None

        return confidence_delta, None
