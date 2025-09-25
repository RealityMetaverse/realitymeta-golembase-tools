#!/usr/bin/env python3
"""
Data utility functions for processing data.
"""

import base64
import hashlib
from pathlib import Path
from typing import Any, Dict
from ..common.enums import Encoding


def generate_content_hash(data: Dict[str, str | int]) -> str:
    """
    Generate a SHA-256 hash from the keys and values of the dictionary.
    This creates a hash that can be used to detect changes in the data.
    """
    # Sort keys for deterministic hashing
    sorted_items = sorted(data.items())

    # Create a string representation of all key-value pairs
    hash_input = ""
    for key, value in sorted_items:
        hash_input += f"{key}:{str(value)}|"

    # Generate SHA-256 hash
    hash_object = hashlib.sha256(hash_input.encode(Encoding.UTF8.value))
    return hash_object.hexdigest()


def is_field_none_or_empty_string(
    field_value: Any, field_name: str = ""
) -> tuple[bool, str]:
    """
    Check if a field value is None or empty string.

    Args:
        field_name: The name of the field being checked
        field_value: The value to check

    Returns:
        Tuple of (is_invalid: bool, error_message: str)
        - is_invalid: True if field is None or empty string, False if valid
        - error_message: Empty string if valid, descriptive error message if invalid
    """
    if field_value is None:
        return True, f"'{field_name}' is None"

    if isinstance(field_value, str) and field_value.strip() == "":
        return True, f"'{field_name}' is empty string"

    return False, ""


# DEV: according to OpenSea NFT Metadata Spec
def is_nft_metadata_attribute_field(field_data: list[dict]) -> bool:
    return isinstance(field_data, list) and all(
        isinstance(item, dict) and "trait_type" in item and "value" in item
        for item in field_data
    )


def read_file_as_base64(file_path: Path) -> str:
    """Read file content as base64 string. Raises IOError if reading fails."""
    try:
        with file_path.open("rb") as f:
            return base64.b64encode(f.read()).decode(Encoding.UTF8.value)
    except (OSError, ValueError) as e:
        raise IOError(f"Could not read file as base64 for {file_path.name}: {e}") from e


def write_base64_to_file(encoded_str: str, output_path: Path) -> None:
    """Decode base64 string and write it to file."""
    try:
        binary_data = base64.b64decode(encoded_str.encode(Encoding.UTF8.value))
        with output_path.open("wb") as f:
            f.write(binary_data)
    except (OSError, ValueError) as e:
        raise IOError(f"Could not write base64 to file {output_path.name}: {e}") from e


def recreate_file_from_entity(entity: Any, output_dir: Path) -> Path:
    """
    Recreate a file from a RealityMetaGolemBaseEntity instance.

    Args:
        entity: A RealityMetaGolemBaseEntity instance containing file data and metadata
        output_dir: Directory where the recreated file should be saved

    Returns:
        Path to the recreated file

    Raises:
        ValueError: If entity is invalid or missing required data
        IOError: If file creation fails
    """
    # Validate entity has required attributes
    required_attrs = ["_sys_data", "_sys_file_name", "_sys_file_extension"]
    for attr in required_attrs:
        if not hasattr(entity, attr):
            raise ValueError(f"Entity missing required attribute: {attr}")

    # Get file data and metadata
    file_data = getattr(entity, "_sys_data")
    file_name = getattr(entity, "_sys_file_name")
    file_extension = getattr(entity, "_sys_file_extension")

    # Check if data is valid
    if file_data is None or file_data == "null" or file_data.strip() == "":
        raise ValueError("Entity contains no file data to recreate")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Construct output file path
    output_file_path = output_dir / file_name

    # If file_name doesn't have extension, add it
    if not output_file_path.suffix and file_extension:
        output_file_path = output_file_path.with_suffix(f".{file_extension}")

    # Recreate the file
    write_base64_to_file(file_data, output_file_path)

    return output_file_path
