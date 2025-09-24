"""
Reality NFT utilities for media URL validation and statistics tracking.
"""

from typing import List
from pathlib import Path


def extract_file_basename_stem_from_url(url: str) -> str:
    """Extract the basename stem from a URL."""
    return Path(url).stem


class RealityNFTMediaStatistics:
    """Class to track media statistics for Reality NFT metadata."""

    def __init__(self):
        # Total files processed counter
        self.total_files = 0

        # Media statistics counters
        self.default_image_count = 0
        self.default_animation_url_count = 0
        self.default_external_url_count = 0

        # Lists to store NFT names using default media
        self.default_image_nfts: List[str] = []
        self.default_animation_url_nfts: List[str] = []
        self.default_external_url_nfts: List[str] = []

    def reset(self):
        """Reset all counters and lists."""
        self.total_files = 0
        self.default_image_count = 0
        self.default_animation_url_count = 0
        self.default_external_url_count = 0
        self.default_image_nfts.clear()
        self.default_animation_url_nfts.clear()
        self.default_external_url_nfts.clear()

    def check_and_record_media_url_match(
        self, url: str, file_basename_stem: str, field_name: str
    ) -> None:
        """
        Check if the base filename extracted from URL matches the base filename of the file.
        If it doesn't match, record the NFT as using a default/generic media file.
        Increments total_files counter each time this method is called.

        Args:
            url: The media URL to check
            file_basename_stem: The NFT metadata filename base stem
            field_name: The field name (image, animation_url, external_url)
        """
        # Increment total files counter each time this method is called
        self.total_files += 1

        expected_name = file_basename_stem
        actual_filename = extract_file_basename_stem_from_url(url)

        if actual_filename != expected_name:
            if field_name == "image":
                self.default_image_count += 1
                self.default_image_nfts.append(expected_name)
            elif field_name == "animation_url":
                self.default_animation_url_count += 1
                self.default_animation_url_nfts.append(expected_name)
            elif field_name == "external_url":
                self.default_external_url_count += 1
                self.default_external_url_nfts.append(expected_name)

    def print_statistics_report(self) -> None:
        """
        Print a comprehensive media statistics report using the internal total_files counter.
        """
        total_default_count = (
            self.default_image_count
            + self.default_animation_url_count
            + self.default_external_url_count
        )

        if total_default_count > 0:
            print(f"\nMEDIA STATISTICS (out of {self.total_files} files):")
            print("-" * 50)

            if self.default_image_count > 0:
                print(f"NFTs using default image ({self.default_image_count}):")
                for nft_name in sorted(self.default_image_nfts):
                    print(f"  - {nft_name}")

            if self.default_animation_url_count > 0:
                print(
                    f"\nNFTs using default animation ({self.default_animation_url_count}):"
                )
                for nft_name in sorted(self.default_animation_url_nfts):
                    print(f"  - {nft_name}")

            if self.default_external_url_count > 0:
                print(
                    f"\nNFTs using default external_url ({self.default_external_url_count}):"
                )
                for nft_name in sorted(self.default_external_url_nfts):
                    print(f"  - {nft_name}")
        else:
            print("All NFTs are using asset-specific media files!")
