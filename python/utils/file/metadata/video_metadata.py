#!/usr/bin/env python3
"""
Video analysis functions for file metadata extraction.
"""

from pathlib import Path
from typing import Dict, Any
import ffmpeg

from ....common.enums import MetadataType


def extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract video-specific metadata. Raises exceptions if extraction fails."""
    probe = ffmpeg.probe(str(file_path))

    vid_metadata = {}

    # Get video stream info
    video_streams = [
        stream for stream in probe["streams"] if stream["codec_type"] == "video"
    ]
    if video_streams:
        video_stream = video_streams[0]

        vid_metadata["width"] = video_stream.get("width")
        vid_metadata["height"] = video_stream.get("height")
        vid_metadata["codec"] = video_stream.get("codec_name")
        vid_metadata["pixel_format"] = video_stream.get("pix_fmt")

        # frame rate is a string like "24/1" or "24000/1001", we want to convert it to an integer
        frame_rate = video_stream.get("r_frame_rate")
        frame_rate_split = frame_rate.split("/")
        vid_metadata["frame_rate"] = int(
            int(frame_rate_split[0]) / int(frame_rate_split[1])
        )

        duration = None
        if "duration" in video_stream:
            duration = float(video_stream["duration"])
        elif "duration" in probe.get("format", {}):
            duration = float(probe["format"]["duration"])

        vid_metadata["duration"] = int(round(duration, 2))

    # Get audio stream info if present
    audio_streams = [
        stream for stream in probe["streams"] if stream["codec_type"] == "audio"
    ]
    if audio_streams:
        audio_stream = audio_streams[0]
        vid_metadata["has_audio"] = True
        vid_metadata["audio_codec"] = audio_stream.get("codec_name")
        vid_metadata["audio_sample_rate"] = audio_stream.get("sample_rate")
        vid_metadata["audio_channels"] = audio_stream.get("channels")
    else:
        vid_metadata["has_audio"] = False

    # Format info
    format_info = probe.get("format", {})
    vid_metadata["format"] = format_info.get("format_name")
    vid_metadata["bitrate"] = format_info.get("bit_rate")

    return {MetadataType.VIDEO: vid_metadata}
