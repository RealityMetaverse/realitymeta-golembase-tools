import argparse
import os
import sys
from ..factories import create_rmgb_entities_from_directory
from ..common.globals import logger

entities = []


def main():

    ap = argparse.ArgumentParser(description="Create RM Arkiv entities from directory")
    ap.add_argument(
        "--in-dir",
        "-i",
        dest="in_dir",
        required=True,
        help="Input directory with files to process",
    )
    ap.add_argument(
        "--rpc-url",
        "-r",
        dest="rpc_url",
        help="Arkiv RPC URL (uses default from config if not provided)",
    )
    ap.add_argument(
        "--ws-url",
        "-w",
        dest="ws_url",
        help="Arkiv WebSocket URL (uses default from config if not provided)",
    )
    ap.add_argument(
        "--private-key",
        "-k",
        dest="private_key",
        help="Private key for Arkiv authentication (uses PRIVATE_KEY environment variable if not provided)",
    )

    args = ap.parse_args()

    # Check if directory exists
    if not os.path.isdir(args.in_dir):
        logger.error(f"Error: Directory '{args.in_dir}' does not exist")
        sys.exit(1)

    # Load entities using the factory function
    try:
        global entities
        entities = create_rmgb_entities_from_directory(args.in_dir)
        logger.info(f"Successfully created {len(entities)} entities from {args.in_dir}")
    except Exception as e:
        logger.error(f"Error creating entities from directory: {e}")
        sys.exit(1)

    if not entities:
        logger.error(f"No entities found in {args.in_dir}")
        logger.error("Make sure the directory contains supported files")
        sys.exit(1)


if __name__ == "__main__":
    main()
