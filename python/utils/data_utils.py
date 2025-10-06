#!/usr/bin/env python3
"""
Data utility functions for processing data.
"""

import base64
import hashlib
import gzip
import json
from pathlib import Path
from typing import Any, Dict, Tuple
from ..common.enums import Encoding, CompressionMethod, FileType
from ..common.config import OVERSIZED_FILE_COMPRESSION_STRATEGY, BASE64_EXPANSION_FACTOR


def decode_base64_to_bytes(encoded_str: str) -> bytes:
    """
    Decode base64 string to bytes.
    Raises ValueError if decoding fails.
    """
    try:
        return base64.b64decode(encoded_str.encode(Encoding.UTF8.value))
    except ValueError as e:
        raise ValueError(f"Could not decode base64 string: {e}") from e


def encode_bytes_to_base64(data: bytes) -> str:
    """
    Encode bytes to base64 string.
    """
    return base64.b64encode(data).decode(Encoding.UTF8.value)


def minify_json_data(data: Any) -> str:
    """
    Minify JSON data by removing whitespace.
    """
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def minify_json_file_data(file_data: bytes) -> bytes:
    """
    Minify JSON data by removing whitespace.
    Raises ValueError if JSON parsing fails.
    """
    try:
        # Parse and minify JSON
        json_data = json.loads(file_data.decode(Encoding.UTF8.value))
        minified_json = minify_json_data(json_data)
        return minified_json.encode(Encoding.UTF8.value)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Could not parse JSON data: {e}") from e


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
            return encode_bytes_to_base64(f.read())
    except (OSError, ValueError) as e:
        raise IOError(f"Could not read file as base64 for {file_path.name}: {e}") from e


def write_base64_to_file(encoded_str: str, output_path: Path) -> None:
    """Decode base64 string and write it to file."""
    try:
        binary_data = decode_base64_to_bytes(encoded_str)
        with output_path.open("wb") as f:
            f.write(binary_data)
    except (OSError, ValueError) as e:
        raise IOError(f"Could not write base64 to file {output_path.name}: {e}") from e


def recreate_file_from_entity(entity: Any, output_dir: Path) -> Path:
    """
    Recreate a file from a RmArkivEntity instance.

    Args:
        entity: A RmArkivEntity instance containing file data and metadata
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


# TODO: When RmArkivEntity supports multiple versions with different MAX_FILE_SIZE values,
#       update this function to accept a version parameter and use the appropriate size limit
def get_compression_strategy(file_type: str, file_size: int) -> CompressionMethod:
    """
    Get compression strategy for a file type.
    Compression is ONLY applied if file is oversized (over MAX_FILE_SIZE).
    """
    from ..dataclasses.rm_arkiv_entity import RmArkivEntity

    # Check if file is oversized and use compression strategy
    if file_size * BASE64_EXPANSION_FACTOR > RmArkivEntity.MAX_FILE_SIZE:
        try:
            file_type_enum = FileType.from_string(file_type)
            compression_type = OVERSIZED_FILE_COMPRESSION_STRATEGY.get(
                file_type_enum, CompressionMethod.NONE
            )
            return compression_type
        except ValueError:
            # If file_type is not a valid FileType, return no compression
            return CompressionMethod.NONE

    # No compression by default for normal-sized files
    return CompressionMethod.NONE


def read_file_as_base64_with_compression(
    file_path: Path, file_type: str, file_size: int
) -> Tuple[str, str, int | None]:
    """
    Read file with smart compression based on file type.
    Returns: (base64_encoded_data, compression_method, compressed_data_size)
    """

    try:
        compression_strategy = get_compression_strategy(file_type, file_size)

        # Read file as binary
        with file_path.open("rb") as f:
            file_data = f.read()

        if compression_strategy == CompressionMethod.GZIP:
            # For JSON files, minify before compression for better results
            if file_type == FileType.JSON.value:
                file_data = minify_json_file_data(file_data)

            # Try gzip compression
            compressed_data = gzip.compress(file_data)

            # Use compression if it actually reduces size
            if len(compressed_data) < len(file_data):
                base64_data = encode_bytes_to_base64(compressed_data)
                return base64_data, CompressionMethod.GZIP.value, len(compressed_data)
            else:
                # No compression beneficial, use original
                base64_data = encode_bytes_to_base64(file_data)
                return base64_data, CompressionMethod.NONE.value, None

        elif compression_strategy == CompressionMethod.NONE:
            base64_data = encode_bytes_to_base64(file_data)
            return base64_data, CompressionMethod.NONE.value, None
        else:
            raise ValueError(f"Unknown compression strategy: {compression_strategy}")

    except (OSError, ValueError) as e:
        raise IOError(f"Could not process file {file_path.name}: {e}") from e


def decompress_gzip_data(encoded_str: str) -> bytes:
    """Decode base64, decompress gzip, and return data as bytes."""
    try:
        # Decode base64 and decompress
        compressed_data = decode_base64_to_bytes(encoded_str)
        decompressed_data = gzip.decompress(compressed_data)
        return decompressed_data
    except (ValueError, OSError) as e:
        raise IOError(f"Could not decompress gzip data: {e}") from e


def write_compressed_data_to_file(
    encoded_str: str, output_path: Path, compression_type: str
) -> None:
    """Write compressed data to file, decompressing if necessary."""
    try:
        if compression_type == CompressionMethod.GZIP.value:
            # Decompress gzip and write binary
            decompressed_data = decompress_gzip_data(encoded_str)
            with output_path.open("wb") as f:
                f.write(decompressed_data)

        else:  # compression_type == "none"
            # No compression, use original method
            write_base64_to_file(encoded_str, output_path)

    except (OSError, ValueError, json.JSONDecodeError) as e:
        raise IOError(
            f"Could not write decompressed file {output_path.name}: {e}"
        ) from e
