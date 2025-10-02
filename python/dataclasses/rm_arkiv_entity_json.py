#!/usr/bin/env python3
from dataclasses import dataclass
from typing import ClassVar
from .rm_arkiv_entity import RmArkivEntity


@dataclass
class RmArkivEntityJson(RmArkivEntity):
    """
    Specialized RmArkivEntity for JSON files.
    Contains additional JSON-specific metadata.
    """

    # REQUIRED FIELDS FOR JSON
    REQUIRED_FIELDS: ClassVar[dict[str, type]] = {"_json_is_nft_metadata": (bool, str)}

    # JSON-SPECIFIC FIELDS
    # -------------------------------------------
    _json_is_nft_metadata: bool | str = None
