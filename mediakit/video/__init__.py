"""
Video processing module for mediakit.
Provides video analysis, conversion, thumbnail and grid generation.
"""
from .info import VideoInfo
from .converter import (
    VideoConverter,
    VideoCodecDetector,
    VideoDurationProvider,
    CreationTimeHandler,
    ConversionResult,
)
from .thumbnail import (
    ThumbnailGenerator,
    FrameValidator,
    StepCalculator,
)
from .grid_generator import (
    VideoGridGenerator,
    GridSizeCalculator,
    FrameExtractor,
    GridComposer,
    generate_video_grid,
)
from ..core.interfaces import VideoGridConfig
from .sprite import (
    VideoSpriteGenerator,
    SpriteConfig,
    generate_video_sprites,
)

__all__ = [
    # Video info
    "VideoInfo",
    
    # Conversion
    "VideoConverter",
    "VideoCodecDetector",
    "VideoDurationProvider",
    "CreationTimeHandler",
    "ConversionResult",
    
    # Thumbnails
    "ThumbnailGenerator",
    "FrameValidator",
    "StepCalculator",
    
    # Grid generation
    "VideoGridGenerator",
    "VideoGridConfig",
    "GridSizeCalculator",
    "FrameExtractor",
    "GridComposer",
    "generate_video_grid",
    
    # Sprites
    "VideoSpriteGenerator",
    "SpriteConfig",
    "generate_video_sprites",
]
