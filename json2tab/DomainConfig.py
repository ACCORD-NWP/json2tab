"""Module with domain configuration similar to Tactus."""

import os
from dataclasses import dataclass
from typing import Any, Dict

import tomli as toml


@dataclass
class DomainConfig:
    """Configuration class for domain specifications.

    Attributes:
        name (str): Domain name
        xloncen (float): Center longitude
        xlatcen (float): Center latitude
        xdx (float): Grid spacing in x-direction (meters)
        xdy (float): Grid spacing in y-direction (meters)
        nimax (int): Number of grid points in x-direction
        njmax (int): Number of grid points in y-direction
    """

    name: str
    xloncen: float
    xlatcen: float
    xdx: float
    xdy: float
    nimax: int
    njmax: int

    @classmethod
    def from_toml(cls, toml_path: str) -> "DomainConfig":
        """Create DomainConfig from TOML file.

        Args:
            toml_path (str): Path to TOML configuration file

        Returns:
            DomainConfig: Initialized domain configuration

        Raises:
            FileNotFoundError: If TOML file doesn't exist
            KeyError: If required keys are missing from TOML file
        """
        if not os.path.exists(toml_path):
            raise FileNotFoundError(f"TOML file not found: {toml_path}")

        with open(toml_path, "r") as file:
            config = toml.load(file)
            try:
                domain = config["domain"]
                return DomainConfig.from_dict(domain)
            except KeyError as e:
                raise KeyError(f"Missing required key in TOML file: {e}") from e

    @classmethod
    def from_dict(cls, domain: Dict[str, Any]) -> "DomainConfig":
        """Create DomainConfig from config dictionary.

        Args:
            domain (Dict[str, Any]): Dictionary containing domain config

        Returns:
            DomainConfig: Initialized domain configuration

        Raises:
            KeyError: If required keys are missing in dictionary
        """
        try:
            return cls(
                name=domain["name"],
                xloncen=domain["xloncen"],
                xlatcen=domain["xlatcen"],
                xdx=domain["xdx"],
                xdy=domain["xdy"],
                nimax=domain["nimax"],
                njmax=domain["njmax"],
            )
        except KeyError as e:
            raise KeyError(f"Missing required key config dictionary: {e}") from e

    @classmethod
    def from_config(cls, domain_config: Dict[str, Any]) -> "DomainConfig":
        """Create DomainConfig from config dictionary.

        Args:
            domain_config (Dict[str, Any]): json2tab domain configuration

        Returns:
            DomainConfig: Initialized domain configuration
        """
        if "file" in domain_config:
            domain_file = domain_config["file"]
            domain = DomainConfig.from_toml(domain_file)
        else:
            domain = DomainConfig.from_dict(domain_config)

        return domain
