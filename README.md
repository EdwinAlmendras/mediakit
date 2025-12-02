# MediaKit

A professional Python toolkit for processing media sets including images and videos. Designed following SOLID principles and common design patterns.

## Features

### Image Processing
- **Batch Resizing**: Resize image sets to multiple quality levels (320px, 1280px, 2048px)
- **Grid Preview Generation**: Create visual grid previews from image collections
- **Cover Selection**: Automatically select the best cover image (prefers portrait JPEGs)
- **Orientation Fixing**: Correct EXIF orientation automatically
- **7-Zip Archiving**: Create encrypted, multi-part archives

### Video Processing
- **Video Information**: Extract detailed metadata using ffprobe
- **Video Conversion**: Convert videos to H.264/MP4 with smart preset selection
- **Thumbnail Generation**: Extract valid thumbnails (skips blank frames)
- **Grid Previews**: Generate visual grid previews from video frames
- **Sprite Sheets**: Generate sprite sheets with WebVTT for video player previews

## Installation

```bash
pip install mediakit
```

Or install from source:

```bash
git clone https://github.com/your-repo/mediakit.git
cd mediakit
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- Pillow >= 10.0.0
- natsort >= 8.0.0

**External tools** (for video processing):
- FFmpeg
- FFprobe
- 7-Zip (for archiving)

## Quick Start

### Image Set Processing

```python
from pathlib import Path
from mediakit import SetProcessor, SetProcessorConfig, ResizeQuality

# Configure processor
config = SetProcessorConfig(
    resize_qualities=[ResizeQuality.SMALL, ResizeQuality.MEDIUM],
    preview_cell_size=400,
)

processor = SetProcessor(config)

# Process a complete image set
metadata = processor.process(Path("my_image_set"))
print(f"Processed {metadata.image_count} images")
print(f"Max dimensions: {metadata.max_dimensions.width}x{metadata.max_dimensions.height}")

# Generate preview
preview = processor.generate_preview(Path("my_image_set"))

# Create encrypted archive
archives = processor.create_archive(
    Path("my_image_set"), 
    "output.7z", 
    password="secret"
)
```

### Video Processing

```python
import asyncio
from pathlib import Path
from mediakit.video import (
    VideoInfo,
    VideoConverter,
    ThumbnailGenerator,
    generate_video_grid,
)

async def process_video(video_path: Path):
    # Get video information
    info = VideoInfo(video_path)
    await info.load()
    
    print(f"Duration: {info.duration}s")
    print(f"Resolution: {info.width}x{info.height}")
    print(f"Codec: {info.codec}")
    
    # Generate thumbnail
    thumb_gen = ThumbnailGenerator()
    thumbnail = thumb_gen.generate(video_path)
    
    # Generate grid preview
    grid = await generate_video_grid(
        video_path,
        grid_size=4,
        max_size=480
    )
    
    return thumbnail, grid

# Run
asyncio.run(process_video(Path("my_video.mp4")))
```

### Video Conversion

```python
from pathlib import Path
from mediakit.video import VideoConverter

converter = VideoConverter()

# Check if conversion is needed
if converter.needs_conversion(Path("input.mkv")):
    output = converter.convert(Path("input.mkv"))
    print(f"Converted to: {output}")
```

## Architecture

MediaKit follows SOLID principles and common design patterns:

### Design Patterns Used

- **Facade Pattern**: `SetProcessor` provides a unified API for all set operations
- **Strategy Pattern**: `ImageSelector` supports pluggable selection strategies
- **Factory Pattern**: Configuration objects create properly configured components
- **Interface Segregation**: Small, focused interfaces in `core.interfaces`

### Module Structure

```
mediakit/
├── core/
│   └── interfaces.py      # Abstract interfaces and data types
├── image/
│   ├── processor.py       # Image transformations
│   ├── selector.py        # Image selection strategies
│   ├── resizer.py         # Batch resizing with parallel processing
│   └── orientation.py     # EXIF orientation handling
├── preview/
│   └── image_preview.py   # Grid preview generation
├── archive/
│   └── sevenzip.py        # 7-Zip archive creation
├── video/
│   ├── info.py            # Video metadata extraction
│   ├── converter.py       # Video conversion
│   ├── thumbnail.py       # Thumbnail generation
│   ├── grid_generator.py  # Video grid previews
│   └── sprite.py          # Sprite sheet generation
└── set_processor.py       # Main facade
```

## API Reference

### Core Types

#### `ImageDimensions`
```python
@dataclass
class ImageDimensions:
    width: int
    height: int
    
    @property
    def megapixels(self) -> float: ...
    @property
    def aspect_ratio(self) -> float: ...
    @property
    def is_portrait(self) -> bool: ...
```

#### `ResizeQuality`
```python
class ResizeQuality(Enum):
    SMALL = 320    # Thumbnails
    MEDIUM = 1280  # Web display
    LARGE = 2048   # High quality
```

### Image Components

#### `ImageProcessor`
```python
processor = ImageProcessor(default_quality=90)
processor.resize(image_path, output_path, max_size=1280)
processor.fix_orientation(image_path)
processor.smart_crop_to_square(image_path, size=400)
```

#### `ImageSelector`
```python
selector = ImageSelector()
images = selector.get_images(folder, recursive=False)
cover = selector.select_cover(images)
distributed = selector.select_distributed(images, count=12)
```

### Video Components

#### `VideoInfo`
```python
info = VideoInfo(video_path)
await info.load()  # Async loading

# Properties
info.duration      # float (seconds)
info.width         # int (with SAR correction)
info.height        # int
info.codec         # str
info.fps           # float
info.rotation      # int (degrees)
info.dimensions    # VideoDimensions
```

#### `VideoConverter`
```python
converter = VideoConverter(config=VideoConversionConfig(...))
converter.needs_conversion(video_path)  # Check codec/container
converter.convert(input_path, output_path)  # Smart conversion
converter.convert_to_h264(input_path, output_path)  # Force H.264
```

#### `VideoGridGenerator`
```python
config = VideoGridConfig(grid_size=4, max_size=480)
generator = VideoGridGenerator(video_path, config)
grid_path = await generator.generate()
```

## Development

### Setup

```bash
git clone https://github.com/your-repo/mediakit.git
cd mediakit
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ -v --cov=mediakit --cov-report=html
```

### Code Quality

```bash
# Type checking
mypy mediakit/

# Linting
ruff check mediakit/

# Format
ruff format mediakit/
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Changelog

### v1.0.0
- Initial release
- Image set processing with batch resizing
- Grid preview generation
- 7-Zip archive creation
- Video metadata extraction
- Video conversion with smart codec detection
- Video thumbnail and grid preview generation
- Sprite sheet generation for video players
