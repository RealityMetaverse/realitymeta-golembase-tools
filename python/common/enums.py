#!/usr/bin/env python3
from enum import Enum
from typing import TypeVar, Type


class Encoding(Enum):
    UTF8 = "utf-8"
    ASCII = "ascii"


class NFTMetadataType(Enum):
    STANDARD = "STANDARD"
    REALITY_NFT = "REALITY_NFT"


T = TypeVar("T", bound="BaseStringEnum")


class BaseStringEnum(Enum):
    """
    Base enum class with common string-based enum functionality.
    """

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls: Type[T], value: str) -> T:
        """Create enum instance from string value."""
        value_lower = value.lower()
        for item in cls:
            if item.value == value_lower:
                return item
        raise ValueError(f"Invalid {cls.__name__} value: {value}")

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all possible string values."""
        return [item.value for item in cls]


class SysStatus(BaseStringEnum):
    """
    Enum for RealityMetaGolemBaseEntry sys_status field.
    Representing different environment availability states.
    """

    NONE = "none"
    STAGING = "staging"
    PROD = "prod"
    BOTH = "both"


class MetadataType(BaseStringEnum):
    """
    Enum for metadata types.
    Representing different metadata categories for files.
    """

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    JSON = "json"
    SYSTEM = "system"
    ADDITIONAL = "additional"


class FileType(BaseStringEnum):
    """
    Enum for file types.
    Representing different content types for files.
    """

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    JSON = "json"
    TEXT = "text"
    OTHER = "other"
