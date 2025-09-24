#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, Any

from ....common.enums import Encoding
from ....common.enums import MetadataType


def extract_text_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract text file content and metadata. Raises exceptions if extraction fails."""
    text_content = None
    txt_metadata = {}

    try:
        with file_path.open("r", encoding=Encoding.UTF8.value) as f:
            text_content = f.read()
    except UnicodeDecodeError:
        # Try with different encodings
        for encoding in ["latin-1", "cp1252", "iso-8859-1"]:
            try:
                with file_path.open("r", encoding=encoding) as f:
                    text_content = f.read()
                txt_metadata["encoding_used"] = encoding
                break
            except UnicodeDecodeError:
                continue
        else:
            # If all encodings fail, raise error
            raise UnicodeDecodeError(
                "utf-8",
                b"",
                0,
                0,
                "Could not decode text file with any supported encoding",
            )

    txt_metadata["content"] = text_content
    txt_metadata["line_count"] = text_content.count("\n") + 1
    txt_metadata["char_count"] = len(text_content)
    txt_metadata["word_count"] = len(text_content.split())

    # Check if it's empty
    txt_metadata["is_empty"] = len(text_content.strip()) == 0

    return {MetadataType.TEXT: txt_metadata}
