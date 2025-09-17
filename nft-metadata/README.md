# NFT Metadata Flattener

Flatten NFT metadata files by converting nested attributes to flat fields.

## Features

- Turns `attributes: [{trait_type, value}, ...]` into flat fields with a prefix (default: "attr\_")
- Handles files with different / missing attributes
- Validates required fields and skips incomplete files
- Generates content hashes for data integrity
- Tracks media file usage statistics

## Usage

```bash
# Uses default directories: metadatas -> metadatas_flattened
python flatten_metadata.py

# Custom directories
python flatten_metadata.py --in ./metadata --out ./out

# Custom attribute prefix
python flatten_metadata.py --attr-prefix attr_

# Clean output directory before processing
python flatten_metadata.py --clean-out-dir
```

## Output

Creates flattened JSON files in the output directory with the same filenames as the input files.
