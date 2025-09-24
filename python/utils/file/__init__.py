#!/usr/bin/env python3
from .file_utils import (
    analyze_file,
    analyze_directory,
    analyze_directory_comprehensive,
    save_results_to_json,
)

from .metadata.basic_metadata import (
    detect_mime_type,
    determine_file_type,
    extract_basic_metadata,
)
from ..data_utils import read_file_as_base64, write_base64_to_file

from .metadata.image_metadata import extract_image_metadata
from .metadata.video_metadata import extract_video_metadata
from .metadata.audio_metadata import extract_audio_metadata
from .metadata.json_metadata import extract_json_metadata
from .metadata.text_metadata import extract_text_metadata

__all__ = [
    # Main analysis functions
    "analyze_file",
    "analyze_directory",
    "analyze_directory_comprehensive",
    "save_results_to_json",
    # Basic metadata functions
    "detect_mime_type",
    "determine_file_type",
    "read_file_as_base64",
    "write_base64_to_file",
    "extract_basic_metadata",
    # Type-specific analysis functions
    "extract_image_metadata",
    "extract_video_metadata",
    "extract_audio_metadata",
    "extract_json_metadata",
    "extract_text_metadata",
]
