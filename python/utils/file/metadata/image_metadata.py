#!/usr/bin/env python3
from pathlib import Path
from typing import Dict, Any
from PIL import Image
from ....common.enums import MetadataType


def extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract image-specific metadata. Raises exceptions if extraction fails."""
    with Image.open(file_path) as img:
        return {
            MetadataType.IMAGE: {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "palette": img.palette,
                "has_alpha": getattr(img, "has_transparency_data", False),
                "n_frames": getattr(img, "n_frames", 1),
            }
        }
