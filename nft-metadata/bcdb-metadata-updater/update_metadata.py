import asyncio
import dotenv
import os
import json
import glob
import argparse
import sys
from typing import List, Union, Any

from golem_base_sdk import GolemBaseClient, GolemBaseCreate, Annotation

dotenv.load_dotenv()

GOLEM_DB_RPC = "https://reality-games.holesky.golem-base.io/rpc"
GOLEM_DB_WSS = "wss://reality-games.holesky.golem-base.io/rpc/ws"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Global log counters
info_count = 0
warn_count = 0
error_count = 0
header_printed = False

def color_text(text: str, color: str) -> str:
    """Apply ANSI color codes to text."""
    colors = {
        'blue': '\033[94m',
        'yellow': '\033[93m', 
        'green': '\033[92m',
        'red': '\033[91m',
        'reset': '\033[0m'
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def _print_header_if_needed() -> None:
    """Print log header if it hasn't been printed yet."""
    global header_printed
    if not header_printed:
        print("\nPROCESSING LOG:")
        print("-" * 15)
        header_printed = True

def log_info(message: str) -> None:
    """Print INFO message in blue and increment counter."""
    global info_count
    _print_header_if_needed()
    info_count += 1
    print(f"{color_text('[INFO]', 'blue')} {message}")

def log_warn(message: str) -> None:
    """Print WARN message in yellow and increment counter."""
    global warn_count
    _print_header_if_needed()
    warn_count += 1
    print(f"{color_text('[WARN]', 'yellow')} {message}")

def log_error(message: str) -> None:
    """Print ERROR message in red and increment counter."""
    global error_count
    _print_header_if_needed()
    error_count += 1
    print(f"{color_text('[ERROR]', 'red')} {message}")

def create_annotations_from_metadata(metadata: dict) -> tuple[List[Annotation], List[Annotation]]:
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

def load_metadata_files(directory_path: str) -> List[dict]:
    """Load all JSON metadata files from the specified directory."""
    metadata_files = []
    json_pattern = os.path.join(directory_path, "*.json")
    
    for file_path in glob.glob(json_pattern):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                metadata_files.append({
                    'file_path': file_path,
                    'metadata': metadata
                })
                log_info(f"Loaded metadata from: {os.path.basename(file_path)}")
        except Exception as e:
            log_error(f"Error loading {os.path.basename(file_path)}: {e}")
    
    return metadata_files

async def create_golem_client(rpc_url: str = None, ws_url: str = None, private_key: str = None):
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
    log_info("Golem DB client initialized")
    
    return golem_base_client

async def write_metadata_to_golem(golem_base_client: GolemBaseClient, metadata_files: List[dict], batch_size: int = 10, ttl: int = 3600, enable_logs: bool = True):
    """Write all metadata to Golem Base using the provided client."""
    # Set up log watching (optional)
    if enable_logs:
        await golem_base_client.watch_logs(
            label="nft_metadata",
            create_callback=lambda create: log_info(f"WATCH-> Create: {create}"),
            update_callback=lambda update: log_info(f"WATCH-> Update: {update}"),
            delete_callback=lambda delete: log_info(f"WATCH-> Delete: {delete}"),
            extend_callback=lambda extend: log_info(f"WATCH-> Extend: {extend}"),
        )

    creates = []
    
    for item in metadata_files:
        file_path = item['file_path']
        metadata = item['metadata']
        
        # Create annotations from metadata (content_hash should already be included)
        string_annotations, number_annotations = create_annotations_from_metadata(metadata)
        
        # Create entity data - using the name as the main data
        entity_data = metadata.get('name', 'NFT Metadata').encode('utf-8')
        
        # Create the entity
        create_entity = GolemBaseCreate(
            entity_data,
            ttl,  # TTL in seconds
            string_annotations,
            number_annotations
        )
        
        creates.append(create_entity)
        log_info(f"Prepared entity for {os.path.basename(file_path)} with {len(string_annotations)} string annotations and {len(number_annotations)} number annotations")

    # Batch create all entities
    print(f"{color_text('➤', 'blue')} Creating {len(creates)} entities in Golem Base...")
    
    # Process in batches to avoid overwhelming the API
    for i in range(0, len(creates), batch_size):
        batch = creates[i:i + batch_size]
        try:
            receipts = await golem_base_client.create_entities(batch)
            log_info(f"Successfully created batch {i//batch_size + 1}: {len(receipts)} entities")
            
            # Print receipt details for the first few
            for j, receipt in enumerate(receipts[:3]):  # Show first 3 receipts in each batch
                log_info(f"Receipt {i+j+1}: {receipt}")
                
        except Exception as e:
            log_error(f"Error creating batch {i//batch_size + 1}: {e}")

    print(f"{color_text('✓', 'green')} Finished writing metadata to Golem Base")

async def main():
    """Main function to run the metadata import."""
    ap = argparse.ArgumentParser(description="Import NFT metadata JSON files to Golem Base")
    ap.add_argument("--in", dest="in_dir", default="../metadata-flattener/metadatas-flattened", help="Input directory with *.json (default: ../metadata-flattener/metadatas-flattened)")
    ap.add_argument("--batch-size", dest="batch_size", type=int, default=10, help="Number of entities to create in each batch (default: 10)")
    ap.add_argument("--ttl", type=int, default=86_400, help="Time-to-live for entities in seconds (default: 86_400)")
    ap.add_argument("--no-logs", action="store_true", help="Disable log watching for faster processing")
    ap.add_argument("--rpc-url", dest="rpc_url", default=GOLEM_DB_RPC, help=f"Golem Base RPC URL (default: {GOLEM_DB_RPC})")
    ap.add_argument("--ws-url", dest="ws_url", default=GOLEM_DB_WSS, help=f"Golem Base WebSocket URL (default: {GOLEM_DB_WSS})")
    ap.add_argument("--private-key", dest="private_key", help="Private key for Golem Base authentication (overrides PRIVATE_KEY environment variable)")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true", help="Load and process files without creating entities")
    ap.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    args = ap.parse_args()

    # Check if directory exists
    if not os.path.isdir(args.in_dir):
        print(f"{color_text('✗', 'red')} Error: Directory '{args.in_dir}' does not exist")
        sys.exit(1)
    
    # Check if private key is set
    private_key = args.private_key or PRIVATE_KEY
    if not private_key and not args.dry_run:
        print(f"{color_text('✗', 'red')} Error: Private key is not set")
        print("Please provide a private key using --private-key argument or set PRIVATE_KEY environment variable")
        sys.exit(1)
    
    # Validate batch size and TTL
    if args.batch_size < 1:
        print(f"{color_text('✗', 'red')} Error: Batch size must be at least 1")
        sys.exit(1)
    
    if args.ttl < 1:
        print(f"{color_text('✗', 'red')} Error: TTL must be at least 1 second")
        sys.exit(1)
    
    if args.verbose:
        print(f"{color_text('➤', 'blue')} Starting NFT Metadata to Golem Base import...")
        print(f"Directory: {args.in_dir}")
        print(f"Batch size: {args.batch_size}")
        print(f"TTL: {args.ttl} seconds")
        print(f"Logs enabled: {not args.no_logs}")
        print(f"Dry run: {args.dry_run}")
        print()
    
    # Load metadata files
    metadata_files = load_metadata_files(args.in_dir)
    
    if not metadata_files:
        print(f"{color_text('✗', 'red')} No metadata files found in {args.in_dir}")
        print("Make sure the directory contains .json files")
        sys.exit(1)
    
    print(f"\n{color_text('✓', 'green')} Found {len(metadata_files)} metadata files")
    
    if args.dry_run:
        print(f"{color_text('ℹ', 'blue')} DRY RUN MODE - No entities will be created")
        print("\nFiles that would be processed:")
        for item in metadata_files[:5]:  # Show first 5 files
            print(f"  - {os.path.basename(item['file_path'])}")
        if len(metadata_files) > 5:
            print(f"  ... and {len(metadata_files) - 5} more files")
        print(f"\nWould create {len(metadata_files)} entities in batches of {args.batch_size}")
        return
    
    # Create a client to interact with the GolemDB API
    print(f"{color_text('➤', 'blue')} Initializing Golem DB client...")
    golem_base_client = await create_golem_client(
        rpc_url=args.rpc_url,
        ws_url=args.ws_url,
        private_key=private_key
    )

    try:
        # Write to Golem Base
        await write_metadata_to_golem(
            golem_base_client,
            metadata_files, 
            batch_size=args.batch_size,
            ttl=args.ttl,
            enable_logs=not args.no_logs
        )
        
        print(f"{color_text('✓', 'green')} Import completed!")
    finally:
        # Always disconnect the client when done
        print(f"{color_text('➤', 'blue')} Disconnecting Golem DB client...")
        await golem_base_client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{color_text('✗', 'red')} Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n{color_text('✗', 'red')} Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Print log summary if any logs were generated
        if info_count > 0 or warn_count > 0 or error_count > 0:
            print(f"\n{color_text('ℹ', 'blue')} Log summary: {color_text('[INFO]', 'blue')} {info_count}, {color_text('[WARN]', 'yellow')} {warn_count}, {color_text('[ERROR]', 'red')} {error_count}")
