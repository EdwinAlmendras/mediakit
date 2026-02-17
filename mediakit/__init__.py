"""
MediaKit - Professional media processing toolkit.

A comprehensive library for processing image and video sets including:
- Image resizing to multiple quality levels
- Grid preview generation for images and videos
- Cover image selection
- 7-Zip archive creation
- Video conversion and thumbnail generation
- Video sprite sheet generation for players

Designed following SOLID principles and common design patterns.
Completely independent with no external project dependencies.

Example usage:
    from mediakit import SetProcessor
    
    processor = SetProcessor()
    
    # Process a complete image set
    metadata = processor.process(Path("my_set"))
    print(f"Processed {metadata.image_count} images")
    
    # Generate preview
    preview = processor.generate_preview(Path("my_set"))
    
    # Create archive
    archives = processor.create_archive(Path("my_set"), "my_set.7z")
    
    # Video processing
    from mediakit.video import VideoInfo, VideoGridGenerator
    
    info = VideoInfo(Path("video.mp4"))
    await info.load()
    print(f"Duration: {info.duration}s")
"""

from .set_processor import SetProcessor, SetProcessorConfig
from .core.interfaces import (
    SetMetadata,
    ImageDimensions,
    VideoDimensions,
    VideoMetadata,
    ResizeQuality,
    PreviewConfig,
    VideoGridConfig,
    VideoConversionConfig,
)
from .image import (
    ImageProcessor,
    ImageSelector,
    SetResizer,
    ResizeConfig,
    OrientationFixer,
)
from .preview import ImagePreviewGenerator, GridConfig
from .archive import SevenZipArchiver, ArchiveConfig
from .video import (
    VideoInfo,
    VideoConverter,
    ThumbnailGenerator,
    VideoGridGenerator,
    VideoSpriteGenerator,
    generate_video_grid,
    generate_video_sprites,
)
from .analyzer import analyze, analyze_video, analyze_photo, generate_id, sha256_file
from .image.info import ImageInfo
from .core.extensions import (
    VIDEO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    AUDIO_EXTENSIONS,
    ARCHIVE_EXTENSIONS,
    is_video,
    is_image,
    is_audio,
    is_archive,
    get_media_type,
)

__version__ = "1.0.0"

__all__ = [
    # Main facade
    "SetProcessor",
    "SetProcessorConfig",
    
    # Core types - Image
    "SetMetadata",
    "ImageDimensions",
    "ResizeQuality",
    "PreviewConfig",
    
    # Core types - Video
    "VideoDimensions",
    "VideoMetadata",
    "VideoGridConfig",
    "VideoConversionConfig",
    
    # Image processing
    "ImageProcessor",
    "ImageSelector", 
    "SetResizer",
    "ResizeConfig",
    "OrientationFixer",
    
    # Preview generation
    "ImagePreviewGenerator",
    "GridConfig",
    
    # Archiving
    "SevenZipArchiver",
    "ArchiveConfig",
    
    # Video processing
    "VideoInfo",
    "VideoConverter",
    "ThumbnailGenerator",
    "VideoGridGenerator",
    "VideoSpriteGenerator",
    "generate_video_grid",
    "generate_video_sprites",
    
    # Analyzer
    "ImageInfo",
    "analyze",
    "analyze_video",
    "analyze_photo",
    "generate_id",
    "sha256_file",
    
    # Extensions
    "VIDEO_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "AUDIO_EXTENSIONS",
    "ARCHIVE_EXTENSIONS",
    "is_video",
    "is_image",
    "is_audio",
    "is_archive",
    "get_media_type",
]
