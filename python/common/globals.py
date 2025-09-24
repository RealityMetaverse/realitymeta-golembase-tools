#!/usr/bin/env python3
"""
Global instances to be used across the entire project.
"""

from ..utils.logging_utils import Logger
from ..utils.reality_nft_utils import RealityNFTMediaStatistics

# GLOBAL INSTANCES
logger = Logger()
media_stats = RealityNFTMediaStatistics()


def reset_globals():
    """Reset both global instances to their initial state."""
    logger.reset()
    media_stats.reset()
