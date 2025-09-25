#!/usr/bin/env python3

import os
import dotenv

dotenv.load_dotenv()

GOLEM_DB_RPC = "https://reality-games.holesky.golem-base.io/rpc"
GOLEM_DB_WSS = "wss://reality-games.holesky.golem-base.io/rpc/ws"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

BASE64_EXPANSION_FACTOR = 1.34
NFT_METADATA_ATTRIBUTE_PREFIX = "attr_"

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
