"""Module to build model designation from manufacturer, diameter and power."""

import re


def build_model_designation(manufacturer: str, diameter: float, power: float) -> str:
    """Build model designation from manufacturer, diameter and power."""
    if manufacturer.title() == "Vestas":
        if power < 1000:
            return f"{manufacturer} V{diameter:.0f}-{power:.0f}"
        return f"{manufacturer} V{diameter:.0f}-{power/1000:.1f}"

    if manufacturer.title() == "Siemens":
        return f"{manufacturer} SWT-{power/1000:.1f}-{diameter:.0f}"

    if manufacturer.title() == "Siemens Gamesa":
        return f"{manufacturer} SG-{power/1000:.1f}-{diameter:.0f}"

    if manufacturer.title() == "Enercon":
        if power < 500:
            return f"{manufacturer} E-{diameter:.0f} / {power:.0f}"
        if power < 2000:
            return f"{manufacturer} E-{diameter:.0f}/{power/100:.0f}.{diameter:.0f}"
        return f"{manufacturer} E-{diameter:.0f} {power/1000:.3f}"

    if manufacturer.title() in {"Senvion", "Repower"}:
        return f"{manufacturer} {power/1000:.1f}M{diameter:.0f}"

    if manufacturer.title() == "Nordex":
        if diameter < 140:
            return f"{manufacturer} N{diameter:.0f}/{power:.0f}"
        return f"{manufacturer} N{diameter:.0f}/{power/1000:.1f}"

    if manufacturer.title() in {"Bonus", "Dewind"}:
        return f"{manufacturer} {manufacturer.upper()[0]}{diameter:.0f}/{power:.0f}"

    if manufacturer.title() == "Ref":
        return f"{manufacturer}-{power/1000:.1f}"

    return None


def ensure_manufacturer_prefix(model_name: str) -> str:
    """Adds known manufacturers to model_name based on product prefix."""
    patterns = [
        (r"^eno \d+", "Eno Energy"),
        (r"^(SWP|SPW)-?\d{2}", "Solid Wind"),
        (r"^SWT-(DD|\d+)", "Siemens"),
        (r"^LTW\d+", "Leitwind"),
        (r"^LWT\d+", "Windmolens op Maat"),
        (r"^NTK\s?\d+/\d+", "Nordtank"),
        (r"^MWT(-|\s)?\d+", "Mitsubishi"),
        (r"^SG(-|\s)D?\d+", "Siemens Gamesa"),
        (r"^AW(-|\s)?\d+", "Acciona"),
        (r"^DW(-|\s)?\d+", "DirectWind"),
        (r"^EN(-|\s)?\d+", "Envision"),
        (r"^(BW|WB)\d{2}", "BestWatt"),
        (r"^(TW|WR|TZ)\s?\d+", "Tacke"),
        (r"^(EN|GE)(-|\s)(Haliade(-X)? )?\d+", "General Electric"),
        (r"^MM(-|\s)?\d+", "REpower"),
        (r"^(FL|FUH)(-|\s)?\d+", "Fuhrländer"),
        (r"^B(-|\s)?\d+", "Bonus"),
        (r"^D\d+", "DeWind"),
        (r"^E(-|\s)?\d{2,3}", "Enercon"),
        (r"^F(-|\s)?\d+", "Frisia"),
        (r"^G(-|\s)?\d{2,3}", "Gamesa"),
        (r"^K(-|\s)?\d+", "Kenersys"),
        (r"^(NM|M)(-|\s)?\d+", "NEG Micon"),
        (r"^N(-|\s)?\d+", "Nordex"),
        (r"^V(-|\s)?\d{2,3}", "Vestas"),
        (r"^(W|WW)(-|\s)?\d{2,4}", "Wind World"),
        (r"^(GW|GWH)(-|\s)?\d+", "Goldwind"),
    ]

    # Try each pattern in order
    for pattern, manufacturer in patterns:
        match = re.search(pattern, str(model_name), flags=re.IGNORECASE | re.MULTILINE)
        if match:
            new_model_name = f"{manufacturer} {model_name}"
            return new_model_name

    # By default assume manufacturer prefix is present
    return model_name
