import asyncio
import os
import argparse
import sys
from typing import List
from ..common.enums import Encoding

from golem_base_sdk import (
    GolemBaseClient,
    GolemBaseCreate,
    GolemBaseUpdate,
    GenericBytes,
)
from ..common.globals import logger, reset_globals
from ..factories.rm_arkiv_entity_factory import (
    create_rm_arkiv_entities_from_directory,
)
from ..dataclasses.rm_arkiv_entity import RmArkivEntity
from ..dataclasses.rm_arkiv_entity_audio import (
    RmArkivEntityAudio,
)
from ..dataclasses.rm_arkiv_entity_image import (
    RmArkivEntityImage,
)
from ..dataclasses.rm_arkiv_entity_json import (
    RmArkivEntityJson,
)
from ..dataclasses.rm_arkiv_entity_text import (
    RmArkivEntityText,
)
from ..dataclasses.rm_arkiv_entity_video import (
    RmArkivEntityVideo,
)
from ..utils.arkiv_utils import create_arkiv_client


# Default input directory
DEFAULT_IN_DIR = "./database"


async def check_entities_individual(
    arkiv_client: GolemBaseClient,
    entities: List[
        RmArkivEntity
        | RmArkivEntityAudio
        | RmArkivEntityImage
        | RmArkivEntityJson
        | RmArkivEntityText
        | RmArkivEntityVideo
    ],
) -> dict:
    """
    Check existence of entities individually.
    Returns dict with results for each entity.
    """
    results = {}

    logger.info(f"Checking {len(entities)} entities individually...")

    for entity in entities:
        try:
            entity_checksum = entity._sys_entity_checksum
            file_name = entity._sys_file_name
            category = entity._sys_category

            # First, try to find by entity checksum (exact match - skip)
            entity_checksum_query = f'_sys_entity_checksum = "{entity_checksum}"'
            queried_entities = await arkiv_client.query_entities(
                entity_checksum_query
            )

            if queried_entities:
                # Found exact match by entity checksum - skip
                results[entity_checksum] = {
                    "action": "skip",
                    "reason": "entity_checksum_exists",
                    "entity_key": queried_entities[0].entity_key,
                }
                logger.info(
                    f"Found exact match for {file_name} by entity checksum - skipping"
                )
                continue

            # If no exact match, try to find by file_name + category (update)
            file_category_query = (
                f'_sys_file_name = "{file_name}" && _sys_category = "{category}"'
            )
            queried_entities = await arkiv_client.query_entities(
                file_category_query
            )

            if queried_entities:
                # Found match by file_name + category - update
                results[entity_checksum] = {
                    "action": "update",
                    "reason": "file_name_category_exists",
                    "entity_key": queried_entities[0].entity_key,
                }
                logger.info(
                    f"Found match for {file_name} by file_name+category - will update"
                )
            else:
                # No match found - create
                results[entity_checksum] = {
                    "action": "create",
                    "reason": "not_found",
                    "entity_key": None,
                }
                logger.info(f"No match found for {file_name} - will create")

        except Exception as e:
            logger.error(
                f"Error checking entity {getattr(entity, '_sys_file_name', 'unknown')}: {e}"
            )
            # Fallback to skip for this entity
            entity_checksum = getattr(entity, "_sys_entity_checksum", "unknown")
            results[entity_checksum] = {
                "action": "skip",
                "reason": "processing_error",
                "entity_key": None,
            }

    return results


async def update_arkiv_database(
    arkiv_client: GolemBaseClient,
    entities: List[
        RmArkivEntity
        | RmArkivEntityAudio
        | RmArkivEntityImage
        | RmArkivEntityJson
        | RmArkivEntityText
        | RmArkivEntityVideo
    ],
    batch_size: int = 15,
    ttl: int = 3600,
):
    """Write all metadata to Arkiv using the provided client with create/update logic."""
    # Set up log watching
    await arkiv_client.watch_logs(
        label="nft_metadata",
        create_callback=lambda create: (
            logger.info(f"WATCH-> Create: {create}") if logger else None
        ),
        update_callback=lambda update: (
            logger.info(f"WATCH-> Update: {update}") if logger else None
        ),
        delete_callback=lambda delete: (
            logger.info(f"WATCH-> Delete: {delete}") if logger else None
        ),
        extend_callback=lambda extend: (
            logger.info(f"WATCH-> Extend: {extend}") if logger else None
        ),
    )

    creates = []
    updates = []
    skipped = []

    logger.info(f"Processing {len(entities)} entities...")

    # Check all entities individually
    logger.info("Checking entity existence individually...")
    entity_results = await check_entities_individual(arkiv_client, entities)

    # Process each entity based on batch results
    for entity in entities:
        filename = entity._sys_file_name

        # Create entity data and annotations from the entity
        entity_data, string_annotations, number_annotations = (
            entity.to_arkiv_entity()
        )

        # Get the action determined by batch check
        result = entity_results[entity._sys_entity_checksum]

        action = result["action"]
        entity_key = result["entity_key"]
        reason = result["reason"]

        if action == "skip":
            if logger:
                logger.info(f"Skipping {filename}: {reason}")
            skipped.append(filename)
        elif action == "update":
            # Update existing entity
            update_entity = GolemBaseUpdate(
                GenericBytes.from_hex_string(entity_key),
                entity_data.encode(Encoding.UTF8.value),
                ttl,
                string_annotations,
                number_annotations,
            )
            updates.append(update_entity)
            if logger:
                logger.info(f"Prepared update for {filename} ({reason})")
        else:  # action == 'create'
            # Create new entity
            create_entity = GolemBaseCreate(
                entity_data.encode(Encoding.UTF8.value),
                ttl,
                string_annotations,
                number_annotations,
            )
            creates.append(create_entity)
            if logger:
                logger.info(
                    f"Prepared create for {filename} ({reason}) with {len(string_annotations)} string annotations and {len(number_annotations)} number annotations"
                )

    # Process creates and updates in batches
    logger.info(
        f"Executing operations: {len(creates)} creates, {len(updates)} updates, {len(skipped)} skipped"
    )

    # Process creates in batches
    if creates:
        logger.info(f"Creating {len(creates)} new entities...")
        for i in range(0, len(creates), batch_size):
            batch = creates[i : i + batch_size]
            try:
                receipts = await arkiv_client.create_entities(batch)
                if logger:
                    logger.info(
                        f"Successfully created batch {i//batch_size + 1}: {len(receipts)} entities"
                    )

                # Print receipt details for the first few
                for j, receipt in enumerate(
                    receipts[:3]
                ):  # Show first 3 receipts in each batch
                    if logger:
                        logger.info(f"Create Receipt {i+j+1}: {receipt}")

            except Exception as e:
                if logger:
                    logger.error(f"Error creating batch {i//batch_size + 1}: {e}")

    # Process updates in batches
    if updates:
        logger.info(f"Updating {len(updates)} existing entities...")
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            try:
                receipts = await arkiv_client.update_entities(batch)
                if logger:
                    logger.info(
                        f"Successfully updated batch {i//batch_size + 1}: {len(receipts)} entities"
                    )

                # Print receipt details for the first few
                for j, receipt in enumerate(
                    receipts[:3]
                ):  # Show first 3 receipts in each batch
                    if logger:
                        logger.info(f"Update Receipt {i+j+1}: {receipt}")

            except Exception as e:
                if logger:
                    logger.error(f"Error updating batch {i//batch_size + 1}: {e}")

    logger.info(
        f"Finished processing metadata: {len(creates)} created, {len(updates)} updated, {len(skipped)} skipped"
    )


async def main():
    """Main function to run the metadata import."""
    # Reset global instances to ensure clean state
    reset_globals()

    ap = argparse.ArgumentParser(
        description="Update Arkiv database with RM entities"
    )
    ap.add_argument(
        "--in-dir",
        "-i",
        dest="in_dir",
        default=DEFAULT_IN_DIR,
        help=f"Input directory with RM entities (default: {DEFAULT_IN_DIR})",
    )
    ap.add_argument(
        "--batch-size",
        "-b",
        dest="batch_size",
        type=int,
        default=15,
        help="Number of entities to update in each batch (default: 15)",
    )
    ap.add_argument(
        "--ttl",
        "-t",
        type=int,
        default=86_400,
        help="Time-to-live for entities in seconds (default: 86_400)",
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

    # Check if private key is set
    if not args.private_key:
        logger.error("Error: Private key is not set")
        logger.error(
            "Please provide a private key using --private-key argument or set PRIVATE_KEY environment variable"
        )
        sys.exit(1)

    # Validate batch size and TTL
    if args.batch_size < 1:
        logger.error("Error: Batch size must be at least 1")
        sys.exit(1)

    if args.ttl < 1:
        logger.error("Error: TTL must be at least 1 second")
        sys.exit(1)

    # Load metadata files using the new factory function
    try:
        entities = create_rm_arkiv_entities_from_directory(args.in_dir)
    except Exception as e:
        logger.error(f"Error loading entities from directory: {e}")
        sys.exit(1)

    if not entities:
        logger.error(f"No entities found in {args.in_dir}")
        logger.error("Make sure the directory contains supported files")
        sys.exit(1)

    logger.info(f"Found {len(entities)} entities")

    # Create a client to interact with the Arkiv API
    arkiv_client = await create_arkiv_client(
        rpc_url=args.rpc_url, ws_url=args.ws_url, private_key=args.private_key
    )

    try:
        # Write to Arkiv
        await update_arkiv_database(
            arkiv_client,
            entities,
            batch_size=args.batch_size,
            ttl=args.ttl,
        )

        logger.info("Import completed!")
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
