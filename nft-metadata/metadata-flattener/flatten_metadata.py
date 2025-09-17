#!/usr/bin/env python3
"""
Flatten NFT metadata files by converting nested attributes to flat fields.
"""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, List

# REQUIRED FIELDS CONFIGURATION
# Add field names that must be present in the flattened metadata
# If any of these fields are missing, the metadata file will be skipped
REQUIRED_FIELDS = {
    "animation_url",
    "attr__id",
    "attr_category",
    "attr_location_lat",
    "attr_location_lon",
    "attr_type",
    "description",
    "external_url",
    "image",
    "license",
    "markerUrl",
    "name",
    "nftValue",
    "shares",
    "content_hash"
}

# Global log counters
info_count = 0
warn_count = 0
header_printed = False

# Media statistics counters and lists
default_image_count = 0
default_animation_url_count = 0
default_external_url_count = 0

# Lists to store NFT names using default media
default_image_nfts = []
default_animation_url_nfts = []
default_external_url_nfts = []

def color_text(text: str, color: str) -> str:
    """Apply ANSI color codes to text."""
    colors = {
        'blue': '\033[94m',
        'yellow': '\033[93m', 
        'green': '\033[92m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def _print_header_if_needed() -> None:
    """Print log header if it hasn't been printed yet."""
    global header_printed
    if not header_printed:
        print("\nPROCESSING LOG:")
        print("-" * 15)
        header_printed = True

def log_info(message: str) -> None:
    """Print INFO message in blue and increment counter."""
    global info_count
    _print_header_if_needed()
    info_count += 1
    print(f"{color_text('[INFO]', 'blue')} {message}")

def log_warn(message: str) -> None:
    """Print WARN message in yellow and increment counter."""
    global warn_count
    _print_header_if_needed()
    warn_count += 1
    print(f"{color_text('[WARN]', 'yellow')} {message}")

def sanitize_key(key: str) -> str:
    """Make keys JSON friendly and consistent."""
    # Keep case for readability but normalize spaces/symbols
    key = key.strip()
    # Replace spaces and illegal chars with underscore
    key = re.sub(r"[^\w\-]", "_", key)
    # Collapse multiple underscores
    key = re.sub(r"__+", "_", key)
    return key

def clean_metadata_name(metadata_name: str) -> str:
    """Remove .json extension from metadata name for cleaner logging."""
    if metadata_name.endswith('.json'):
        return metadata_name[:-5]
    return metadata_name

def extract_filename_from_url(url: str) -> str:
    """
    Extract filename from URL by taking the part after the last '/' 
    and removing the file extension.
    """
    if not isinstance(url, str) or not url.strip():
        return ""
    
    # Get the part after the last '/'
    filename_with_ext = url.split('/')[-1]
    
    # Remove file extension (everything after the last '.')
    if '.' in filename_with_ext:
        filename = filename_with_ext.rsplit('.', 1)[0]
    else:
        filename = filename_with_ext
    
    return filename

def check_media_url_match(url: str, metadata_name: str, field_name: str) -> None:
    """
    Check if the filename extracted from URL matches the metadata name.
    If it doesn't match, the NFT is using a default/generic media file.
    """
    global default_image_count, default_animation_url_count, default_external_url_count
    global default_image_nfts, default_animation_url_nfts, default_external_url_nfts
    
    expected_name = clean_metadata_name(metadata_name)
    actual_filename = extract_filename_from_url(url)
    
    if actual_filename != expected_name:
        if field_name == 'image':
            default_image_count += 1
            default_image_nfts.append(expected_name)
        elif field_name == 'animation_url':
            default_animation_url_count += 1
            default_animation_url_nfts.append(expected_name)
        elif field_name == 'external_url':
            default_external_url_count += 1
            default_external_url_nfts.append(expected_name)

def generate_content_hash(data: Dict[str, Any]) -> str:
    """
    Generate a SHA-256 hash from the keys and values of the data dictionary.
    This creates a deterministic hash that can be used to detect data changes.
    """
    # Sort keys for deterministic hashing
    sorted_items = sorted(data.items())
    
    # Create a string representation of all key-value pairs
    # Since flattened data only contains int or str values, we can simplify
    hash_input = ""
    for key, value in sorted_items:
        hash_input += f"{key}:{str(value)}|"
    
    # Generate SHA-256 hash
    hash_object = hashlib.sha256(hash_input.encode('utf-8'))
    return hash_object.hexdigest()

def validate_required_fields(flat_doc: Dict[str, Any]) -> List[str]:
    """
    Check if the flattened document contains all required fields.
    Returns list of missing fields (empty list if all fields are present).
    """
    missing_fields = REQUIRED_FIELDS - set(flat_doc.keys())
    return sorted(list(missing_fields))

def extract_attr_key(attr: Dict[str, Any]) -> Optional[str]:
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

def to_scalar(value: Any, field_name: str = "unknown", metadata_name: str = "unknown") -> Any:
    """
    Convert values to supported scalar types (int or str only).
    - int: keep as int
    - str: keep as str
    - float: convert to string
    - bool: true -> 1, false -> 0
    - None: return None (caller should skip this field)
    - any other type: convert to string
    """
    original_type = type(value).__name__
    
    # Handle None - return None (caller will handle logging)
    if value is None:
        return None
    
    # Handle empty string - return None (caller will handle logging)
    if isinstance(value, str) and value == "":
        return None
    
    # Keep int and str as-is
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value
    
    # Convert float to string
    if isinstance(value, float):
        converted_value = str(value)
        log_info(f"{clean_metadata_name(metadata_name):>6}: {field_name} field converted from {original_type} to str")
        return converted_value
    
    # Convert bool: true -> 1, false -> 0
    if isinstance(value, bool):
        converted_value = 1 if value else 0
        log_info(f"{clean_metadata_name(metadata_name):>6}: {field_name} field converted from {original_type} to int")
        return converted_value
    
    # Any other type -> string
    if isinstance(value, (list, dict)):
        converted_value = json.dumps(value, ensure_ascii=False)
    else:
        converted_value = str(value)
    
    log_info(f"{clean_metadata_name(metadata_name):>6}: {field_name} field converted from {original_type} to str")
    return converted_value

def flatten_one(doc: Dict[str, Any], attr_prefix: str = "attr_", metadata_name: str = "unknown") -> Dict[str, Any]:
    """
    Flatten a single metadata doc:
    - Move attributes[] into top-level as attr_<trait>
    - Check if media URLs belong to this specific asset
    """
    flat = {}

    # Copy non-attributes top-level fields (except 'attributes')
    for k, v in doc.items():
        if k == "attributes":
            continue
        scalar_value = to_scalar(v, field_name=k, metadata_name=metadata_name)

        if scalar_value is None:
            log_warn(f"{clean_metadata_name(metadata_name):>6}: {k} field is None - field will be skipped")
            continue

        # Check media URL filename matches for image, animation_url, and external_url
        if k in ["image", "animation_url", "external_url"]:
            check_media_url_match(scalar_value, metadata_name, k)

        flat[sanitize_key(k)] = scalar_value

    # Handle attributes array
    attrs = doc.get("attributes")
    if isinstance(attrs, list):
        for item in attrs:
            if not isinstance(item, dict):
                continue
            trait = extract_attr_key(item)
            if trait is None:
                log_warn(f"{clean_metadata_name(metadata_name):>6}: No valid key found in attribute dict: {item}")
                continue  # Skip attributes without valid keys
            trait = sanitize_key(trait)
            out_key = f"{attr_prefix}{trait}"

            # Check if 'value' field exists and is not None
            value = item.get("value")
            if value is None:
                log_warn(f"{clean_metadata_name(metadata_name):>6}: Attribute '{trait}' has None value - attribute will be skipped")
                continue  # Skip this entire attribute

            # Check for duplicate traits - skip if already exists
            if out_key in flat:
                log_warn(f"{clean_metadata_name(metadata_name):>6}: Duplicate trait '{trait}' - duplicate will be skipped")
                continue

            scalar_value = to_scalar(value, field_name=out_key, metadata_name=metadata_name)

            if scalar_value is None:
                log_warn(f"{clean_metadata_name(metadata_name):>6}: {out_key} field is None - field will be skipped")
                continue

            flat[out_key] = scalar_value

    # Generate content hash from all the flattened data
    flat["content_hash"] = generate_content_hash(flat)
    
    return flat

def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Flatten metadata JSON files.")
    ap.add_argument("--in", dest="in_dir", default="metadatas", help="Input directory with *.json (default: metadatas)")
    ap.add_argument("--out", dest="out_dir", default="metadatas-flattened", help="Output directory (default: metadatas-flattened)")
    ap.add_argument("--attr-prefix", default="attr_", help="Prefix for attribute fields (default: attr_)")
    ap.add_argument("--clean-out-dir", "-cod", action="store_true", help="Clean output directory before processing")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)

    json_files = sorted(in_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in: {in_dir}")
        return

    flattened_docs = 0
    skipped_docs = 0
    field_counts = {}  # Track how many times each field appears
    total_files = 0    # Track total number of successfully processed files

    # Clean output directory before start if requested
    if args.clean_out_dir and out_dir.exists():
        print(f"{color_text('➤', 'blue')} Cleaning output directory: {out_dir}")
        shutil.rmtree(out_dir, ignore_errors=True)
    
    # Flatten each file
    for fp in json_files:
        try:
            with fp.open("r", encoding="utf-8") as f:
                doc = json.load(f)
        except Exception as e:
            log_warn(f"Skipping {fp.name}: cannot parse JSON ({e})")
            continue

        flat = flatten_one(doc, attr_prefix=args.attr_prefix, metadata_name=fp.name)
        
        # Validate required fields
        missing_fields = validate_required_fields(flat)
        if missing_fields:
            missing_list = ", ".join(missing_fields)
            log_warn(f"{clean_metadata_name(fp.name):>6}: Missing required fields: {missing_list} - file will be skipped")
            skipped_docs += 1
            continue
        
        flattened_docs += 1
        total_files += 1

        # Track field occurrences
        for field_name in flat.keys():
            field_counts[field_name] = field_counts.get(field_name, 0) + 1

        # Save per-file flattened JSON
        write_json(out_dir / fp.name, flat)

    # Log field occurrence statistics
    if field_counts:
        print(f"\nFIELD OCCURRENCE STATISTICS (out of {total_files} files):")
        print("-" * 50)
        
        # Find the longest field name for consistent spacing
        max_field_length = max(len(field_name) for field_name in field_counts.keys()) if field_counts else 0
        max_field_length = max_field_length + 1
        
        for field_name, count in sorted(field_counts.items()):
            if count == total_files:
                print(f"{field_name:<{max_field_length}}: {count} (all)")
            else:
                print(f"{field_name:<{max_field_length}}: {count}")
    
    # Log media statistics
    if default_image_count + default_animation_url_count + default_external_url_count > 0:
        print(f"\nMEDIA STATISTICS (out of {total_files} files):")
        print("-" * 50)
        
        if default_image_count > 0:
            print(f"NFTs using default image ({default_image_count}):")
            for nft_name in sorted(default_image_nfts):
                print(f"  - {nft_name}")
        
        if default_animation_url_count > 0:
            print(f"\nNFTs using default animation ({default_animation_url_count}):")
            for nft_name in sorted(default_animation_url_nfts):
                print(f"  - {nft_name}")
        
        if default_external_url_count > 0:
            print(f"\nNFTs using default external_url ({default_external_url_count}):")
            for nft_name in sorted(default_external_url_nfts):
                print(f"  - {nft_name}")
        
        if (default_image_count == 0 and default_animation_url_count == 0 and 
            default_external_url_count == 0):
            print("All NFTs are using asset-specific media files!")
    
    # Log statistics
    if info_count > 0 or warn_count > 0:
        print(f"\n{color_text('ℹ', 'blue')} Log summary: {color_text('[INFO]', 'blue')} {info_count}, {color_text('[WARN]', 'yellow')} {warn_count}")
    # Summary
    if skipped_docs > 0:
        print(f"{color_text('✓', 'green')} Wrote {flattened_docs} flattened JSON files to: {out_dir}")
        print(f"{color_text('⚠', 'yellow')} Skipped {skipped_docs} files due to missing required fields")
    else:
        print(f"{color_text('✓', 'green')} Wrote {flattened_docs} flattened JSON files to: {out_dir}")
    
if __name__ == "__main__":
    main()
