#!/usr/bin/env python3
from typing import Union
from .enums import MetadataType

# File metadata types
FileMetadataValue = Union[str, int, bool, float, list, dict]
FileMetadataDict = dict[MetadataType, dict[str, FileMetadataValue]]
