"""Module to parse model_designation from windturbine model name.

Further, if available, manufacturer, rated_power and diameter are parsed.
"""

import contextlib
import math
import re

from .get_wf101_manufacturer import get_wf101_manufacturer
from .ModelNameBuilder import ensure_manufacturer_prefix
from .utils import power_to_kw


def parse_model_name(model_name: str) -> dict:
    """Parses a turbine model name to retrieve possible model_designation.

    Fruther - if possible - manufacturer, diameter, and power are retrieved.

    Args:
        model_name (str): Full turbine model name (e.g., "VESTAS V90 3.0MW")

    Returns:
        dict: A dictionary with - if possible -
                *) model_designation,
                *) manufacturer,
                *) diameter,
                *) power
    """
    # Remove all multiple spaces from model name
    model_name = re.sub(r"\s\s+", " ", str(model_name))

    # Ensure model name starts with manufacturer-name
    model_name = ensure_manufacturer_prefix(model_name)

    match = re.search(r"(?P<manufacturer>\w+), ", model_name)
    if match:
        # It looks like manufacturer and type are separated with a comma
        # so remove the first comma that separates manufacturer and type
        model_name = model_name.replace(", ", " ", 1)

    # Replace all commas by dots
    model_name = model_name.replace(",", ".")

    # Look for turbine model patterns within the name
    patterns = [
        # Common naming patterns for major manufacturers
        # Vestas pattern (e.g., V90, V112)
        r"(?P<manufacturer>(Vestas Onshore)|Vestas|(MHI Vestas Offshore)|(MHI Vestas)|MVOW)(\s|-)V(-|\s)?(?P<diameter>\d{2,3})(\s*-\s*(?P<power>\d+(\.\d+)?))?",
        # Enercon pattern (e.g., E40, E82, E101)
        r"(?P<manufacturer>Enercon)(-|\s)(E(-|\s)?)?(?P<diameter>\d{2,3})( EP\d)?( E\d)?( (?P<power>\d+(\.\d+)?))?(\s?/\s?(?P<powerOW>\d+)\.?(?P<diameter2>\d+)?)?",
        # Match AN Bonus  (eg AN Bonus  450/36), Bonus (eg Bonus 37/450, Bonus B39/500  | and Bonus (Bonus-76-2.0) and Gamesa G49-2.0 before Siemens-Gamesa
        r"(?P<manufacturer>AN((-|\s)Bonus)?) (AN\s?)?(?P<powerKW>\d+(\.\d+)?)(/(?P<diameter>\d+))?",
        r"(?P<manufacturer>Bonus|Combi) (?P<diameter>\d+)/(?P<powerKW>\d+(\.\d+)?)",
        r"(?P<manufacturer>Gamesa|Bonus)(\s|-)(G|B)?(-|\s)?(?P<diameter>\d+)([-|/](?P<power>\d+(\.\d+)?))?(\s?(?P<known_unit>(kW)|(MW)))?",
        # Siemens / Gamesa / Siemens-Gamesa pattern (e.g., SWT-3.6-120)
        r"(?P<manufacturer>(Siemens(\s|-)Gamesa)|Siemens|Gamesa|(AN(-|\s))?Bonus|SWT)\s?(SWT|SG|G)?((-|\s)?(DD-(?P<power>\d+(\.\d+)?)))-(?P<diameter>\d+)",
        r"(?P<manufacturer>(Siemens(\s|-)Gamesa)|Siemens|Gamesa|(AN(-|\s))?Bonus|SWT)\s?(SWT|SG|G)?((-|\s)?(DD|(D?(?P<power>\d+(\.\d+)?))))?-(?P<diameter>\d+)?",
        r"(?P<manufacturer>(Siemens(\s|-)Gamesa)|Siemens|Gamesa|(AN(-|\s))?Bonus|SWT) SG-(?P<diameter>\d+)",
        # Senvion, REpower pattern
        r"(?P<manufacturer>Kenersys) K\s?(?P<diameter>\d+)\s(?P<powerMW>\d+(\.\d+)?)MW",
        r"(?P<manufacturer>Senvion|REpower|(Jacobs PowerTec JPT)|(Jacobs Wind Electric)|Jacobs|(HSW Husumer Schiffs)|Kenersys)(\s|-|\.)\s?(M|HSW)?\s?(?P<power>\d+(\.(\d+|X))?)?((M|D|/|\s|-)\s?(?P<diameter>\d+))?((/|\s)(?P<power2>\d+(\.\d+)?))?",
        # Haliade turbines  (eg Haliade-6)
        r"(?P<manufacturer>Haliade)(\s|-)(?P<power>\d+(\.\d)?)",
        # Mitsubishi turbines; eg Mitsubishi  MWT-250
        r"(?P<manufacturer>Mitsubishi) MWT-(?P<diameter>\d+)/(?P<power>\d+(\.\d)?)",
        r"(?P<manufacturer>Mitsubishi) MWT-S?(?P<powerkW>\d+(\.\d)?)(-(?P<diameter>\d+))?",
        # Adwen turbines; eg Adwen AD 5-135
        r"(?P<manufacturer>Adwen) AD (?P<powerMW>\d+(\.\d)?)-(?P<diameter>\d+)",
        # IZAR TURBINAS turbines; eg IZAR TURBINAS  Bonus 44/600
        r"(?P<manufacturer>(Izar Turbinas)|Izar) Bonus (?P<diameter>\d+)(-|/)(?P<power>\d+(\.\d)?)",
        # Made - Endesa  AE-61/1.100 turbines; eg Made - Endesa  AE-61/1.100
        r"(?P<manufacturer>(Made\s?-\s?Endesa)|Made|Endesa) (AE|M)(-|\s)(?P<diameter>\d+)((-|/)(?P<power>\d+(\.\d)?))?",
        # Suzlon turbines; eg Suzlon  S 60-1000, Suzlon 88 - 2.1 MW
        r"(?P<manufacturer>Suzlon) (S(\s|-)?)?(?P<diameter>\d+)(((\s?(-|/)\s?)|\s)(?P<power>\d+(\.\d)?))?",
        # Reference turbines  (eg REF-6.0, REF-8.0)
        r"(?P<manufacturer>REF)(\s|-)(?P<powerMW>\d+(\.\d)?)",
        # Nordex (eg Nordex N131/3300, Nordex N149/4.0-4.5, Nordex N149/5.X, Nordex N90)
        r"(?P<manufacturer>Nordex|Sudwind|Suedwind|Südwind) (N|S)(\s|-)?(?P<diameter>\d+)((/(?P<power>\d+(\.(\d+|X|x))?))(-\d(\.\d+)?)?)?",
        # Tacke (eg Tacke TW 1.5i)
        r"(?P<manufacturer>Tacke)\s+(TW|WR|TZ)\s?(?P<power>\d+(\.\d+))[a-z]+",
        # BARD pattern (eg BARD  6.5, BARD  VM)
        r"(?P<manufacturer>BARD) (?P<power>(\d+(\.\d+)?)|V)M?",
        # GE/Enron pattern (eg General Electric  GE 3.2 -103, GE General Electric  GE 3.4-137, GE General Electric  GE 3.6s, Cypress 6.0-164)
        r"(?P<manufacturer>(GE General Electric)|(General Electric)|GE|Enron|Cypress)(\s+(Wind|Energy|EN|GE|Haliade|Haliade-X))?(\s|-)(?P<power>\d+(\.\d+)?)\s?((-(?P<power_max>\d+(\.\d+)?))?-\s?(?P<diameter>\d+(\.\d+)?)?)?w*",
        # NEG Micon pattern (eg NEG Micon  NM 43/600, NEG Micon  NM 54/950 )
        r"(?P<manufacturer>(NEG(\s|-)Micon)|NEG|Micon|(NEG Wind World)|(Wind World))\s+(NM|M|W|WW)?\s*(?P<diameter>\d+)C?((/|-)(?P<powerKW>\d+))?",
        # Nordtank pattern (eg Nordtank  NTK 1500 64)
        r"(?P<manufacturer>(Nordtank Energy Group)|Nordtank|NEG)(\s+NTK\s?((?P<powerKW>\d+)(-(?P<unknown>\d+))?)((/|\s)(?P<diameter>\d+))?((/|\s)(?P<hub_height>\d+))?)?",
        # Goldwind/Frisia/Vensys pattern (eg Goldwind  GW 87 / 1500, Frisia  F48/750  )
        r"(?P<manufacturer>Goldwind|Acciona|Frisia|Vensys)\s+(S|GW|GWH|F)?(-|\s)?(?P<diameter>\d+)(\s?/\s?(?P<powerKW>\d+))?",
        # Acciona pattern (eg Acciona  AW-148/3300 )
        r"(?P<manufacturer>Acciona)\s+(AW)?(-|\s)?(?P<diameter>\d+)(\s?/\s?(?P<powerKW>\d+))?",
        # Leitwind pattern (eg Leitwind  LTW42 250 )
        r"(?P<manufacturer>Leitwind)\s+LTW\s?(?P<diameter>\d+)\s(?P<powerKW>\d+)",
        # Fuhrländer LLC pattern (eg Fuhrländer LLC  WTU2.5-103 )
        r"(?P<manufacturer>Fuhrländer|Fuhrlaender) LLC WTU(?P<power>\d+(\.\d+)?)-(?P<diameter>\d+)",
        # Fuhrländer FL pattern (eg Fuhrländer FL 2500/100  )
        r"(?P<manufacturer>Fuhrländer|Fuhrlaender) FL( MD)? (?P<powerKW>\d+(\.\d+)?)(/(?P<diameter>\d+))?",
        # Fuhrländer FUH pattern (eg FUH15 G1 D250  )
        r"(?P<manufacturer>Fuhrländer|Fuhrlaender) FUH(-|\s)?(?P<radius>\d+) G\d+ D(?P<powerKW>\d+(\.\d+)?)",
        # Envision pattern (eg Envision  EN 171-6.5 )
        r"(?P<manufacturer>Envision) (EN|N) (?P<diameter>\d+)-(?P<power>\d+(\.\d+)?)",
        # IWT pattern (eg IWT  V90 )
        r"(?P<manufacturer>IWT)\s+V(?P<diameter>\d+)",
        # THYmøllen pattern (eg THYmøllen TWP40-10 )
        r"(?P<manufacturer>(THY møllen( Aps)?)|THYmøllen|THY) TWP(-|\s)?(?P<swept_area>\d+)-(?P<powerKW>\d+(\.\d+)?)",
        # Seewind pattern (eg Seewind  S 52 750 )
        r"(?P<manufacturer>Seewind) (S\s?)?(?P<diameter>\d+)(\s|/)(?P<powerKW>\d+)",
        # DWP pattern (eg DWP D150/22 )
        r"(?P<manufacturer>DWP|(Windpower D)) D?\s?(?P<powerKW>\d+)(/(?P<diameter>\d+))?",
        # Kleinwind pattern (eg Kleinwind GmbH  Schachner Windrad SW10 )
        r"(?P<manufacturer>(Kleinwind GmbH)|Kleinwind)( Schachner Windrad)? SW(?P<powerKW>\d+(\.\d+)?)",
        # Windtec pattern (eg Windtec  WT1566 )
        r"(?P<manufacturer>Windtec) (WT\s?)?(?P<powerdiameter>\d+)",
        # Eno Energy  Eno 126 4.8
        r"(?P<manufacturer>Eno Energy)\s+eno (?P<diameter>\d+)(\s(?P<power>\d+(\.\d+)))?",
        # DeWind (eg DeWind  D6 64/1250 )
        r"(?P<manufacturer>DeWind)\s+D(?P<diameterDm>\d+(\.\d+)?)(\s(?P<diameter>\d+)/(?P<powerKW>\d+))?",
        # DDIS  DDIS60  )
        r"(?P<manufacturer>DDIS)\s+DDIS(?P<diameter>\d+)",
        # Aircon models, eg AIRCON  30 or AIRCON  10 S
        r"(?P<manufacturer>Aircon) (?P<powerDW>\d+)( S)?",
        # BestWatt eg BestWatt BW10
        r"(?P<manufacturer>BestWatt)\s+(BW|WB)(?P<powerKW>\d+)",
        # KVA Vind models, e.g. KVA Vind  6-10
        r"(?P<manufacturer>KVA Vind)(\s+KVA( Vind))? (?P<diameter>\d+)-(?P<powerKW>\d+)",
        # Vindsyssel VS 150
        r"(?P<manufacturer>Vind-Syssel|Vindsyssel|Vendsyssel) VS\s?(?P<powerKW>\d+)((-|-s|/)(?P<diameter>\d+))?",
        # Gaia  eg, 133-11kW lattice tower
        r"(?P<manufacturer>Gaia|(Gaia Wind)) (?P<swept_area>\d+)-(?P<powerKW>\d+)(\s?kW)?",
        # RRB Enery, eg RRB Energy  V27-225
        r"(?P<manufacturer>RRB|(RRB Energy))(\s+Pawan Shakthi)? (V|PS)(?P<diameter>\d+)?(-(?P<powerKW>\d+))?",
        # EAZ Wind, eg EAZ Wind
        r"(?P<manufacturer>EAZ Wind)(\s+EAZ-(?P<diameter>Twelve))?",
        # Solid Wind, eg Solid Wind  SWP-20 or SWP25-16TG20
        r"(?P<manufacturer>Solid Wind) (SWP|SPW)(-|\s)?(?P<powerKW>\d+(\.\d+)?)",
        # Windmolens op Maat LWT25 or Logic-25kW
        r"(?P<manufacturer>(Windmolens op Maat)|Logic)(-|\s)(LWT)?(?P<powerKW>\d+(\.\d+)?)(\s?kW)?",
        # EWT Directwind 900/54
        r"(?P<manufacturer>EWT|DirectWind) (DW )?(?P<diameter>\d+)(-|\*|\s)(?P<power>\d+(\.\d)?(?P<known_unit>MW)?)",
        # WTN Wind TechnikNord  WTN 500/48 or WTN Wind TechnikNord  WTN 648
        r"(?P<manufacturer>(WTN Wind TechnikNord)|(Wind TechnikNord)|WindTechnikNord|WTN) WTN (?P<powerKW>\d+(\.\d+)?)(/(?P<diameter>\d+))?",
        # FO_ pattern (e.g., FO_012234)
        r"FO_(?P<diameter>\d+)(?P<manufacturer_code>\d{2})",
        # Simplified manufacturer letter+number pattern
        r"(?P<manufacturer>\w+) [A-Z]+(\s|-|/)?\d+((-|\.|/)\d+(\.\d+)?)?",
        # Simplified letter+number pattern (fallback)
        r"[A-Z]+\d+((-|\.|/)\d+(\.\d+)?)?",
    ]

    model_designation = None
    manufacturer = None
    power = None
    diameter = None
    manufacturer_match_pattern = None
    is_known_manufacturer = False

    known_unit = None

    # Try each pattern in order
    for pattern in patterns:
        match = re.search(f"^{pattern}", model_name, re.IGNORECASE)
        if match:
            try:
                manufacturer_match_pattern = get_manufacturer_match_pattern(pattern)
                is_known_manufacturer = manufacturer_match_pattern is not None
            except Exception:
                manufacturer_match_pattern = None

            model_designation = match.group(0)
            # logger.debug(f"Found match for '{model_name}' based on pattern {pattern} to retrieve model_designation = '{model_designation}'")

            with contextlib.suppress(Exception):
                manufacturer = match.group("manufacturer")

            if not manufacturer:
                try:
                    manufacturer_code = match.group("manufacturer_code")
                    manufacturer = get_wf101_manufacturer(int(manufacturer_code))

                    with contextlib.suppress(Exception):
                        # Try to match FORTRAN-based manufacturer with known regex manufacturer
                        for sub_pattern, _ in patterns:
                            manufacturer_match_sub_pattern = (
                                get_manufacturer_match_pattern(sub_pattern)
                            )
                            if manufacturer_match_sub_pattern:
                                manufacturer_match = re.search(
                                    manufacturer_match_sub_pattern,
                                    manufacturer,
                                    re.IGNORECASE,
                                )
                                if manufacturer_match:
                                    manufacturer = manufacturer_match.group(0)
                                    manufacturer_match_pattern = (
                                        manufacturer_match_sub_pattern
                                    )
                                    break
                except (ValueError, IndexError, TypeError):
                    pass

            # Clean up strange dash-named manufacturer in 'Common turbine models'
            if manufacturer in ["NEG-Micon", "AN-Bonus"]:
                manufacturer = manufacturer.replace("-", " ")

            swap_power_diameter = False
            try:
                known_unit = match.group("known_unit")
                if (
                    known_unit is not None
                    and match.group("power") is None
                    and match.group("diameter") is not None
                ):
                    swap_power_diameter = True
            except (ValueError, IndexError, TypeError):
                pass

            try:
                power = (
                    match.group("power")
                    if not swap_power_diameter
                    else match.group("diameter")
                )

                with contextlib.suppress(ValueError, TypeError):
                    power = float(power)

                # Special treatment of roman numbers for power in BARDs turbines
                if manufacturer == "BARD" and power == "V":
                    power = 5000
                    model_designation = f"{manufacturer} {power/1000:1.1f}"
                    known_unit = "kW"

                # Special treatment of strong roundoff in 'Common turbine models'
                if manufacturer == "Senvion" and power == 6:
                    power = 6200
                    model_designation = f"{manufacturer} {power/1000:1.1f}"
                    known_unit = "kW"
            except IndexError:
                pass

            try:
                power2 = float(match.group("power2"))
                if power2 > 0:
                    power = power2
            except (ValueError, IndexError, TypeError):
                pass

            try:
                power100W = float(match.group("powerOW"))

                if power100W < 100:
                    power100W *= 100  # Convert to kW

                if not power:
                    power = power100W
                    known_unit = "kW"

            except (ValueError, IndexError, TypeError):
                pass

            try:
                power10W = float(match.group("powerDW"))

                if power10W < 100:
                    power10W *= 10  # Convert to kW

                if not power:
                    power = power10W
                    known_unit = "kW"

            except (ValueError, IndexError, TypeError):
                pass

            try:
                power = float(match.group("powerMW")) * 1000
                known_unit = "kW"
            except (ValueError, IndexError, TypeError):
                pass

            try:
                power = float(match.group("powerKW"))
                known_unit = "kW"
            except (ValueError, IndexError, TypeError):
                pass

            try:
                diameter_str = (
                    match.group("diameter")
                    if not swap_power_diameter
                    else match.group("power")
                )
                if diameter_str == "Twelve":
                    diameter = 12
                else:
                    diameter = float(diameter_str)

                    if manufacturer and manufacturer.upper() == "MICON":
                        # Micon states sweep area in stead of diameter, correct for this
                        area = diameter
                        radius = math.sqrt(area / math.pi)
                        diameter = 2 * radius
            except (ValueError, IndexError, TypeError):
                pass

            try:
                diameter2 = float(match.group("diameter2"))
                if diameter2 > 0:
                    diameter = diameter2
            except (ValueError, IndexError, TypeError):
                pass

            try:
                diameterDm = float(match.group("diameterDm"))

                if not diameter and diameterDm > 0:
                    diameter = 10 * float(diameterDm)
            except (ValueError, IndexError, TypeError):
                pass

            try:
                area = float(match.group("swept_area"))

                if not diameter:
                    radius = math.sqrt(area / math.pi)
                    diameter = 2 * radius
            except (ValueError, IndexError, TypeError):
                pass

            try:
                radius = float(match.group("radius"))
                if radius > 0 and not diameter:
                    diameter = 2 * radius
            except (ValueError, IndexError, TypeError):
                pass

            if (
                manufacturer is not None
                and diameter is not None
                and power is not None
                and manufacturer.upper() == "WIND WORLD"
                and diameter > 1000
            ):
                diameter /= 100

            if (
                manufacturer is not None
                and power is not None
                and diameter is not None
                and manufacturer.upper()
                in [x.upper() for x in ["Micon", "NEG", "NEG-Micon", "NEG Micon"]]
                and diameter > power
            ):
                # Micon states sweep area in stead of diameter, correct for this
                area = diameter
                radius = math.sqrt(area / math.pi)
                diameter = 2 * radius

            if manufacturer is not None and manufacturer.upper() in [
                x.upper() for x in ["NEG", "NEG-Micon", "NEG Micon"]
            ]:
                # Check if we need to swap power and diameter for some NEG MICON
                # turbine types as they seem to be less consistent
                if (diameter is not None and power is not None and diameter > power) or (
                    diameter is not None and power is None and diameter > 150
                ):
                    diameter, power = power, diameter

            if (
                manufacturer is not None
                and power is not None
                and diameter is None
                and manufacturer.upper()
                in [
                    x.upper()
                    for x in [
                        "WTN Wind TechnikNord",
                        "Wind TechnikNord",
                        "WindTechnikNord",
                        "WTN",
                        "Windtec",
                    ]
                ]
                and power % 10 != 0
            ):
                # The power field is a mix of power and diameter; split the two
                power, diameter = divmod(power, 100)
                power *= 100

            if (
                manufacturer is not None
                and diameter is not None
                and power is None
                and manufacturer.upper()
                in [x.upper() for x in ["Sudwind", "Suedwind", "Südwind"]]
                and diameter > 100
            ):
                # The diameter field is a mix of diameter and power; split the two
                diameter, power = divmod(diameter, 100)
                power *= 10

            try:
                parsed_unit = match.group("known_unit")
                if known_unit is None and len(parsed_unit) > 0:
                    known_unit = "kW"
            except (ValueError, IndexError, TypeError):
                pass

            # Convert power to kW if possible
            if power:
                try:
                    if isinstance(power, str):
                        power_float = float(power.lower().replace("x", "0"))
                    else:
                        power_float = power
                    power = power_to_kw(
                        power_float, known_unit=known_unit, diameter=diameter
                    )
                except (ValueError, TypeError):
                    pass

            break

    # Remove dash between manufacturer and model name
    if model_designation:
        posDash = model_designation.find("-")
        posSpace = model_designation.find(" ")

        if posDash > 0 and (posDash < posSpace or posSpace < 0):
            model_designation = (
                model_designation[:posDash] + " " + model_designation[posDash + 1 :]
            )

    return {
        "model_name": model_name,
        "model_designation": model_designation,
        "manufacturer": manufacturer,
        "manufacturer_pattern": manufacturer_match_pattern,
        "diameter": diameter,
        "power": power,
        "is_known_manufacturer": is_known_manufacturer,
    }


def get_manufacturer_match_pattern(pattern: str) -> str:
    """Builds the regex pattern to match manufacturer name.

    Args:
        pattern (str): Input regex containing a manufacturer group

    Returns:
        regex that only matches the manufacturer group
    """
    open_pos = pattern.find("(?P<manufacturer>")

    if open_pos >= 0:
        pos = open_pos
        depth = 1

        while depth > 0:
            if pattern.find("(", pos + 1) < pattern.find(")", pos + 1):
                pos = pattern.find("(", pos + 1)
                depth += 1
            else:
                close_pos = pattern.find(")", pos + 1)
                pos = pattern.find(")", pos + 1)
                depth -= 1

        manufacturer_pattern = pattern[open_pos : close_pos + 1]

        # Match all shouldn't be a specific manufacturer pattern
        if manufacturer_pattern == r"(?P<manufacturer>\w+)":
            manufacturer_pattern = None

        return manufacturer_pattern

    return None
