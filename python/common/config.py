#!/usr/bin/env python3

import os
import dotenv
from .enums import CompressionMethod, FileType

dotenv.load_dotenv()

ARKIV_RPC = "https://reality-games.hoodi.arkiv.network/rpc"
ARKIV_WSS = "wss://reality-games.hoodi.arkiv.network/rpc/ws"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

BASE64_EXPANSION_FACTOR = 1.34
NFT_METADATA_ATTRIBUTE_PREFIX = "attr_"

# Compression strategy for oversized files (over MAX_FILE_SIZE after BASE64 expansion)
# Only JSON, text, and other files get compressed when oversized
OVERSIZED_FILE_COMPRESSION_STRATEGY = {
    FileType.JSON: CompressionMethod.GZIP,  # Gzip for oversized JSON files
    FileType.TEXT: CompressionMethod.GZIP,  # Gzip for oversized text files
    FileType.IMAGE: CompressionMethod.NONE,  # No compression for images (already compressed)
    FileType.VIDEO: CompressionMethod.NONE,  # No compression for videos (already compressed)
    FileType.AUDIO: CompressionMethod.NONE,  # No compression for audio (already compressed)
    FileType.OTHER: CompressionMethod.GZIP,  # Gzip for oversized other files
}

REALITY_NFT_CONVERTED_METADATA_REQUIRED_FIELDS = {
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
}
