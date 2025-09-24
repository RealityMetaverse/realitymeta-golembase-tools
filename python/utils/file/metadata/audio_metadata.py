#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, Any
from mutagen import File as MutagenFile

from ....common.enums import MetadataType


def extract_audio_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract audio-specific metadata. Raises exceptions if extraction fails."""
    audio_file = MutagenFile(str(file_path))

    if audio_file is None:
        raise RuntimeError(f"Could not read audio file: {file_path.name}")

    aud_metadata = {}

    if hasattr(audio_file, "info"):
        info = audio_file.info
        aud_metadata["codec"] = type(info).__name__

        if hasattr(info, "length"):
            aud_metadata["duration"] = info.length

        if hasattr(info, "bitrate"):
            aud_metadata["bitrate"] = info.bitrate

        if hasattr(info, "sample_rate"):
            aud_metadata["sample_rate"] = info.sample_rate

        if hasattr(info, "channels"):
            aud_metadata["channels"] = info.channels

        if hasattr(info, "mode"):
            aud_metadata["mode"] = info.mode

        if hasattr(info, "version"):
            aud_metadata["version"] = info.version

        if hasattr(info, "layer"):
            aud_metadata["layer"] = info.layer

    if hasattr(audio_file, "tags"):
        aud_metadata["tags"] = audio_file.tags

    return {MetadataType.AUDIO: aud_metadata}
