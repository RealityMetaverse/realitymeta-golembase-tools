"""
Reality NFT utilities for media URL validation and statistics tracking.
"""

from typing import List
from pathlib import Path


# TODO: fix circular dependency
def _get_logger():
    """Lazy load logger to avoid circular dependency."""
    from ..common.globals import logger

    return logger


def extract_file_basename_stem_from_url(url: str) -> str:
    """Extract the basename stem from a URL."""
    return Path(url).stem


class RealityNFTMediaStatistics:
    """Class to track media statistics for Reality NFT metadata."""

    def __init__(self):
        # Set to track unique files processed
        self.processed_files = set()

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
        self.processed_files.clear()
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
        Also adds the file to processed_files set to track unique files.
        """
        # Add this file to the set of processed files
        self.processed_files.add(file_basename_stem)

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
        Print a comprehensive media statistics report using the internal processed_files set.
        """
        total_files = len(self.processed_files)
        total_default_count = (
            self.default_image_count
            + self.default_animation_url_count
            + self.default_external_url_count
        )

        if total_files > 0:
            if total_default_count > 0:
                print(f"\nREALITY NFT MEDIA STATISTICS (out of {total_files} files):")
                print("-" * 50)

                if self.default_image_count > 0:
                    print(
                        f"Reality NFTs using default image ({self.default_image_count}):"
                    )
                    self._print_nft_names_in_columns(self.default_image_nfts)

                if self.default_animation_url_count > 0:
                    print(
                        f"\nReality NFTs using default animation ({self.default_animation_url_count}):"
                    )
                    self._print_nft_names_in_columns(self.default_animation_url_nfts)

                if self.default_external_url_count > 0:
                    print(
                        f"\nReality NFTs using default external_url ({self.default_external_url_count}):"
                    )
                    self._print_nft_names_in_columns(self.default_external_url_nfts)
            else:
                print("All Reality NFTs are using asset-specific media files!")

            _get_logger().print_in_new_line = True

    def _print_nft_names_in_columns(
        self, nft_names: List[str], columns: int = 10
    ) -> None:
        """
        Print NFT names in a columnar format for better readability.
        """
        if not nft_names:
            return

        sorted_names = sorted(nft_names)

        # Calculate the maximum width needed for each column
        max_name_length = max(len(name) for name in sorted_names) if sorted_names else 0
        column_width = max_name_length + 2  # Add some padding

        # Print names in columns
        for i in range(0, len(sorted_names), columns):
            row_names = sorted_names[i : i + columns]
            # Pad the row to have exactly 'columns' elements for consistent formatting
            while len(row_names) < columns:
                row_names.append("")

            # Format each name with proper spacing
            formatted_row = "  ".join(f"{name:<{column_width}}" for name in row_names)
            print(f"  {formatted_row}")
