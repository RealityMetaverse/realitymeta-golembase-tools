#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, Any

from ....common.enums import Encoding
from ....common.enums import MetadataType
from ....utils.data_utils import is_nft_metadata_attribute_field
from ....common.config import (
    NFT_METADATA_ATTRIBUTE_PREFIX,
    REALITY_NFT_CONVERTED_METADATA_REQUIRED_FIELDS,
)


# TODO: fix circular import
def _get_media_stats():
    """Lazy load media_stats to avoid circular import."""
    from ....common.globals import media_stats

    return media_stats


def extract_json_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract JSON file content and metadata. Raises exceptions if extraction fails."""
    with file_path.open("r", encoding=Encoding.UTF8.value) as f:
        json_data = json.load(f)

    json_metadata = {"is_nft_metadata": False}
    attributes = None

    if "attributes" in json_data and is_nft_metadata_attribute_field(
        json_data["attributes"]
    ):
        json_metadata["is_nft_metadata"] = True

        # attributes deleted to be added to additional_metadata separately
        attributes = json_data["attributes"]
        del json_data["attributes"]

    if attributes:
        for key in json_data.keys():
            if key.startswith(NFT_METADATA_ATTRIBUTE_PREFIX):
                raise ValueError(
                    f"No field can start with '{NFT_METADATA_ATTRIBUTE_PREFIX}' in an NFT metadata. Field: {key}"
                )

        for attribute in attributes:
            json_data[f"{NFT_METADATA_ATTRIBUTE_PREFIX}{attribute['trait_type']}"] = (
                attribute["value"]
            )

    # TODO: think of a better way to check if the metadata is a Reality NFT metadata
    if "license" in json_data and "realitymeta" in json_data["license"]:
        for field in REALITY_NFT_CONVERTED_METADATA_REQUIRED_FIELDS:
            if field not in json_data:
                raise ValueError(
                    f"Field '{field}' is required in a Reality NFT metadata."
                )

        # Check media URL file_basename matches for Reality NFT metadata
        file_basename_stem = file_path.stem
        media_stats = _get_media_stats()
        for k, v in json_data.items():
            if k in ["image", "animation_url", "external_url"]:
                media_stats.check_and_record_media_url_match(v, file_basename_stem, k)

    return {
        MetadataType.ADDITIONAL: json_data,
        MetadataType.JSON: json_metadata,
    }
