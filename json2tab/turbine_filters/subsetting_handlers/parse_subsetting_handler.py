"""Module for parsing specific subsetting handler from subsetting_config."""

from ...logs import logger
from ...turbine_filters.subsetting_handlers.BoundingBoxHandler import BoundingBoxHandler
from ...turbine_filters.subsetting_handlers.CountryHandler import CountryHandler
from ...turbine_filters.subsetting_handlers.DomainHandler import DomainHandler
from ...turbine_filters.subsetting_handlers.TrueHandler import TrueHandler


def parse_subsetting_handler(subsetting_config: dict):
    """Parse specific subsetting handler from subsetting_config.

    Raises:
        ValueError: when method is not specified in subsetting config

    Args:
        subsetting_config (dict): config dict specifying subsetting section

    Returns:
        A subsetting handler initialized with configuration
    """
    # Validate spatial subsetting configuration
    method = subsetting_config["method"]
    if method not in subsetting_config:
        raise ValueError(f"{method} configuration missing.")

    if method == "domain":
        return DomainHandler(subsetting_config["domain"])

    if method == "bbox":
        return BoundingBoxHandler(subsetting_config["bbox"])

    if method == "country":
        return CountryHandler(subsetting_config["country"])

    if method == "true":
        return TrueHandler()

    logger.error(
        f"Subsetting method must be either 'bbox, 'country' or 'domain', "
        f"found method = {method}."
    )
    return None
