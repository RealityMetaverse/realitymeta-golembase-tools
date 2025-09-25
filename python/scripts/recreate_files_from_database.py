#!/usr/bin/env python3
import asyncio
import os
import argparse
import sys
from pathlib import Path
from typing import List

from golem_base_sdk import GolemBaseClient
from ..common.globals import logger, reset_globals
from ..dataclasses.reality_meta_golem_base_entity import RealityMetaGolemBaseEntity
from ..utils.golem_base_utils import create_golem_base_client


# Default output directory
DEFAULT_OUT_DIR = "./recreated_files"


async def query_entities_by_version(
    golem_base_client: GolemBaseClient, version: int = 1
) -> List[any]:
    """
    Query all entities with a specific sys version from Golem Base.
    Returns a list of Golem Base entities.
    """
    try:
        # Query for entities with the specified version
        query = f"_sys_version = {version}"
        logger.info(f"Querying entities with version {version}...")

        entities = await golem_base_client.query_entities(query)
        logger.info(f"Found {len(entities)} entities with version {version}")

        return entities
    except Exception as e:
        logger.error(f"Error querying entities: {e}")
        return []


async def recreate_files_from_entities(
    golem_base_client: GolemBaseClient,
    output_dir: Path,
    version: int = 1,
) -> None:
    """
    Query entities with specified version and recreate files.
    """
    # Query entities with the specified version
    entities = await query_entities_by_version(golem_base_client, version)

    if not entities:
        logger.warning(f"No entities found with version {version}")
        return

    logger.info(f"Processing {len(entities)} entities...")

    successful_recreations = 0
    failed_recreations = 0

    for i, entity in enumerate(entities, 1):
        try:
            # Create RealityMetaGolemBaseEntity from Golem Base entity
            rmgb_entity = RealityMetaGolemBaseEntity.from_golem_base_entity(entity)

            # Recreate the file
            output_file_path = rmgb_entity.recreate_file(
                output_dir, organize_by_category=True
            )

            logger.info(f"[{i}/{len(entities)}] Recreated: {output_file_path}")
            successful_recreations += 1

        except Exception as e:
            logger.error(f"[{i}/{len(entities)}] Failed to recreate entity: {e}")
            failed_recreations += 1
            continue

    logger.info(f"File recreation completed!")
    logger.info(f"Successfully recreated: {successful_recreations} files")
    if failed_recreations > 0:
        logger.warning(f"Failed to recreate: {failed_recreations} files")


async def main():
    """Main function to run the file recreation from database."""
    # Reset global instances to ensure clean state
    reset_globals()

    ap = argparse.ArgumentParser(
        description="Recreate files from Golem Base entities with specific version"
    )
    ap.add_argument(
        "--output-dir",
        "--out",
        dest="output_dir",
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for recreated files (default: {DEFAULT_OUT_DIR})",
    )
    ap.add_argument(
        "--version",
        "-v",
        dest="version",
        type=int,
        default=1,
        help="Sys version to query for (default: 1)",
    )
    ap.add_argument(
        "--rpc-url",
        "-rpc",
        dest="rpc_url",
        help="Golem Base RPC URL (uses default from config if not provided)",
    )
    ap.add_argument(
        "--ws-url",
        "-ws",
        dest="ws_url",
        help="Golem Base WebSocket URL (uses default from config if not provided)",
    )
    ap.add_argument(
        "--private-key",
        "-pk",
        dest="private_key",
        help="Private key for Golem Base authentication (uses PRIVATE_KEY environment variable if not provided)",
    )
    args = ap.parse_args()

    # Convert output directory to Path object
    output_dir = Path(args.output_dir)

    # Check if private key is set
    if not args.private_key:
        logger.error("Error: Private key is not set")
        logger.error(
            "Please provide a private key using --private-key argument or set PRIVATE_KEY environment variable"
        )
        sys.exit(1)

    # Validate version
    if args.version < 1:
        logger.error("Error: Version must be at least 1")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info(f"Organize by category: {args.organize_by_category}")

    # Create a client to interact with the GolemDB API
    logger.info("Initializing Golem DB client...")
    golem_base_client = await create_golem_base_client(
        rpc_url=args.rpc_url, ws_url=args.ws_url, private_key=args.private_key
    )

    try:
        # Recreate files from database
        await recreate_files_from_entities(
            golem_base_client,
            output_dir,
            version=args.version,
        )

        logger.info("File recreation completed!")
    finally:
        # Always disconnect the client when done
        logger.info("Disconnecting Golem DB client...")
        await golem_base_client.disconnect()

        # Print log summary if any logs were generated
        logger.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
