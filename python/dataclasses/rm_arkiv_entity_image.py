#!/usr/bin/env python3
from dataclasses import dataclass
from typing import Optional, ClassVar
from .rm_arkiv_entity import RmArkivEntity


@dataclass
class RmArkivEntityImage(RmArkivEntity):
    """
    Specialized RmArkivEntity for image files.
    Contains additional image-specific metadata.
    """

    ARKIV_NULL_VALUE: ClassVar[str] = (
        RmArkivEntity.ARKIV_NULL_VALUE
    )
    ARKIV_FALSE_VALUE: ClassVar[str] = (
        RmArkivEntity.ARKIV_FALSE_VALUE
    )

    # REQUIRED FIELDS FOR IMAGE
    REQUIRED_FIELDS: ClassVar[dict[str, type]] = {
        "_img_width": int,
        "_img_height": int,
        "_img_format": str,
    }

    # IMAGE-SPECIFIC FIELDS
    # --------------------------------------------
    # REQUIRED FIELDS
    # --------------------------------------------
    _img_width: int = None  # in pixels
    _img_height: int = None  # in pixels
    _img_format: str = None  # e.g. "PNG", "JPEG"
    _img_has_alpha: bool | str = None

    # OPTIONAL FIELDS
    # --------------------------------------------
    # e.g. "RGB", "RGBA", "L"
    _img_mode: Optional[str] = ARKIV_NULL_VALUE
    _img_palette: Optional[str] = ARKIV_NULL_VALUE
    # Number of frames (for animated images like GIFs)
    _img_n_frames: Optional[int] = 1

    def get_image_dimensions(self) -> tuple[int, int]:
        """Get image dimensions as (width, height) tuple."""
        return (self._img_width, self._img_height)

    def get_aspect_ratio(self) -> float:
        """Calculate and return the aspect ratio (width/height)."""
        width, height = self.get_image_dimensions()
        if height > 0:
            return width / height
        return 0

    def is_animated(self) -> bool:
        """Check if this is an animated image (multiple frames)."""
        return self._img_n_frames > 1
