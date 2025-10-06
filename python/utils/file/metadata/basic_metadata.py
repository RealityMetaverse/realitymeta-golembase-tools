#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, Any
import mimetypes
from ....common.enums import FileType, MetadataType
from ...data_utils import read_file_as_base64_with_compression


def detect_mime_type(file_path: Path) -> str:
    mime_type = mimetypes.guess_type(str(file_path))[0]

    if mime_type is None:
        return "application/octet-stream"

    return mime_type


def determine_file_type(mime_type: str, extension: str = None) -> str:
    """
    Determine the general file type category based primarily on MIME type.
    Returns the file type string extracted from the first half of the MIME type.
    """
    file_types = FileType.get_all_values()

    file_type_extracted_from_mime_type = mime_type.split("/")[0]
    if file_type_extracted_from_mime_type in file_types:
        return file_type_extracted_from_mime_type

    if extension == ".json":
        return "json"

    return "other"


def extract_basic_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract basic file system metadata with smart compression. Raises exceptions if MIME type detection or file reading fails."""
    stat = file_path.stat()

    mime_type = detect_mime_type(file_path)
    file_type = determine_file_type(mime_type, file_path.suffix.lower())

    # Use smart compression based on file type, with fallback for oversized files
    sys_data, compression_method, compressed_data_size = (
        read_file_as_base64_with_compression(file_path, file_type, stat.st_size)
    )

    return {
        MetadataType.SYSTEM: {
            "file_name": file_path.name,
            "file_stem": file_path.stem,
            "file_extension": file_path.suffix.lstrip("."),
            "file_type": file_type,
            "mime_type": mime_type,
            "file_size": stat.st_size,
            "file_modified_at": int(stat.st_mtime),
            "category": file_path.parent.name,
            "data": sys_data,
            "compression_method": compression_method,
            "compressed_data_size": compressed_data_size,
        }
    }
