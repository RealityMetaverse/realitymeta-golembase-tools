# Reality Meta Golem Base Tools

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![Status](https://img.shields.io/badge/status-under%20development-orange)

File tracking and management system for Golem Base. Upload any file type, track changes, and recreate files locally with comprehensive metadata extraction.

## Features

- **Universal File Support**: Handle any file type with basic metadata extraction
- **Special File Types**: Enhanced metadata extraction for images, audio, video, text, and JSON files
- **Change Tracking**: Monitor file modifications and update database entries
- **Local Recreation**: Recreate original files from database entries
- **Content Integrity**: Hash-based duplicate detection
- **NFT Metadata Processing**: Flatten nested attributes to flat fields

## File Type Support

### Special Treatment (Enhanced Metadata)
**Images, Audio, Video, Text, and JSON files** receive comprehensive metadata extraction:

#### Images
- Resolution (width, height)
- Format (PNG, JPEG, etc.)
- Color mode (RGB, RGBA, L, etc.)
- Transparency support (has_alpha)
- Frame count (for animated formats like GIF)
- Palette information

#### Audio
- Duration (in seconds)
- Bitrate (bits per second)
- Sample rate (e.g., 44100, 48000)
- Channels (1=mono, 2=stereo)
- Codec type (MP3Info, FLACInfo, etc.)
- Mode and version information
- Layer information

#### Video
- Resolution (width, height)
- Duration (in seconds)
- Video codec (h264, vp9, etc.)
- Frame rate
- Format (mov, mp4, etc.)
- Audio track presence
- Audio codec and sample rate
- Pixel format
- Bitrate

#### Text
- Content (full text)
- Character, word, and line counts
- Encoding detection (UTF-8, latin-1, etc.)
- Empty file detection

#### JSON
- NFT metadata detection
- Attribute flattening (trait_type → attr_trait_type)
- Reality NFT metadata validation
- Schema validation

### General Files
**Any other file type** receives basic metadata extraction (file size, modification time, MIME type, etc.)

## Commands

### Create Entities (Testing)
```bash
./create_rmgb_entries --in-dir ./database
```
*Converts files to Reality Meta Golem Base entries for testing purposes*

### Update Database
```bash
./update-database --in-dir ./database --batch-size 15 --ttl 86400
```

### Recreate Files
```bash
./recreate_files_from_database --output-dir ./recreated --version 1
```

## Configuration

- **File Size Limit**: 130KB per file (140KB total - 10KB metadata reserve)
- **Attribute Prefix**: `attr_` for NFT metadata attributes
- **Golem Base Values**: `null`, `true`, `false`
- **Empty Files**: Automatically skipped
- **Missing NFT Fields**: Files with incomplete metadata are skipped

## PLANNED IMPROVEMENTS

- Prevent multiple file handles for same file during entity creation
- Enhanced logging with type-based log filtering


## UP TO DISCUSSION

- Return without `_` prefix in field names
- Compress file before encoding (works best for text files, minimal benefit for media files)

## MUST KNOW

- **Golem Base Values**: Cannot use golem base values as string values
- **Attribute Prefix**: Cannot use `attr_` in JSON if attributes field exists
- **File Handling**: Files skipped if empty or missing required NFT metadata fields
- **Entity Fields**: Reality Meta Golem Base Entity fields are read-only after initialization
- **Size Limits**: 130KB file size limit (140KB total - 10KB metadata reserve)
- **Encoding**: Base64 encoding with 1.34x expansion factor
