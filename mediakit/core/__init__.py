"""
Core module - Interfaces, protocols, and data types for mediakit.
"""
from .interfaces import (
    # Enums
    ResizeQuality,
    
    # Data classes - Image
    ImageDimensions,
    SetMetadata,
    PreviewConfig,
    
    # Data classes - Video
    VideoDimensions,
    VideoMetadata,
    VideoGridConfig,
    VideoConversionConfig,
    
    # Abstract interfaces
    IImageProcessor,
    IImageSelector,
    IPreviewGenerator,
    IVideoPreviewGenerator,
    IArchiver,
    ISetResizer,
    ISetProcessor,
    IVideoInfoProvider,
    IVideoConverter,
    IThumbnailGenerator,
)

__all__ = [
    # Enums
    "ResizeQuality",
    
    # Data classes - Image
    "ImageDimensions",
    "SetMetadata",
    "PreviewConfig",
    
    # Data classes - Video
    "VideoDimensions",
    "VideoMetadata",
    "VideoGridConfig",
    "VideoConversionConfig",
    
    # Abstract interfaces
    "IImageProcessor",
    "IImageSelector",
    "IPreviewGenerator",
    "IVideoPreviewGenerator",
    "IArchiver",
    "ISetResizer",
    "ISetProcessor",
    "IVideoInfoProvider",
    "IVideoConverter",
    "IThumbnailGenerator",
]
