#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Optional, ClassVar
from .rm_arkiv_entity import RmArkivEntity


@dataclass
class RmArkivEntityAudio(RmArkivEntity):
    """
    Specialized RmArkivEntity for audio files.
    Contains additional audio-specific metadata.
    """

    ARKIV_NULL_VALUE: ClassVar[str] = (
        RmArkivEntity.ARKIV_NULL_VALUE
    )
    ARKIV_FALSE_VALUE: ClassVar[str] = (
        RmArkivEntity.ARKIV_FALSE_VALUE
    )

    # REQUIRED FIELDS FOR AUDIO
    REQUIRED_FIELDS: ClassVar[dict[str, type]] = {"_aud_duration": int}

    # AUDIO-SPECIFIC FIELDS
    # -------------------------------------------
    # REQUIRED FIELDS
    # -------------------------------------------
    _aud_duration: int = None  # in seconds

    # OPTIONAL FIELDS
    # -------------------------------------------
    _aud_bitrate: Optional[int] = ARKIV_NULL_VALUE  # Bitrate in bits per second
    # e.g. 44100, 48000
    _aud_sample_rate: Optional[int] = ARKIV_NULL_VALUE
    # Number of audio channels (1=mono, 2=stereo)
    _aud_channels: Optional[int] = ARKIV_NULL_VALUE
    # Audio codec type (e.g., "MP3Info", "FLACInfo")
    _aud_codec: Optional[str] = ARKIV_NULL_VALUE
    # e.g. stereo mode for MP3
    _aud_mode: Optional[str] = ARKIV_NULL_VALUE
    # e.g. MPEG version
    _aud_version: Optional[str] = ARKIV_NULL_VALUE
    # Layer information
    _aud_layer: Optional[str] = ARKIV_NULL_VALUE

    def get_duration_formatted(self) -> Optional[str]:
        """Get formatted duration as MM:SS string."""
        duration = self._aud_duration
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        return f"{minutes:02d}:{seconds:02d}"

    def is_stereo(self) -> bool:
        """Check if audio is stereo (2 channels)."""
        return self._aud_channels == 2

    def is_mono(self) -> bool:
        """Check if audio is mono (1 channel)."""
        return self._aud_channels == 1
