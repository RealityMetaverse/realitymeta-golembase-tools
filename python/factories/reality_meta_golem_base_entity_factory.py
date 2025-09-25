#!/usr/bin/env python3
from pathlib import Path
from typing import List, Union
from ..common.types import FileMetadataDict
from ..common.enums import FileType, MetadataType
from ..common.globals import logger
from ..dataclasses.reality_meta_golem_base_entity import RealityMetaGolemBaseEntity
from ..dataclasses.reality_meta_golem_base_entity_audio import (
    RealityMetaGolemBaseEntityAudio,
)
from ..dataclasses.reality_meta_golem_base_entity_image import (
    RealityMetaGolemBaseEntityImage,
)
from ..dataclasses.reality_meta_golem_base_entity_json import (
    RealityMetaGolemBaseEntityJson,
)
from ..dataclasses.reality_meta_golem_base_entity_text import (
    RealityMetaGolemBaseEntityText,
)
from ..dataclasses.reality_meta_golem_base_entity_video import (
    RealityMetaGolemBaseEntityVideo,
)
from ..utils.file.file_utils import analyze_directory

# Base class used for OTHER
file_type_to_class_mapping = {
    FileType.IMAGE: RealityMetaGolemBaseEntityImage,
    FileType.VIDEO: RealityMetaGolemBaseEntityVideo,
    FileType.AUDIO: RealityMetaGolemBaseEntityAudio,
    FileType.JSON: RealityMetaGolemBaseEntityJson,
    FileType.TEXT: RealityMetaGolemBaseEntityText,
    FileType.OTHER: RealityMetaGolemBaseEntity,
}


def create_reality_meta_golem_base_entity(
    file_type: FileType, data: FileMetadataDict
) -> (
    RealityMetaGolemBaseEntity
    | RealityMetaGolemBaseEntityAudio
    | RealityMetaGolemBaseEntityImage
    | RealityMetaGolemBaseEntityJson
    | RealityMetaGolemBaseEntityText
    | RealityMetaGolemBaseEntityVideo
):
    """
    Create a RealityMetaGolemBaseEntity or a subclass instance based on the FileType.
    """
    if not isinstance(data, dict):
        raise TypeError("Data must be a dictionary")

    if file_type not in file_type_to_class_mapping:
        raise ValueError(f"Unsupported file type: {file_type}")

    entity_class = file_type_to_class_mapping[file_type]

    try:
        return entity_class.create_from_dict(data)
    except Exception as e:
        raise ValueError(f"Failed to create {entity_class.__name__} instance: {str(e)}")


def create_reality_meta_golem_base_entity_from_file_metadata(
    file_metadata: FileMetadataDict,
) -> (
    RealityMetaGolemBaseEntity
    | RealityMetaGolemBaseEntityAudio
    | RealityMetaGolemBaseEntityImage
    | RealityMetaGolemBaseEntityJson
    | RealityMetaGolemBaseEntityText
    | RealityMetaGolemBaseEntityVideo
):
    """
    Create a RealityMetaGolemBaseEntity or a subclass instance from a FileMetadataDict only.
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

    return create_reality_meta_golem_base_entity(file_type, file_metadata)


def create_reality_meta_golem_base_entities_from_directory(
    directory_path: Union[str, Path],
) -> List[
    RealityMetaGolemBaseEntity
    | RealityMetaGolemBaseEntityAudio
    | RealityMetaGolemBaseEntityImage
    | RealityMetaGolemBaseEntityJson
    | RealityMetaGolemBaseEntityText
    | RealityMetaGolemBaseEntityVideo
]:
    """
    Analyze a directory and create RealityMetaGolemBaseEntity instances or subclasses from the analysis results.
    """
    # Analyze the directory to get file metadata
    file_metadata_list = analyze_directory(directory_path)

    # Create entities from the metadata
    entities = []
    for file_metadata in file_metadata_list:
        try:
            entity = create_reality_meta_golem_base_entity_from_file_metadata(
                file_metadata
            )
            entities.append(entity)
        except Exception as e:
            file_name = file_metadata.get(MetadataType.SYSTEM, {}).get("file_name")
            logger.error(f"Failed to create entity for file: {file_name}. Error: {e}")
            continue

    return entities


# ALIAS
create_rmgb_entity = create_reality_meta_golem_base_entity
create_rmgb_entity_from_file_metadata = (
    create_reality_meta_golem_base_entity_from_file_metadata
)
create_rmgb_entities_from_directory = (
    create_reality_meta_golem_base_entities_from_directory
)
