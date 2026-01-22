"""Module to write pandas dataframe with statistics data to file."""

import os
from pathlib import Path
from typing import Optional

import pandas as pd
from tabulate import tabulate

from ..io.writers import generate_output_filename, parse_ext_string_to_list
from ..logs import logger


def write_statistics(
    stats: pd.DataFrame, output_dir: Path, filename: str, header: Optional[str] = None
) -> str:
    """Write statistics table to file, returns plain text table."""
    plain_text = tabulate(stats, headers="keys", tablefmt="psql", showindex=False)

    if filename is not None and len(filename) > 0:
        _, ext = os.path.splitext(filename)
        exts = parse_ext_string_to_list(ext)

        for ext in exts:
            output_filename = output_dir / generate_output_filename(filename, ext)
            if ext.lower() in ["csv", ".csv"]:
                stats.to_csv(output_filename, index=False)
            elif ext.lower() in ["txt", ".txt"]:
                with open(output_filename, "w") as file:
                    if header is None:
                        header = ""

                    if len(header) > 0 and not header.endswith("\n"):
                        header = f"{header}\n"

                    file.write(f"{header}{plain_text}")
            else:
                logger.warning(
                    f"Could not derive valid output format for extension {ext}. "
                    "No file written."
                )

    return plain_text


def inject_suffix_in_filename(filename: str, suffix: str) -> str:
    """Inject suffix in filename before extension."""
    if filename is None or len(filename) == 0:
        return filename

    filename, ext = os.path.splitext(filename)
    return f"{filename}{suffix}{ext}"
