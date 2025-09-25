#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Optional, ClassVar
from .reality_meta_golem_base_entity import RealityMetaGolemBaseEntity


@dataclass
class RealityMetaGolemBaseEntityText(RealityMetaGolemBaseEntity):
    """
    Specialized RealityMetaGolemBaseEntity for text files.
    Contains additional text-specific metadata.
    """

    GOLEM_BASE_NULL_VALUE: ClassVar[str] = (
        RealityMetaGolemBaseEntity.GOLEM_BASE_NULL_VALUE
    )

    # REQUIRED FIELDS FOR TEXT
    REQUIRED_FIELDS: ClassVar[dict[str, type]] = {
        "_txt_content": str,
        "_txt_line_count": int,
        "_txt_char_count": int,
        "_txt_word_count": int,
    }

    # TEXT-SPECIFIC FIELDS
    # -------------------------------------------------------------------------
    # REQUIRED FIELDS
    # -------------------------------------------------------------------------
    _txt_content: str = None  # The actual text content
    _txt_line_count: int = None  # Number of lines in the text
    _txt_char_count: int = None  # Total character count
    _txt_word_count: int = None  # Total word count

    # OPTIONAL FIELDS
    # -------------------------------------------------------------------------
    # e.g. "UTF-8", "latin-1", "cp1252", "iso-8859-1"
    _txt_encoding_used: Optional[str] = GOLEM_BASE_NULL_VALUE

    def get_average_line_length(self) -> float:
        """Calculate average characters per line."""
        char_count = self._txt_char_count
        line_count = self._txt_line_count

        if line_count > 0:
            return char_count / line_count
        return 0

    def get_average_word_length(self) -> float:
        """Calculate average characters per word."""
        char_count = self._txt_char_count
        word_count = self._txt_word_count

        if word_count > 0:
            return char_count / word_count
        return 0

    def get_words_per_line(self) -> float:
        """Calculate average words per line."""
        word_count = self._txt_word_count
        line_count = self._txt_line_count

        if line_count > 0:
            return word_count / line_count
        return 0

    def get_text_preview(self, max_chars: int = 100) -> str:
        """Get a preview of the text content (first N characters)."""
        content = self._txt_content
        if len(content) <= max_chars:
            return content

        return content[:max_chars] + "..."
