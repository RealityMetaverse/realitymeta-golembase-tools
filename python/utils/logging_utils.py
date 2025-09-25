#!/usr/bin/env python3
"""
Logging utilities with colored output and counters.
"""

from typing import Tuple


def color_text(text: str, color: str) -> str:
    """Apply ANSI color codes to text."""
    colors = {
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "green": "\033[92m",
        "red": "\033[91m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


# COLORED SYMBOLS
def green_checkmark() -> str:
    """Return a green checkmark symbol."""
    return color_text("✓", "green")


def yellow_warning() -> str:
    """Return a yellow warning symbol."""
    return color_text("⚠", "yellow")


def blue_arrow() -> str:
    """Return a blue arrow symbol."""
    return color_text("➤", "blue")


def blue_info() -> str:
    """Return a blue info symbol."""
    return color_text("ℹ", "blue")


def red_x() -> str:
    """Return a red X symbol."""
    return color_text("✗", "red")


# PRINT WITH COLORED SYMBOLS
def print_green_checkmark(message: str) -> None:
    """Print a green checkmark followed by the message."""
    print(f"{green_checkmark()} {message}")


def print_yellow_warning(message: str) -> None:
    """Print a yellow warning symbol followed by the message."""
    print(f"{yellow_warning()} {message}")


def print_blue_arrow(message: str) -> None:
    """Print a blue arrow symbol followed by the message."""
    print(f"{blue_arrow()} {message}")


def print_blue_info(message: str) -> None:
    """Print a blue info symbol followed by the message."""
    print(f"{blue_info()} {message}")


def print_red_x(message: str) -> None:
    """Print a red X symbol followed by the message."""
    print(f"{red_x()} {message}")


class Logger:
    """A logger class with colored output and message counters."""

    def __init__(self):
        """Initialize logger with zero counters."""
        self.info_count = 0
        self.warn_count = 0
        self.error_count = 0
        self.header_printed = False
        self.print_in_new_line = False

    def _print_header_if_needed(self) -> None:
        """Print log header if it hasn't been printed yet."""
        if not self.header_printed:
            print("\nPROCESSING LOG:")
            print("-" * 15)
            self.header_printed = True

    def _print_new_line_if_needed(self) -> None:
        """Print a new line if print_in_new_line is True and then set it to False."""
        if self.print_in_new_line:
            print()
            self.print_in_new_line = False

    def info(self, message: str) -> None:
        """Print INFO message in blue and increment counter."""
        self._print_header_if_needed()
        self._print_new_line_if_needed()
        self.info_count += 1
        print(f"{color_text('[INFO]', 'blue')} {message}")

    def warn(self, message: str) -> None:
        """Print WARN message in yellow and increment counter."""
        self._print_header_if_needed()
        self._print_new_line_if_needed()
        self.warn_count += 1
        print(f"{color_text('[WARN]', 'yellow')} {message}")

    def error(self, message: str) -> None:
        """Print ERROR message in red and increment counter."""
        self._print_header_if_needed()
        self._print_new_line_if_needed()
        self.error_count += 1
        print(f"{color_text('[ERROR]', 'red')} {message}")

    def get_counts(self) -> Tuple[int, int, int]:
        """Return current log counts as (info_count, warn_count, error_count)."""
        return self.info_count, self.warn_count, self.error_count

    def print_summary(self) -> None:
        """Print a summary of all log counts if any logs were generated."""
        if self.info_count > 0 or self.warn_count > 0 or self.error_count > 0:
            print(
                f"\n{blue_info()} Log summary: {color_text('[INFO]', 'blue')} {self.info_count}, {color_text('[WARN]', 'yellow')} {self.warn_count}, {color_text('[ERROR]', 'red')} {self.error_count}"
            )

    def reset(self) -> None:
        """Reset all log counters and header flag."""
        self.info_count = 0
        self.warn_count = 0
        self.error_count = 0
        self.header_printed = False
        self.print_in_new_line = False
