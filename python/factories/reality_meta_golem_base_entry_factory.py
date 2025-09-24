#!/usr/bin/env python3
from pathlib import Path
from typing import List, Union
from ..common.types import FileMetadataDict
from ..common.enums import FileType, MetadataType
from ..common.globals import logger
from ..dataclasses.reality_meta_golem_base_entry import RealityMetaGolemBaseEntry
from ..dataclasses.reality_meta_golem_base_entry_audio import (
    RealityMetaGolemBaseEntryAudio,
)
from ..dataclasses.reality_meta_golem_base_entry_image import (
    RealityMetaGolemBaseEntryImage,
)
from ..dataclasses.reality_meta_golem_base_entry_json import (
    RealityMetaGolemBaseEntryJson,
)
from ..dataclasses.reality_meta_golem_base_entry_text import (
    RealityMetaGolemBaseEntryText,
)
from ..dataclasses.reality_meta_golem_base_entry_video import (
    RealityMetaGolemBaseEntryVideo,
)
from ..utils.file.file_utils import analyze_directory

# Base class used for OTHER
file_type_to_class_mapping = {
    FileType.IMAGE: RealityMetaGolemBaseEntryImage,
    FileType.VIDEO: RealityMetaGolemBaseEntryVideo,
    FileType.AUDIO: RealityMetaGolemBaseEntryAudio,
    FileType.JSON: RealityMetaGolemBaseEntryJson,
    FileType.TEXT: RealityMetaGolemBaseEntryText,
    FileType.OTHER: RealityMetaGolemBaseEntry,
}


def create_reality_meta_golem_base_entry(
    file_type: FileType, data: FileMetadataDict
) -> (
    RealityMetaGolemBaseEntry
    | RealityMetaGolemBaseEntryAudio
    | RealityMetaGolemBaseEntryImage
    | RealityMetaGolemBaseEntryJson
    | RealityMetaGolemBaseEntryText
    | RealityMetaGolemBaseEntryVideo
):
    """
    Create a RealityMetaGolemBaseEntry or a subclass instance based on the FileType.
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")

    if file_type not in file_type_to_class_mapping:
        raise ValueError(f"Unsupported file type: {file_type}")

    entry_class = file_type_to_class_mapping[file_type]

    try:
        return entry_class.create_from_dict(data)
    except Exception as e:
        raise ValueError(f"Failed to create {entry_class.__name__} instance: {str(e)}")


def create_reality_meta_golem_base_entry_from_file_metadata(
    file_metadata: FileMetadataDict,
) -> (
    RealityMetaGolemBaseEntry
    | RealityMetaGolemBaseEntryAudio
    | RealityMetaGolemBaseEntryImage
    | RealityMetaGolemBaseEntryJson
    | RealityMetaGolemBaseEntryText
    | RealityMetaGolemBaseEntryVideo
):
    """
    Create a RealityMetaGolemBaseEntry or a subclass instance from a FileMetadataDict only.
    """
    if not isinstance(file_metadata, dict):
        raise TypeError("file_metadata must be a dictionary")

    # Determine the file type from the metadata
    # TODO: create a utility function for this
    file_type_str = file_metadata.get(MetadataType.SYSTEM, {}).get("file_type")
    if not file_type_str:
        raise ValueError("file_type not found in system metadata")

    try:
        file_type = FileType.from_string(file_type_str)
    except ValueError:
        raise ValueError(f"Invalid file_type: {file_type_str}")

    return create_reality_meta_golem_base_entry(file_type, file_metadata)


def create_reality_meta_golem_base_entries_from_directory(
    directory_path: Union[str, Path],
) -> List[
    RealityMetaGolemBaseEntry
    | RealityMetaGolemBaseEntryAudio
    | RealityMetaGolemBaseEntryImage
    | RealityMetaGolemBaseEntryJson
    | RealityMetaGolemBaseEntryText
    | RealityMetaGolemBaseEntryVideo
]:
    """
    Analyze a directory and create RealityMetaGolemBaseEntry instances or subclasses from the analysis results.
    """
    # Analyze the directory to get file metadata
    file_metadata_list = analyze_directory(directory_path)

    # Create entries from the metadata
    entries = []
    for file_metadata in file_metadata_list:
        try:
            entry = create_reality_meta_golem_base_entry_from_file_metadata(
                file_metadata
            )
            entries.append(entry)
        except Exception as e:
            file_name = file_metadata.get(MetadataType.SYSTEM, {}).get("file_name")
            logger.error(f"Failed to create entry for file: {file_name}. Error: {e}")
            continue

    return entries


# ALIAS
create_rmgb_entry = create_reality_meta_golem_base_entry
create_rmgb_entry_from_file_metadata = (
    create_reality_meta_golem_base_entry_from_file_metadata
)
create_rmgb_entries_from_directory = (
    create_reality_meta_golem_base_entries_from_directory
)
