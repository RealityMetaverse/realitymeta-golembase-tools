#!/usr/bin/env python3
import json
from pathlib import Path
from typing import List, Any, Union, Optional
from ...common.enums import FileType, MetadataType, Encoding
from ...common.types import FileMetadataDict
from .metadata.basic_metadata import extract_basic_metadata
from .metadata.image_metadata import extract_image_metadata
from .metadata.video_metadata import extract_video_metadata
from .metadata.audio_metadata import extract_audio_metadata
from .metadata.json_metadata import extract_json_metadata
from .metadata.text_metadata import extract_text_metadata


# TODO: fix circular dependency
def _get_logger():
    """Lazy load logger to avoid circular dependency."""
    from ...common.globals import logger

    return logger


def analyze_file(file_path: Union[str, Path]) -> FileMetadataDict:
    """
    Analyze a single file.
    Extracts basic filesystem metadata and type-specific metadata based on the file's MIME type.
    Raises exceptions if the file cannot be analyzed.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Start with basic metadata
    metadata = extract_basic_metadata(file_path)
    if metadata.get(MetadataType.SYSTEM, {}).get("file_size") <= 0:
        raise ValueError(f"Skipping file with size 0: {file_path.name}")

    file_type_str = metadata[MetadataType.SYSTEM]["file_type"]

    # Extract type-specific metadata based on determined file type
    # Using FileType enum values for comparison
    if file_type_str == FileType.IMAGE.value:
        metadata.update(extract_image_metadata(file_path))
    elif file_type_str == FileType.VIDEO.value:
        metadata.update(extract_video_metadata(file_path))
    elif file_type_str == FileType.AUDIO.value:
        metadata.update(extract_audio_metadata(file_path))
    elif file_type_str == FileType.JSON.value:
        metadata.update(extract_json_metadata(file_path))
    elif file_type_str == FileType.TEXT.value:
        text_metadata = extract_text_metadata(file_path)
        # Skip file if text content is empty
        if text_metadata.get(MetadataType.TEXT, {}).get("is_empty", False):
            raise ValueError(f"Skipping file with empty text content: {file_path.name}")
        metadata.update(text_metadata)

    return metadata


def analyze_directory(directory_path: Union[str, Path]) -> List[FileMetadataDict]:
    """
    Analyze files in immediate subdirectories (depth = 1).
    """
    dir_path = Path(directory_path)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory does not exist: {dir_path}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {dir_path}")

    results: List[FileMetadataDict] = []
    files: List[Path] = []
    skipped_count = 0

    for subdir in dir_path.iterdir():
        if subdir.is_dir():
            subdir_files = [f for f in subdir.glob("*") if f.is_file()]
            files.extend(subdir_files)

    _get_logger().info(f"Found {len(files)} files to analyze in {dir_path}")

    for file_path in files:
        try:
            file_data = analyze_file(file_path)
            results.append(file_data)
            _get_logger().info(f"Analyzed: {file_path.name}")
        except Exception as e:
            skipped_count += 1
            _get_logger().error(f"Error analyzing {file_path.name}: {e}")

    _get_logger().info(
        f"Analysis complete: {len(results)} files processed, {skipped_count} files skipped"
    )
    return results


def save_results_to_json(
    results: List[FileMetadataDict], output_path: Union[str, Path]
) -> None:
    """Save analysis results to a JSON file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding=Encoding.UTF8.value) as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    _get_logger().info(f"File metadata results saved to: {output_path}")


def analyze_directory_comprehensive(
    directory_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> List[FileMetadataDict]:
    """
    Convenience function to analyze a directory and optionally save results.
    """
    results: List[FileMetadataDict] = analyze_directory(directory_path)

    if output_path:
        save_results_to_json(results, output_path)

    return results
