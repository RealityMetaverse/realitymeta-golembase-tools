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
from ..factories.reality_meta_golem_base_entity_factory import (
    create_reality_meta_golem_base_entities_from_directory,
)
from ..dataclasses.reality_meta_golem_base_entity import RealityMetaGolemBaseEntity
from ..dataclasses.reality_meta_golem_base_entity_audio import (
    RealityMetaGolemBaseEntityAudio,
)
from ..dataclasses.reality_meta_golem_base_entity_image import (
    RealityMetaGolemBaseEntityImage,
)
from ..dataclasses.reality_meta_golem_base_entity_json import (
    RealityMetaGolemBaseEntityJson,
)
from ..dataclasses.reality_meta_golem_base_entity_text import (
    RealityMetaGolemBaseEntityText,
)
from ..dataclasses.reality_meta_golem_base_entity_video import (
    RealityMetaGolemBaseEntityVideo,
)
from ..utils.golem_base_utils import create_golem_base_client


# Default input directory
DEFAULT_IN_DIR = "./database"


async def check_entities_batch(
    golem_base_client: GolemBaseClient,
    entities: List[
        RealityMetaGolemBaseEntity
        | RealityMetaGolemBaseEntityAudio
        | RealityMetaGolemBaseEntityImage
        | RealityMetaGolemBaseEntityJson
        | RealityMetaGolemBaseEntityText
        | RealityMetaGolemBaseEntityVideo
    ],
) -> dict:
    """
    Check existence of multiple entities at once.
    Returns dict with results for each entity.
    """
    results = {}

    try:
        # Collect all entity checksums, file names, and categories for batch queries
        entity_checksums = []
        file_names = []
        categories = []

        for entity in entities:
            entity_checksum = entity._sys_entity_checksum
            file_name = entity._sys_file_name
            category = entity._sys_category

            entity_checksums.append(entity_checksum)
            file_names.append(file_name)
            categories.append(category)

        # Batch query for entity checksums
        entity_checksum_entities = {}
        if entity_checksums:
            entity_checksum_query = " || ".join(
                [f'_sys_entity_checksum = "{ec}"' for ec in entity_checksums]
            )
            entities = await golem_base_client.query_entities(entity_checksum_query)
            for entity in entities:
                # Extract entity checksum from entity annotations
                for annotation in entity.string_annotations + entity.number_annotations:
                    if annotation.name == "_sys_entity_checksum":
                        entity_checksum_entities[annotation.value] = entity.entity_key
                        break

        # Batch query for file names and categories
        file_category_entities = {}
        if file_names and categories:
            # Create queries for file_name + category combinations
            file_category_queries = []
            for file_name, category in zip(file_names, categories):
                file_category_queries.append(
                    f'_sys_file_name = "{file_name}" && _sys_category = "{category}"'
                )

            file_category_query = " || ".join(file_category_queries)
            entities = await golem_base_client.query_entities(file_category_query)
            for entity in entities:
                # Extract file_name and category from entity annotations
                entity_file_name = None
                entity_category = None
                for annotation in entity.string_annotations + entity.number_annotations:
                    if annotation.name == "_sys_file_name":
                        entity_file_name = annotation.value
                    elif annotation.name == "_sys_category":
                        entity_category = annotation.value

                if entity_file_name and entity_category:
                    key = f"{entity_file_name}|{entity_category}"
                    file_category_entities[key] = entity.entity_key

        # Process results for each entity
        for entity in entities:
            entity_checksum = entity._sys_entity_checksum
            file_name = entity._sys_file_name
            category = entity._sys_category
            file_category_key = f"{file_name}|{category}"

            # Check entity checksum first (exact match - skip)
            if entity_checksum in entity_checksum_entities:
                results[entity] = {
                    "action": "skip",
                    "reason": "entity_checksum_exists",
                    "entity_key": entity_checksum_entities[entity_checksum],
                }
            # Then check file_name + category (update)
            elif file_category_key in file_category_entities:
                results[entity] = {
                    "action": "update",
                    "reason": "file_name_category_exists",
                    "entity_key": file_category_entities[file_category_key],
                }
            # Default to create
            else:
                results[entity] = {
                    "action": "create",
                    "reason": "not_found",
                    "entity_key": None,
                }

        return results

    # TODO: think better way to handle this
    except Exception as e:
        logger.error(f"Error in batch entity check: {e}")
        # Fallback: skip all if batch query fails
        return {
            entity: {
                "action": "skip",
                "reason": "query_error",
                "entity_key": None,
            }
            for entity in entities
        }


async def update_golem_base_database(
    golem_base_client: GolemBaseClient,
    entities: List[
        RealityMetaGolemBaseEntity
        | RealityMetaGolemBaseEntityAudio
        | RealityMetaGolemBaseEntityImage
        | RealityMetaGolemBaseEntityJson
        | RealityMetaGolemBaseEntityText
        | RealityMetaGolemBaseEntityVideo
    ],
    batch_size: int = 15,
    ttl: int = 3600,
):
    """Write all metadata to Golem Base using the provided client with create/update logic."""
    # Set up log watching
    await golem_base_client.watch_logs(
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

    # Batch check all entities at once
    logger.info("Checking entity existence in batch...")
    entity_results = await check_entities_batch(golem_base_client, entities)

    # Process each entity based on batch results
    for entity in entities:
        filename = entity._sys_file_name

        # Create entity data and annotations from the entity
        entity_data, string_annotations, number_annotations = (
            entity.to_golem_base_entity()
        )

        # Get the action determined by batch check
        result = entity_results.get(
            entity, {"action": "skip", "reason": "not_found", "entity_key": None}
        )
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
                receipts = await golem_base_client.create_entities(batch)
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
                receipts = await golem_base_client.update_entities(batch)
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
        description="Update Golem Base database with RealityMeta entities"
    )
    ap.add_argument(
        "--in-dir",
        "--in",
        dest="in_dir",
        default=DEFAULT_IN_DIR,
        help=f"Input directory with RealityMeta entities (default: {DEFAULT_IN_DIR})",
    )
    ap.add_argument(
        "--batch-size",
        "-bs",
        dest="batch_size",
        type=int,
        default=15,
        help="Number of entities to update in each batch (default: 15)",
    )
    ap.add_argument(
        "--ttl",
        type=int,
        default=86_400,
        help="Time-to-live for entities in seconds (default: 86_400)",
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
        entities = create_reality_meta_golem_base_entities_from_directory(args.in_dir)
    except Exception as e:
        logger.error(f"Error loading entities from directory: {e}")
        sys.exit(1)

    if not entities:
        logger.error(f"No entities found in {args.in_dir}")
        logger.error("Make sure the directory contains supported files")
        sys.exit(1)

    logger.info(f"Found {len(entities)} entities")

    # Create a client to interact with the GolemDB API
    logger.info("Initializing Golem DB client...")
    golem_base_client = await create_golem_base_client(
        rpc_url=args.rpc_url, ws_url=args.ws_url, private_key=args.private_key
    )

    try:
        # Write to Golem Base
        await update_golem_base_database(
            golem_base_client,
            entities,
            batch_size=args.batch_size,
            ttl=args.ttl,
        )

        logger.info("Import completed!")
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
