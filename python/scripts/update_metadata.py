import asyncio
import dotenv
import os
import argparse
import sys
from typing import List, Union, Any
from ..common.config import Encoding

# Add parent directory to path for relative imports

from golem_base_sdk import (
    GolemBaseClient,
    GolemBaseCreate,
    Annotation,
    GolemBaseUpdate,
    GenericBytes,
)
from ..utils.logging_utils import (
    color_text,
    green_checkmark,
    yellow_warning,
    blue_arrow,
    blue_info,
    red_x,
    print_green_checkmark,
    print_yellow_warning,
    print_blue_arrow,
    print_blue_info,
    print_red_x,
)
from ..common.globals import logger, reset_globals
from ..utils.file_utils import load_data_files as load_metadata_files

dotenv.load_dotenv()

GOLEM_DB_RPC = "https://reality-games.holesky.golem-base.io/rpc"
GOLEM_DB_WSS = "wss://reality-games.holesky.golem-base.io/rpc/ws"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

FLATTENED_METADATA_DIR = "./metadata-flattener/metadatas-flattened"


def create_annotations_from_metadata(
    metadata: dict,
) -> tuple[List[Annotation], List[Annotation]]:
    """
    Create annotations from metadata dictionary.
    Returns tuple of (string_annotations, number_annotations)
    """
    string_annotations = []
    number_annotations = []

    for key, value in metadata.items():
        if isinstance(value, str):
            string_annotations.append(Annotation(key, value))
        elif isinstance(value, int):
            number_annotations.append(Annotation(key, value))
        else:
            # Convert other types to string as fallback
            string_annotations.append(Annotation(key, str(value)))

    return string_annotations, number_annotations


async def create_golem_client(
    rpc_url: str = None,
    ws_url: str = None,
    private_key: str = None,
):
    """Create and configure a GolemBaseClient instance."""
    # Use provided URLs or fall back to defaults
    rpc_url = rpc_url or GOLEM_DB_RPC
    ws_url = ws_url or GOLEM_DB_WSS

    # Use provided private key or fall back to environment variable
    private_key = private_key or PRIVATE_KEY

    # Create a client to interact with the GolemDB API
    golem_base_client = await GolemBaseClient.create(
        rpc_url=rpc_url,
        ws_url=ws_url,
        private_key=private_key,
    )
    logger.info("Golem DB client initialized")

    return golem_base_client


async def check_entities_batch(
    golem_base_client: GolemBaseClient, metadata_items: List[dict]
) -> dict:
    """
    Check existence of multiple entities at once using batch queries.
    Returns dict with results for each item.
    """
    results = {}

    try:
        # Collect all content_hashes and attr__ids for batch queries
        content_hashes = []
        attr_ids = []

        for metadata in metadata_items:
            content_hash = metadata["content_hash"]  # Must exist
            attr_id = metadata["attr__id"]  # Must exist

            content_hashes.append(content_hash)
            attr_ids.append(attr_id)

        # Batch query for content_hashes
        content_hash_entities = {}
        content_hash_query = " || ".join(
            [f'content_hash = "{ch}"' for ch in content_hashes]
        )
        entities = await golem_base_client.query_entities(content_hash_query)
        for entity in entities:
            # Extract content_hash from entity annotations
            for annotation in entity.string_annotations + entity.number_annotations:
                if annotation.name == "content_hash":
                    content_hash_entities[annotation.value] = entity.entity_key
                    break

        # Batch query for attr__ids
        attr_id_entities = {}
        attr_id_query = " || ".join([f'attr__id = "{aid}"' for aid in attr_ids])
        entities = await golem_base_client.query_entities(attr_id_query)
        for entity in entities:
            # Extract attr__id from entity annotations
            for annotation in entity.string_annotations + entity.number_annotations:
                if annotation.name == "attr__id":
                    attr_id_entities[str(annotation.value)] = entity.entity_key
                    break

        # Process results for each item
        for metadata in metadata_items:
            file_path = metadata["file_path"]
            content_hash = metadata["content_hash"]  # Must exist
            attr_id = metadata["attr__id"]  # Must exist

            # Check content_hash first
            if content_hash in content_hash_entities:
                results[file_path] = {
                    "action": "skip",
                    "reason": "content_hash_exists",
                    "entity_key": content_hash_entities[content_hash],
                }
            # Then check attr__id
            elif str(attr_id) in attr_id_entities:
                results[file_path] = {
                    "action": "update",
                    "reason": "attr_id_exists",
                    "entity_key": attr_id_entities[str(attr_id)],
                }
            # Default to create
            else:
                results[file_path] = {
                    "action": "create",
                    "reason": "not_found",
                    "entity_key": None,
                }

        return results

    except Exception as e:
        logger.error(f"Error in batch entity check: {e}")
        # Fallback: mark all as create if batch query fails
        return {
            metadata["file_path"]: {
                "action": "create",
                "reason": "query_error",
                "entity_key": None,
            }
            for metadata in metadata_items
        }


async def write_metadata_to_golem(
    golem_base_client: GolemBaseClient,
    metadata_files: List[dict],
    batch_size: int = 10,
    ttl: int = 3600,
    enable_logs: bool = True,
):
    """Write all metadata to Golem Base using the provided client with create/update logic."""
    # Set up log watching (optional)
    if enable_logs:
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

    print_blue_arrow(f"Processing {len(metadata_files)} metadata files...")

    # Batch check all entities at once
    print_blue_arrow("Checking entity existence in batch...")
    entity_results = await check_entities_batch(golem_base_client, metadata_files)

    # Process each file based on batch results
    for metadata in metadata_files:
        file_path = metadata["file_path"]
        filename = os.path.basename(file_path)

        # Create annotations from metadata (content_hash should already be included)
        string_annotations, number_annotations = create_annotations_from_metadata(
            metadata
        )

        # Create entity data - using the name as the main data
        entity_data = metadata.get("name", "NFT Metadata").encode(Encoding.UTF8.value)

        # Get the action determined by batch check
        result = entity_results.get(
            file_path, {"action": "create", "reason": "not_found", "entity_key": None}
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
                entity_data,
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
                entity_data, ttl, string_annotations, number_annotations
            )
            creates.append(create_entity)
            if logger:
                logger.info(
                    f"Prepared create for {filename} ({reason}) with {len(string_annotations)} string annotations and {len(number_annotations)} number annotations"
                )

    # Process creates and updates in batches
    total_operations = len(creates) + len(updates)
    print_blue_arrow(
        f"Executing operations: {len(creates)} creates, {len(updates)} updates, {len(skipped)} skipped"
    )

    # Process creates in batches
    if creates:
        print_blue_arrow(f"Creating {len(creates)} new entities...")
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
        print_blue_arrow(f"Updating {len(updates)} existing entities...")
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

    print_green_checkmark(
        f"Finished processing metadata: {len(creates)} created, {len(updates)} updated, {len(skipped)} skipped"
    )


async def main():
    """Main function to run the metadata import."""
    # Reset global instances to ensure clean state
    reset_globals()

    ap = argparse.ArgumentParser(
        description="Import NFT metadata JSON files to Golem Base"
    )
    ap.add_argument(
        "--in",
        dest="in_dir",
        default=FLATTENED_METADATA_DIR,
        help=f"Input directory with *.json (default: {FLATTENED_METADATA_DIR})",
    )
    ap.add_argument(
        "--batch-size",
        dest="batch_size",
        type=int,
        default=50,
        help="Number of entities to create in each batch (default: 50)",
    )
    ap.add_argument(
        "--ttl",
        type=int,
        default=86_400,
        help="Time-to-live for entities in seconds (default: 86_400)",
    )
    ap.add_argument(
        "--no-logs",
        action="store_true",
        help="Disable log watching for faster processing",
    )
    ap.add_argument(
        "--rpc-url",
        dest="rpc_url",
        default=GOLEM_DB_RPC,
        help=f"Golem Base RPC URL (default: {GOLEM_DB_RPC})",
    )
    ap.add_argument(
        "--ws-url",
        dest="ws_url",
        default=GOLEM_DB_WSS,
        help=f"Golem Base WebSocket URL (default: {GOLEM_DB_WSS})",
    )
    ap.add_argument(
        "--private-key",
        dest="private_key",
        help="Private key for Golem Base authentication (overrides PRIVATE_KEY environment variable)",
    )
    ap.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Load and process files without creating entities",
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    args = ap.parse_args()

    # Check if directory exists
    if not os.path.isdir(args.in_dir):
        print_red_x(f"Error: Directory '{args.in_dir}' does not exist")
        sys.exit(1)

    # Check if private key is set
    private_key = args.private_key or PRIVATE_KEY
    if not private_key and not args.dry_run:
        print_red_x("Error: Private key is not set")
        print(
            "Please provide a private key using --private-key argument or set PRIVATE_KEY environment variable"
        )
        sys.exit(1)

    # Validate batch size and TTL
    if args.batch_size < 1:
        print_red_x("Error: Batch size must be at least 1")
        sys.exit(1)

    if args.ttl < 1:
        print_red_x("Error: TTL must be at least 1 second")
        sys.exit(1)

    if args.verbose:
        print_blue_arrow("Starting NFT Metadata to Golem Base import...")
        print(f"Directory: {args.in_dir}")
        print(f"Batch size: {args.batch_size}")
        print(f"TTL: {args.ttl} seconds")
        print(f"Logs enabled: {not args.no_logs}")
        print(f"Dry run: {args.dry_run}")
        print()

    # Load metadata files
    metadata_files = load_metadata_files(args.in_dir, logger)

    if not metadata_files:
        print_red_x(f"No metadata files found in {args.in_dir}")
        print("Make sure the directory contains .json files")
        sys.exit(1)

    print_green_checkmark(f"Found {len(metadata_files)} metadata files")

    if args.dry_run:
        print(f"{blue_info()} DRY RUN MODE - No entities will be created or updated")
        print("\nFiles that would be processed:")
        for metadata in metadata_files[:5]:  # Show first 5 files
            content_hash = metadata["content_hash"]  # Must exist
            attr_id = metadata["attr__id"]  # Must exist
            print(
                f"  - {os.path.basename(metadata['file_path'])} (content_hash: {content_hash[:16]}..., attr__id: {attr_id})"
            )
        if len(metadata_files) > 5:
            print(f"  ... and {len(metadata_files) - 5} more files")
        print(
            f"\nWould process {len(metadata_files)} files with create/update/skip logic in batches of {args.batch_size}"
        )
        print(
            "Logic: Check content_hash → Check attr__id → Create/Update/Skip accordingly"
        )
        return

    # Create a client to interact with the GolemDB API
    print_blue_arrow("Initializing Golem DB client...")
    golem_base_client = await create_golem_client(
        rpc_url=args.rpc_url, ws_url=args.ws_url, private_key=private_key
    )

    try:
        # Write to Golem Base
        await write_metadata_to_golem(
            golem_base_client,
            metadata_files,
            batch_size=args.batch_size,
            ttl=args.ttl,
            enable_logs=not args.no_logs,
        )

        print_green_checkmark("Import completed!")
    finally:
        # Always disconnect the client when done
        print_blue_arrow("Disconnecting Golem DB client...")
        await golem_base_client.disconnect()

        # Print log summary if any logs were generated
        logger.print_summary()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_red_x("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_red_x(f"\nUnexpected error: {e}")
        sys.exit(1)
