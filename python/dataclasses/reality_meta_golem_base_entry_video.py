#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Optional, ClassVar
from .reality_meta_golem_base_entry import RealityMetaGolemBaseEntry


@dataclass
class RealityMetaGolemBaseEntryVideo(RealityMetaGolemBaseEntry):
    """
    Specialized RealityMetaGolemBaseEntry for video files.
    Contains additional video-specific metadata.
    """

    GOLEM_BASE_NULL_VALUE: ClassVar[str] = (
        RealityMetaGolemBaseEntry.GOLEM_BASE_NULL_VALUE
    )

    # REQUIRED FIELDS FOR VIDEO
    REQUIRED_FIELDS: ClassVar[dict[str, type]] = {
        "_vid_width": int,
        "_vid_height": int,
        "_vid_codec": str,
        "_vid_frame_rate": int,
        "_vid_duration": int,
        "_vid_format": str,
        "_vid_has_audio": (bool, str),
    }

    # VIDEO-SPECIFIC FIELDS
    # -------------------------------------------
    # REQUIRED FIELDS
    # -------------------------------------------
    _vid_width: int = None  # in pixels
    _vid_height: int = None  # in pixels
    _vid_codec: str = None  # e.g. "h264", "vp9"
    _vid_frame_rate: int = None
    _vid_duration: int = None  # in seconds
    _vid_format: str = None  # e.g. "mov,mp4,m4a,3gp,3g2,mj2"
    _vid_has_audio: bool | str = None  # Whether video has audio track

    # OPTIONAL FIELDS
    # -------------------------------------------
    # e.g. "yuv420p"
    _vid_pixel_format: Optional[str] = GOLEM_BASE_NULL_VALUE
    # e.g. "aac", "mp3"
    _vid_audio_codec: Optional[str] = GOLEM_BASE_NULL_VALUE
    # e.g. 44100
    _vid_audio_sample_rate: Optional[int] = GOLEM_BASE_NULL_VALUE
    # Number of audio channels
    _vid_audio_channels: Optional[int] = GOLEM_BASE_NULL_VALUE
    # Overall bitrate in bits per second
    _vid_bitrate: Optional[int] = GOLEM_BASE_NULL_VALUE

    def get_video_dimensions(self) -> tuple[int, int]:
        """Get video dimensions as (width, height) tuple."""
        width = self._vid_width
        height = self._vid_height
        return (width, height)

    def get_aspect_ratio(self) -> float:
        """Calculate and return the aspect ratio (width/height)."""
        width, height = self.get_video_dimensions()
        if height > 0:
            return width / height
        return 0

    def get_duration_formatted(self) -> str:
        """Get formatted duration as HH:MM:SS string."""
        duration = self._vid_duration
        if duration == 0:
            return "00:00:00"

        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
