#!/usr/bin/env python3
import asyncio
import os
import argparse
import sys
from pathlib import Path
from typing import List

from golem_base_sdk import GolemBaseClient, GenericBytes
from ..common.globals import logger, reset_globals
from ..dataclasses.rm_arkiv_entity import (
    RmArkivEntity,
)
from ..dataclasses.rm_arkiv_entity_audio import (
    RmArkivEntityAudio,
)
from ..dataclasses.rm_arkiv_entity_image import (
    RmArkivEntityImage,
)
from ..dataclasses.rm_arkiv_entity_audio import (
    RmArkivEntityAudio,
)
from ..dataclasses.rm_arkiv_entity_image import (
    RmArkivEntityImage,
)
from ..dataclasses.rm_arkiv_entity_video import (
    RmArkivEntityVideo,
)
from ..dataclasses.rm_arkiv_entity_text import (
    RmArkivEntityText,
)
from ..dataclasses.rm_arkiv_entity_json import (
    RmArkivEntityJson,
)


from ..utils.arkiv_utils import create_arkiv_client


# Default output directory
DEFAULT_OUT_DIR = "./recreated_files"


async def query_entities_by_version(
    arkiv_client: GolemBaseClient, version: int = 1
) -> List[any]:
    """
    Query all entities with a specific sys version from Arkiv.
    Returns a list of Arkiv entities.
    """
    try:
        # Query for entities with the specified version
        query = f"_sys_version = {version}"
        logger.info(f"Querying entities with version {version}...")

        entities = await arkiv_client.query_entities(query)
        logger.info(f"Found {len(entities)} entities with version {version}")

        return entities
    except Exception as e:
        logger.error(f"Error querying entities: {e}")
        return []


async def recreate_files_from_entities(
    arkiv_client: GolemBaseClient,
    output_dir: Path,
    version: int = 1,
) -> None:
    """
    Query entities with specified version and recreate files.
    """
    # Query entities with the specified version
    entities = await query_entities_by_version(arkiv_client, version)

    if not entities:
        logger.warn(f"No entities found with version {version}")
        return

    logger.info(f"Processing {len(entities)} entities...")

    successful_recreations = 0
    failed_recreations = 0

    for i, entity in enumerate(entities, 1):
        try:
            # Get entity metadata - convert entity key to proper format
            entity_key_bytes = GenericBytes.from_hex_string(entity.entity_key)
            entity_metadata = await arkiv_client.get_entity_metadata(
                entity_key_bytes
            )

            # Determine the correct entity class based on file type
            file_type = None
            for annotation in entity_metadata.string_annotations:
                if annotation.key == "_sys_file_type":
                    file_type = annotation.value
                    break

            # Import the appropriate entity class
            if file_type == "image":
                rmgb_entity = RmArkivEntityImage.from_arkiv_entity(
                    entity_metadata
                )
            elif file_type == "audio":
                rmgb_entity = RmArkivEntityAudio.from_arkiv_entity(
                    entity_metadata
                )
            elif file_type == "video":
                rmgb_entity = RmArkivEntityVideo.from_arkiv_entity(
                    entity_metadata
                )
            elif file_type == "text":
                rmgb_entity = RmArkivEntityText.from_arkiv_entity(
                    entity_metadata
                )
            elif file_type == "json":
                rmgb_entity = RmArkivEntityJson.from_arkiv_entity(
                    entity_metadata
                )
            else:
                # Fallback to base entity
                rmgb_entity = RmArkivEntity.from_arkiv_entity(
                    entity_metadata
                )

            # Recreate the file
            output_file_path = rmgb_entity.to_file(
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
        logger.warn(f"Failed to recreate: {failed_recreations} files")


async def main():
    """Main function to run the file recreation from database."""
    # Reset global instances to ensure clean state
    reset_globals()

    ap = argparse.ArgumentParser(
        description="Recreate files from Arkiv entities with specific version"
    )
    ap.add_argument(
        "--out-dir",
        "-o",
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

    # Create a client to interact with the Arkiv API
    logger.info("Initializing Arkiv client...")
    arkiv_client = await create_arkiv_client(
        rpc_url=args.rpc_url, ws_url=args.ws_url, private_key=args.private_key
    )

    try:
        # Recreate files from database
        await recreate_files_from_entities(
            arkiv_client,
            output_dir,
            version=args.version,
        )

        logger.info("File recreation completed!")
    finally:
        # Always disconnect the client when done
        logger.info("Disconnecting Arkiv client...")
        await arkiv_client.disconnect()

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
