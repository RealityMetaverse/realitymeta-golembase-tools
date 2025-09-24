#!/usr/bin/env python3
"""
Converts data to Golem Base compatible format.
Only works with JSON files.
"""

import argparse
import re
import shutil
import sys
import inquirer
from pathlib import Path
from typing import Any, Dict, Optional, List
from ..common.config import DataTypes, get_converted_data_required_fields
from ..utils.logging_utils import (
    print_green_checkmark,
    print_yellow_warning,
    print_blue_arrow,
    print_red_x,
)
from ..utils.file_utils import (
    write_json,
    load_data_files,
)
from ..utils.data_utils import (
    calculate_data_size,
    generate_content_hash,
    to_scalar,
)
from ..common.globals import logger, media_stats, reset_globals


def sanitize_key(key: str) -> str:
    """Make keys JSON friendly and consistent."""
    # Keep case for readability but normalize spaces/symbols
    key = key.strip()
    # Replace spaces and illegal chars with underscore
    key = re.sub(r"[^\w\-]", "_", key)
    # Collapse multiple underscores
    key = re.sub(r"__+", "_", key)
    return key


def validate_required_fields(
    converted_doc: Dict[str, Any], data_type: DataTypes
) -> List[str]:
    """
    Check if the converted document contains all required fields.
    Returns list of missing fields (empty list if all fields are present).
    """
    required_fields = get_converted_data_required_fields(data_type)
    missing_fields = required_fields - set(converted_doc.keys())
    return sorted(list(missing_fields))


def extract_attribute_key(attr: Dict[str, Any]) -> Optional[str]:
    """
    Get a stable attribute key name:
    Prefer 'trait_type', fallback to 'type' or 'name' if present.
    Returns None if no valid key is found.
    """
    for k in ("trait_type", "type", "name"):
        if k in attr and isinstance(attr[k], str) and attr[k].strip():
            return attr[k]

    # No valid key found
    return None


def convert_data(
    doc_data: Dict[str, Any],
    file_basename_stem: str = "unknown",
    data_type: DataTypes = DataTypes.STANDARD,
) -> Dict[str, Any]:
    """
    Flatten a single document:
    - Move attributes[] into top-level as attributes_<trait>
    - Check if media URLs belong to this specific asset
    """
    converted = {}

    # Copy non-attributes top-level fields (except 'attributes')
    for k, v in doc_data.items():
        if k == "attributes":
            continue
        scalar_value, conversion_info = to_scalar(v)

        if scalar_value is None:
            logger.warn(
                f"{file_basename_stem:>6}: {k} field is None - field will be skipped"
            )
            continue

        # Log conversion info if there was a type conversion
        if conversion_info:
            logger.info(f"{file_basename_stem:>6}: {k} field {conversion_info}")

        # Check media URL file_basename matches for image, animation_url, and external_url
        if k in ["image", "animation_url", "external_url"]:
            media_stats.check_and_record_media_url_match(
                scalar_value, file_basename_stem, k
            )

        converted[sanitize_key(k)] = scalar_value

    # Handle attributes array
    attrs = doc_data.get("attributes")
    if isinstance(attrs, list):
        for item in attrs:
            if not isinstance(item, dict):
                continue
            trait = extract_attribute_key(item)
            if trait is None:
                logger.warn(
                    f"{file_basename_stem:>6}: No valid key found in attribute dict: {item}"
                )
                continue  # Skip attributes without valid keys
            trait = sanitize_key(trait)
            out_key = f"attributes_{trait}"

            # Check if 'value' field exists and is not None
            value = item.get("value")
            if value is None:
                logger.warn(
                    f"{file_basename_stem:>6}: Attribute '{trait}' has None value - attribute will be skipped"
                )
                continue  # Skip this entire attribute

            # Check for duplicate traits - skip if already exists
            if out_key in converted:
                logger.warn(
                    f"{file_basename_stem:>6}: Duplicate trait '{trait}' - duplicate will be skipped"
                )
                continue

            scalar_value, conversion_info = to_scalar(value)

            if scalar_value is None:
                logger.warn(
                    f"{file_basename_stem:>6}: {out_key} field is None - field will be skipped"
                )
                continue

            # Log conversion info if there was a type conversion
            if conversion_info:
                logger.info(
                    f"{file_basename_stem:>6}: {out_key} field {conversion_info}"
                )

            converted[out_key] = scalar_value

    # Add data_type field to identify this as NFT metadata
    converted["data_type"] = data_type.value

    # Generate data_fields string containing all field names that will be in the final document
    # We need to include all fields that will be present after adding metadata fields
    temp_converted = converted.copy()
    temp_converted["data_fields"] = ""  # Placeholder
    temp_converted["data_size"] = 0  # Placeholder
    temp_converted["content_hash"] = ""  # Placeholder

    # Create sorted list of all field names (including the metadata fields we're adding)
    all_field_names = sorted(temp_converted.keys())
    # Convert to comma-separated string
    converted["data_fields"] = ",".join(all_field_names)

    # Calculate and add data_size field (size in bytes when serialized as JSON)
    # We need to iteratively calculate this to get the accurate size including the data_size field itself
    temp_converted = converted.copy()

    # Start with a reasonable estimate and iterate to find the exact size
    estimated_size = 100000  # Start with a large estimate
    for _ in range(5):  # Maximum 5 iterations should be enough
        temp_converted["data_size"] = estimated_size
        actual_size = calculate_data_size(temp_converted)
        if actual_size == estimated_size:
            break  # Converged to the exact size
        estimated_size = actual_size

    converted["data_size"] = estimated_size

    # Generate content hash from all the converted data (including data_size)
    converted["content_hash"] = generate_content_hash(converted)

    return converted


def select_data_type_interactive() -> DataTypes:
    """
    Interactive menu to select data type using arrow keys.
    Returns the selected DataTypes enum value.
    """
    # Create choices with descriptions
    data_types = list(DataTypes)
    descriptions = {
        DataTypes.STANDARD: None,
        DataTypes.REALITY_NFT_METADATA: None,
    }

    # Create formatted choices for inquirer
    choices = []
    for dt in data_types:
        description = descriptions.get(dt, "No description available")
        choice_text = dt.value
        choice_text = (
            choice_text if description is None else f"{dt.value} - {description}"
        )
        choices.append(choice_text)

    try:
        questions = [
            inquirer.List(
                "data_type",
                message="Select data type for conversion",
                choices=choices,
                carousel=True,  # Allow wrapping around
            ),
        ]
        answers = inquirer.prompt(questions)

        if answers is None:  # User pressed Ctrl+C
            print("\nOperation cancelled by user.")
            sys.exit(0)

        # Extract the data type from the selected choice
        selected_choice = answers["data_type"]
        selected_type_value = selected_choice.split(" - ")[0]
        selected_type = DataTypes(selected_type_value)

        print(f"\n✓ Selected: {selected_type.value}")
        print(
            f"  Description: {descriptions.get(selected_type, 'No description available')}"
        )

        # Show additional required fields for specialized types
        if selected_type != DataTypes.STANDARD:
            required_fields = get_converted_data_required_fields(selected_type)
            standard_fields = get_converted_data_required_fields(DataTypes.STANDARD)
            extra_fields = required_fields - standard_fields
            if extra_fields:
                print(
                    f"  Additional required fields: {', '.join(sorted(extra_fields))}"
                )
        print()

        return selected_type

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)


def main():
    # Reset global instances to ensure clean state
    reset_globals()

    ap = argparse.ArgumentParser(
        description="Convert data to Golem Base compatible format."
    )
    ap.add_argument(
        "--in-dir",
        "--in",
        "-i",
        dest="in_dir",
        required=True,
        help="Input directory with JSON files",
    )
    ap.add_argument("--out-dir", "-o", dest="out_dir", help="Output directory")
    ap.add_argument(
        "--data-type",
        "-dt",
        dest="data_type",
        choices=[dt.value for dt in DataTypes],
        help="Data type for conversion. If not provided, an interactive menu will be shown.",
        metavar="{" + ",".join([dt.value for dt in DataTypes]) + "}",
    )
    ap.add_argument(
        "--clean-out-dir",
        "-cod",
        action="store_true",
        help="Clean output directory before processing",
    )

    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = None
    if args.out_dir:
        out_dir = Path(args.out_dir)

    clean_out_dir = args.clean_out_dir

    # Handle data type selection
    if args.data_type is None:
        # No data type provided, show interactive menu
        data_type = select_data_type_interactive()
    else:
        # Convert data_type string to DataTypes enum (argparse choices ensures it's valid)
        data_type = DataTypes(args.data_type)

    # Handle output directory - if not provided, create in_dir + "_converted" in parent directory
    if out_dir is None:
        parent_dir = in_dir.parent
        converted_folder_name = f"{in_dir.name}_converted"
        out_dir = parent_dir / converted_folder_name

    # Load all JSON files using the improved load_data_files function
    try:
        data_files = load_data_files(in_dir)
    except (FileNotFoundError, ValueError) as e:
        print_red_x(f"Error: {e}")
        sys.exit(1)

    if not data_files:
        return

    converted_docs = 0
    skipped_docs = 0
    field_counts = {}  # Track how many times each field appears
    total_files = 0  # Track total number of successfully processed files

    # Clean output directory before start if requested
    if clean_out_dir and out_dir.is_dir():
        print_blue_arrow(f"Cleaning output directory: {out_dir}")
        shutil.rmtree(out_dir, ignore_errors=True)

    # Convert each file
    for file_data in data_files:
        # Extract the original data (without the added metadata)
        doc_data = {
            k: v
            for k, v in file_data.items()
            if k not in ["file_path", "file_basename", "file_basename_stem"]
        }
        file_basename = file_data["file_basename"]
        file_basename_stem = file_data["file_basename_stem"]

        converted = convert_data(
            doc_data=doc_data,
            file_basename_stem=file_basename_stem,
            data_type=data_type,
        )

        # Validate required fields
        missing_fields = validate_required_fields(converted, data_type)
        if missing_fields:
            missing_list = ", ".join(missing_fields)
            logger.warn(
                f"{file_basename_stem:>6}: Missing required fields: {missing_list} - file will be skipped"
            )
            skipped_docs += 1
            continue

        converted_docs += 1
        total_files += 1

        # Track field occurrences
        for field_name in converted.keys():
            field_counts[field_name] = field_counts.get(field_name, 0) + 1

        # Save per-file converted JSON
        write_json(out_dir / file_basename, converted)

    # Log field occurrence statistics
    if field_counts:
        print(f"\nFIELD OCCURRENCE STATISTICS (out of {total_files} files):")
        print("-" * 50)

        # Find the longest field name for consistent spacing
        max_field_length = (
            max(len(field_name) for field_name in field_counts.keys())
            if field_counts
            else 0
        )
        max_field_length = max_field_length + 1

        for field_name, count in sorted(field_counts.items()):
            if count == total_files:
                print(f"{field_name:<{max_field_length}}: {count} (all)")
            else:
                print(f"{field_name:<{max_field_length}}: {count}")

    # Log media statistics
    media_stats.print_statistics_report()

    # Log statistics
    logger.print_summary()
    # Summary
    if skipped_docs > 0:
        print_green_checkmark(
            f"Wrote {converted_docs} converted JSON files to: {out_dir}"
        )
        print_yellow_warning(
            f"Skipped {skipped_docs} files due to missing required fields"
        )
    else:
        print_green_checkmark(
            f"Wrote {converted_docs} converted JSON files to: {out_dir}"
        )


if __name__ == "__main__":
    main()
