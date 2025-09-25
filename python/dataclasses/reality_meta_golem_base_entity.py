#!/usr/bin/env python3
import json
from dataclasses import dataclass, fields, field
from pathlib import Path
from typing import Optional, List, ClassVar, Any
from ..common.enums import MetadataType, SysStatus
from ..common.types import FileMetadataDict
from ..common.config import BASE64_EXPANSION_FACTOR
from ..utils.data_utils import (
    generate_content_hash,
    is_field_none_or_empty_string,
    write_base64_to_file,
)
from ..utils.golem_base_utils import create_golem_base_entity_annotations


@dataclass
class RealityMetaGolemBaseEntity:
    """
    Dataclass for system fields only.
    Fields become read-only after initialization.
    """

    # CONFIGURATION
    # -------------------------------------------
    VERSION: ClassVar[int] = 1
    # DEV: Golem Base max entity size is 140KB
    # DEV: 10KB is reserved for metadata
    # TODO: 10KB might be too much or too little, the precise amount needs to be determined
    GOLEM_BASE_MAX_ENTRY_SIZE: ClassVar[int] = 140 * 1024  # in bytes
    RESERVED_SPACE_FOR_METADATA: ClassVar[int] = 10 * 1024  # in bytes
    MAX_FILE_SIZE: ClassVar[int] = (
        GOLEM_BASE_MAX_ENTRY_SIZE - RESERVED_SPACE_FOR_METADATA
    )

    GOLEM_BASE_NULL_VALUE: ClassVar[str] = "null"
    GOLEM_BASE_TRUE_VALUE: ClassVar[str] = "true"
    GOLEM_BASE_FALSE_VALUE: ClassVar[str] = "false"

    GOLEM_BASE_VALUES: ClassVar[dict[Any, str]] = {
        None: GOLEM_BASE_NULL_VALUE,
        True: GOLEM_BASE_TRUE_VALUE,
        False: GOLEM_BASE_FALSE_VALUE,
    }

    SYSTEM_FIELDS_PREFIX: ClassVar[str] = "_sys_"
    IMAGE_METADATA_PREFIX: ClassVar[str] = "_img_"
    AUDIO_METADATA_PREFIX: ClassVar[str] = "_aud_"
    VIDEO_METADATA_PREFIX: ClassVar[str] = "_vid_"
    TEXT_METADATA_PREFIX: ClassVar[str] = "_txt_"
    JSON_METADATA_PREFIX: ClassVar[str] = "_json_"

    METADATA_PREFIXES: ClassVar[dict[MetadataType, str]] = {
        MetadataType.IMAGE: IMAGE_METADATA_PREFIX,
        MetadataType.AUDIO: AUDIO_METADATA_PREFIX,
        MetadataType.VIDEO: VIDEO_METADATA_PREFIX,
        MetadataType.TEXT: TEXT_METADATA_PREFIX,
        MetadataType.SYSTEM: SYSTEM_FIELDS_PREFIX,
        MetadataType.JSON: JSON_METADATA_PREFIX,
    }

    # Conversion prefixes for identifying converted data types
    CONVERTED_LIST_PREFIX: ClassVar[str] = "__list__:"
    CONVERTED_DICT_PREFIX: ClassVar[str] = "__dict__:"

    # DEV: checksum is being calculated according to metadata fields + additional_fields excluding fields in this list
    ENTRY_CHECKSUM_IGNORED_FIELDS: ClassVar[List[str]] = [
        "_sys_version",
        "_sys_file_checksum",
        "_sys_entity_checksum",
        "_sys_modified_at",
    ]
    # DEV: in addition to ENTRY_CHECKSUM_IGNORED_FIELDS
    FILE_CHECKSUM_IGNORED_FIELDS: ClassVar[List[str]] = [
        "_sys_field_names",
        "_sys_parent_file_name",
        "_sys_category",
        "_sys_tags",
    ]

    # SYSTEM FIELDS
    # -------------------------------------------
    # REQUIRED FIELDS
    # ---------------------------------------------
    # File metadata
    _sys_file_name: str  # e.g. "example.png"
    _sys_file_stem: str  # e.g. "example"
    _sys_file_extension: str  # e.g. "png"
    _sys_file_type: str  # FileType enum
    _sys_mime_type: str  # e.g. "image/png"
    _sys_file_size: int  # in bytes
    _sys_file_modified_at: int  # Unix timestamp in seconds

    # Classification & integrity
    _sys_category: str

    # OPTIONAL FIELDS
    # ---------------------------------------------
    # Versioning & lifecycle
    _sys_version: Optional[int] = VERSION
    _sys_status: Optional[str] = SysStatus.BOTH.value  # TODO: add validation

    # Data
    _sys_data: Optional[str] = GOLEM_BASE_NULL_VALUE  # Base64 encoded string

    # Chunking
    # TODO: will be implemented later with chunking
    # NOTE: Optional will be removed later
    _sys_total_chunks: Optional[int] = 1
    _sys_chunk_index: Optional[int] = 1

    # Classification & integrity
    # TODO: to be implemented later with parent-child relationships
    _sys_parent_file_name: Optional[str] = GOLEM_BASE_NULL_VALUE
    _sys_tags: Optional[list[str] | str] = GOLEM_BASE_NULL_VALUE
    # DEV: following fields are created in __post_init__
    # NOTE: requires CONVERTED_LIST_PREFIX
    _sys_field_names: Optional[str] = GOLEM_BASE_NULL_VALUE
    # DEV: for checking if the entity is already stored in the database
    _sys_entity_checksum: Optional[str] = GOLEM_BASE_NULL_VALUE
    # DEV: for checking if the file is already stored with different metadata
    # TODO: however similar thing can be archived by using _sys_data, decide if this is needed
    _sys_file_checksum: Optional[str] = GOLEM_BASE_NULL_VALUE

    # FILE CONTENT
    # -------------------------------------------
    # DEV: right now it can override system fields
    # TODO: prevent overriding system fields
    additional_fields: Optional[dict[str, str | int] | str] = GOLEM_BASE_NULL_VALUE

    def get_metadata_field_names(self) -> List[str]:
        """Get the names of all metadata fields."""
        metadata_prefixes = tuple(self.METADATA_PREFIXES.values())
        return [
            field.name
            for field in fields(self)
            if field.name.startswith(metadata_prefixes)
        ]

    def create_checksums(self) -> tuple[str, str]:
        """Create file and entity checksums."""
        entity_checksum_ignored_fields_set = set(self.ENTRY_CHECKSUM_IGNORED_FIELDS)
        file_checksum_ignored_fields_set = (
            set(self.FILE_CHECKSUM_IGNORED_FIELDS) | entity_checksum_ignored_fields_set
        )

        metadata_prefixes = tuple(self.METADATA_PREFIXES.values())

        # Initialize with additional fields if they exist
        entity_checksum_data = {}
        file_checksum_data = {}

        if isinstance(self.additional_fields, dict) and len(self.additional_fields) > 0:
            entity_checksum_data = self.additional_fields.copy()
            file_checksum_data = entity_checksum_data.copy()

        for field in fields(self):
            if field.name.startswith(metadata_prefixes):
                field_value = self.__dict__.get(field.name)

                if field.name not in entity_checksum_ignored_fields_set:
                    entity_checksum_data[field.name] = field_value
                if field.name not in file_checksum_ignored_fields_set:
                    file_checksum_data[field.name] = field_value

        entity_checksum = generate_content_hash(entity_checksum_data)
        file_checksum = generate_content_hash(file_checksum_data)

        return entity_checksum, file_checksum

    # DEV: __setattr__ makes sure fields not asisgned None or empty string, however we still need to validate to make sure all fields are set
    def validate_system_fields(self) -> None:
        """
        Validate that all system fields are present and not empty.
        Raises ValueError if any field is None or empty string.
        """
        invalid_fields = []

        for field in fields(self):
            field_value = self.__dict__.get(field.name)
            is_invalid, error_message = is_field_none_or_empty_string(
                field_value, field.name
            )
            if is_invalid:
                invalid_fields.append(error_message)

        if invalid_fields:
            raise ValueError(
                f"Invalid fields after initialization: {', '.join(invalid_fields)}"
            )

    def validate_required_fields(self) -> None:
        """
        Validate that all required fields are present, not empty, and have correct types.
        """
        if not hasattr(self, "REQUIRED_FIELDS"):
            return

        invalid_fields = []

        for field_name, expected_type in self.REQUIRED_FIELDS.items():
            if not hasattr(self, field_name):
                invalid_fields.append(f"'{field_name}' is missing")
                continue

            field_value = self.__dict__.get(field_name)
            is_invalid, error_message = is_field_none_or_empty_string(
                field_value, field_name
            )
            if is_invalid:
                invalid_fields.append(error_message)

            if not isinstance(field_value, expected_type):
                invalid_fields.append(
                    f"'{field_name}' has incorrect type: {type(field_value)}. Expected type: {expected_type}"
                )

        if invalid_fields:
            raise ValueError(
                f"Required fields validation failed: {', '.join(invalid_fields)}"
            )

    def convert_to_golem_base_value(self, value: Any) -> str | int:
        """
        Converts values to golem base values.
        """
        # to prevent convertion 1 -> 'true' and 0 -> 'false'
        if isinstance(value, int):
            return value

        # bool -> string
        # None -> string
        try:
            if value in self.GOLEM_BASE_VALUES:
                return self.GOLEM_BASE_VALUES[value]
        except TypeError:
            pass

        # float -> string
        if isinstance(value, float):
            return str(value)

        # list -> string
        if isinstance(value, list):
            if len(value) == 0:
                return self.GOLEM_BASE_NULL_VALUE
            else:
                return self.CONVERTED_LIST_PREFIX + json.dumps(
                    value, ensure_ascii=False
                )

        # dict -> string
        if isinstance(value, dict):
            if len(value) == 0:
                return self.GOLEM_BASE_NULL_VALUE
            else:
                return self.CONVERTED_DICT_PREFIX + json.dumps(
                    value, ensure_ascii=False
                )

        # empty string -> golem base null value
        if isinstance(value, str) and value.strip() == "":
            return self.GOLEM_BASE_NULL_VALUE

        return value

    def __setattr__(self, name: str, value) -> None:
        """
        Set if not initialized, or during initialization.
        """
        # Allow setting during initialization
        if not hasattr(self, "_initialized") or name == "_initialized":
            if name != "additional_fields":
                value = self.convert_to_golem_base_value(value)
            else:
                if isinstance(value, dict):
                    value = {
                        k: self.convert_to_golem_base_value(v) for k, v in value.items()
                    }
                else:
                    value = self.GOLEM_BASE_NULL_VALUE

            super().__setattr__(name, value)
            return

    def __post_init__(self):
        # Fields that are not allowed to be set by user
        self._sys_version = self.VERSION
        self._sys_field_names = [f.name for f in fields(self)]
        self._sys_entity_checksum, self._sys_file_checksum = self.create_checksums()

        # Validate that all required fields are present and not empty
        self.validate_required_fields()
        # Validate that all fields are not None or empty after initialization
        self.validate_system_fields()

        if self._sys_file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size is too large: {self._sys_file_size} bytes, max is {self.MAX_FILE_SIZE} bytes"
            )

        file_size_with_expansion_factor = self._sys_file_size * BASE64_EXPANSION_FACTOR
        if file_size_with_expansion_factor > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size is too large with expansion factor: {file_size_with_expansion_factor} bytes, max is {self.MAX_FILE_SIZE} bytes"
            )

        # Mark initialization as complete - fields are now read-only
        object.__setattr__(self, "_initialized", True)

    def get_raw_value(self, name: str) -> Any:
        """Get the raw value of a field."""
        return object.__getattribute__(self, name)

    def __getattribute__(self, name: str):
        """
        Convert golem base values back to original types.
        """
        # Get the actual value first using the parent's __getattribute__
        value = super().__getattribute__(name)

        # Skip conversion during initialization to avoid recursion
        # Use object.__getattribute__ to avoid calling our own __getattribute__
        try:
            initialized = object.__getattribute__(self, "_initialized")
            if not initialized:
                return value
        except AttributeError:
            # _initialized doesn't exist yet, so we're still initializing
            return value

        # int -> int
        # to prevent convertion 'true' -> 1 and 'false' -> 0
        if isinstance(value, int):
            return value

        # Convert golem base values back to original types
        golem_base_values = object.__getattribute__(self, "GOLEM_BASE_VALUES")
        reversed_dict = {v: k for k, v in golem_base_values.items()}
        try:
            if value in reversed_dict:
                return reversed_dict[value]
        except TypeError:
            # Value is unhashable (dict, list, etc.), skip this conversion
            pass

        # string float -> float
        if isinstance(value, str) and ("+" in value or "-" in value or "." in value):
            try:
                return float(value)
            except ValueError:
                pass

        # stringified list -> list
        converted_list_prefix = object.__getattribute__(self, "CONVERTED_LIST_PREFIX")
        if isinstance(value, str) and value.startswith(converted_list_prefix):
            return json.loads(value[len(converted_list_prefix) :])

        # stringified dict -> dict
        converted_dict_prefix = object.__getattribute__(self, "CONVERTED_DICT_PREFIX")
        if isinstance(value, str) and value.startswith(converted_dict_prefix):
            return json.loads(value[len(converted_dict_prefix) :])

        # For null values, return None instead of the string representation
        golem_base_null_value = object.__getattribute__(self, "GOLEM_BASE_NULL_VALUE")
        if value == golem_base_null_value:
            return None

        return value

    def to_dict(self) -> dict:
        """Convert the dataclass to a dictionary with golem base values converted back to original types."""

        result = {}
        for field in fields(self):
            # This will go through __getattribute__
            result[field.name] = getattr(self, field.name)

        return result

    @classmethod
    def create_from_dict(
        cls,
        file_metadata: FileMetadataDict,
    ) -> "RealityMetaGolemBaseEntity":
        """
        Create an instance from a FileMetadataDict.

        The FileMetadataDict has a nested structure like:
        {
            "sys": {"file_name": "example.png", "file_size": 1024, ...},
            "img": {"width": 800, "height": 600, ...},
            "txt": {...},
            "aud": {...},
            "vid": {...}
        }

        This method flattens it to match the dataclass field names with prefixes:
        {
            "_sys_file_name": "example.png",
            "_sys_file_size": 1024,
            "_img_width": 800,
            "_img_height": 600,
            ...
        }

        Raises ValueError if required fields are missing or invalid metadata types are provided.
        """
        if not isinstance(file_metadata, dict):
            raise ValueError("file_metadata must be a dictionary")

        # Extract necessary metadata types
        valid_metadata_types_str = [
            metadata_type.value for metadata_type in cls.METADATA_PREFIXES.keys()
        ]

        filtered_metadata = {}
        additional_fields = {}

        for metadata_type, metadata_dict in file_metadata.items():
            metadata_type_str = metadata_type.value
            if metadata_type_str == MetadataType.ADDITIONAL.value:
                additional_fields = metadata_dict
                continue

            if metadata_type_str not in valid_metadata_types_str:
                # TODO: log unused metadata types
                continue

            if not isinstance(metadata_dict, dict):
                raise ValueError(
                    f"Metadata for type '{metadata_type_str}' must be a dictionary"
                )

            prefix = cls.METADATA_PREFIXES[metadata_type]

            for key, value in metadata_dict.items():
                field_name = f"{prefix}{key}"
                filtered_metadata[field_name] = value

        # Add additional_fields to flattened_data
        if len(additional_fields) > 0:
            filtered_metadata["additional_fields"] = additional_fields

        return cls(**filtered_metadata)

    def to_golem_base_entity(
        self,
    ) -> tuple[str, List[Any], List[Any]]:
        """
        Create entity data and annotations from metadata fields and additional fields.
        """
        # Create entity data as a string with only the essential fields
        entity_data = f"{self._sys_category} | {self._sys_file_stem} | {self._sys_file_extension} | {self._sys_file_type} | {self._sys_file_size}"

        # Get all metadata fields for annotations
        metadata_field_names = self.get_metadata_field_names()
        metadata_fields = {}

        for field_name in metadata_field_names:
            field_value = self.__dict__.get(field_name)
            metadata_fields[field_name] = field_value

        # Convert metadata fields to annotations
        metadata_string_annotations, metadata_number_annotations = (
            create_golem_base_entity_annotations(metadata_fields)
        )

        # Convert additional fields to annotations if they exist
        additional_string_annotations = []
        additional_number_annotations = []

        if isinstance(self.additional_fields, dict) and len(self.additional_fields) > 0:
            additional_string_annotations, additional_number_annotations = (
                create_golem_base_entity_annotations(self.additional_fields)
            )

        # Merge all annotations
        all_string_annotations = (
            metadata_string_annotations + additional_string_annotations
        )
        all_number_annotations = (
            metadata_number_annotations + additional_number_annotations
        )

        return entity_data, all_string_annotations, all_number_annotations

    @classmethod
    def from_golem_base_entity(
        cls,
        golem_base_entity,
    ) -> "RealityMetaGolemBaseEntity":
        """
        Create a RealityMetaGolemBaseEntity instance from a Golem Base entity.
        Raises: ValueError: If required fields are missing or invalid
        """
        # Combine all annotations into a single dictionary
        all_annotations = {}

        # Process string annotations
        for annotation in golem_base_entity.string_annotations:
            all_annotations[annotation.name] = annotation.value

        # Process number annotations
        for annotation in golem_base_entity.number_annotations:
            all_annotations[annotation.name] = annotation.value

        # Separate metadata fields from additional fields
        metadata_fields = {}
        additional_fields = {}

        # Get all valid metadata prefixes
        metadata_prefixes = tuple(cls.METADATA_PREFIXES.values())

        for field_name, field_value in all_annotations.items():
            if field_name.startswith(metadata_prefixes):
                metadata_fields[field_name] = field_value
            else:
                # This is an additional field
                additional_fields[field_name] = field_value

        # Add additional_fields to metadata_fields if any exist
        if additional_fields:
            metadata_fields["additional_fields"] = additional_fields

        # Create the instance
        return cls(**metadata_fields)

    def recreate_file(
        self, output_dir: Path | str, organize_by_category: bool = False
    ) -> Path:
        """
        Recreate a file from this RealityMetaGolemBaseEntity instance.
        """
        # Convert to Path object if it's a string
        output_dir = Path(output_dir)

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Construct output file path
        if organize_by_category:
            output_file_path = output_dir / self._sys_category / self._sys_file_name
            # Ensure the category subdirectory exists
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_file_path = output_dir / self._sys_file_name

        # Recreate the file
        write_base64_to_file(self._sys_data, output_file_path)

        return output_file_path
