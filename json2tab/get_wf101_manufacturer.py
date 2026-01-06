"""Module to translate wf101 manufacturer type code to manufacturer name."""


def get_wf101_manufacturer(MAN_CODE: int) -> str:
    """Translates wf101 manufacturer type code to manufacturer name.

    Args:
        MAN_CODE (int): last two digits of wf101 turbine type (aka manufacturer code)

    Returns:
        MANUFACTURER as human readable manufacturer name (or None)
    """
    MANUFACTURER = None

    if ( MAN_CODE ==  0 ): MANUFACTURER = "Senvion-Repower/Jacobs/HSW Husum/Kenersys"
    if ( MAN_CODE ==  1 ): MANUFACTURER = "VESTAS ONSHORE"
    if ( MAN_CODE ==  2 ): MANUFACTURER = "NORDEX"
    if ( MAN_CODE ==  3 ): MANUFACTURER = "GE/Enron"
    if ( MAN_CODE ==  4 ): MANUFACTURER = "Fuhrlaender/Protec MD"
    if ( MAN_CODE ==  5 ): MANUFACTURER = "NEG MICON/Nordtank"
    if ( MAN_CODE ==  6 ): MANUFACTURER = "Siemens SWT/GAMESA/BONUS ONSHORE"
    if ( MAN_CODE ==  7 ): MANUFACTURER = "DeWIND"
    if ( MAN_CODE ==  8 ): MANUFACTURER = "Enercon"
    if ( MAN_CODE ==  9 ): MANUFACTURER = "VENSYS"
    if ( MAN_CODE == 20 ): MANUFACTURER = "Tacke"
    if ( MAN_CODE == 21 ): MANUFACTURER = "KNMI onshore reference turbine"
    if ( MAN_CODE == 22 ): MANUFACTURER = "Goldwind (China)"
    if ( MAN_CODE == 23 ): MANUFACTURER = "Leitwind (Italy)"
    if ( MAN_CODE == 24 ): MANUFACTURER = "ACCIONA (Spain)"
    if ( MAN_CODE == 25 ): MANUFACTURER = "KONCAR Croatian manufacturer"
    if ( MAN_CODE == 26 ): MANUFACTURER = "Frisia"
    if ( MAN_CODE == 27 ): MANUFACTURER = "Schuetz"
    if ( MAN_CODE == 28 ): MANUFACTURER = "Envision (China Shanghai)"
    if ( MAN_CODE == 29 ): MANUFACTURER = "Eno Energy"
    if ( MAN_CODE == 40 ): MANUFACTURER = "DDIS France"
    if ( MAN_CODE == 41 ): MANUFACTURER = "FWT"
    if ( MAN_CODE == 42 ): MANUFACTURER = "Wind world (DK)"
    if ( MAN_CODE == 43 ): MANUFACTURER = "Kleinwind SW10"
    if ( MAN_CODE == 44 ): MANUFACTURER = "Seewind"
    if ( MAN_CODE == 45 ): MANUFACTURER = "WTN Windtechnik Nord"
    if ( MAN_CODE == 10 ): MANUFACTURER = "Senvion OFFSHORE"
    if ( MAN_CODE == 11 ): MANUFACTURER = "Vestas OFFSHORE"
    if ( MAN_CODE == 16 ): MANUFACTURER = "SWT OFFSHORE"
    if ( MAN_CODE == 30 ): MANUFACTURER = "Haliade OFFSHORE"
    if ( MAN_CODE == 31 ): MANUFACTURER = "REF OFFSHORE (KNMI)"
    if ( MAN_CODE == 32 ): MANUFACTURER = "Adwen"
    if ( MAN_CODE == 33 ): MANUFACTURER = "Areva"
    if ( MAN_CODE == 34 ): MANUFACTURER = "BARD"

    # Overrides to fix multi manufacturer regex matches
    if ( MAN_CODE ==  0 ): MANUFACTURER = "Senvion"
    if ( MAN_CODE ==  1 ): MANUFACTURER = "Vestas"
    if ( MAN_CODE ==  3 ): MANUFACTURER = "GE General Electric"
    if ( MAN_CODE ==  6 ): MANUFACTURER = "Siemens"
    if ( MAN_CODE == 43 ): MANUFACTURER = "Kleinwind GmbH"
    

    return MANUFACTURER
