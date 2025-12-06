"""
Abstract interfaces following Interface Segregation Principle (SOLID).
Defines contracts for all mediakit components.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ResizeQuality(Enum):
    """Quality levels for image resizing."""
    SMALL = 320
    MEDIUM = 1280
    LARGE = 2048


@dataclass
class ImageDimensions:
    """Represents image dimensions with utility properties."""
    width: int
    height: int
    
    @property
    def min_dimension(self) -> int:
        return min(self.width, self.height)
    
    @property
    def max_dimension(self) -> int:
        return max(self.width, self.height)
    
    @property
    def megapixels(self) -> float:
        return (self.width * self.height) / 1_000_000
    
    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0
    
    @property
    def is_portrait(self) -> bool:
        return self.height > self.width
    
    @property
    def is_landscape(self) -> bool:
        return self.width > self.height


@dataclass
class VideoDimensions:
    """Represents video dimensions with display and rotation info."""
    width: int
    height: int
    display_width: int = 0
    display_height: int = 0
    rotation: int = 0
    
    def __post_init__(self):
        if self.display_width == 0:
            self.display_width = self.width
        if self.display_height == 0:
            self.display_height = self.height


@dataclass
class VideoMetadata:
    """Complete video metadata."""
    path: Path
    duration: float
    dimensions: VideoDimensions
    codec: str
    fps: float
    bitrate: int = 0
    frame_count: int = 0


@dataclass
class SetMetadata:
    """Metadata for an image set."""
    path: Path
    image_count: int
    max_dimensions: ImageDimensions
    cover_path: Optional[Path] = None


@dataclass
class PreviewConfig:
    """Configuration for preview generation."""
    rows: int = 4
    cols: int = 3
    cell_size: int = 400
    randomize: bool = False


@dataclass
class VideoGridConfig:
    """Configuration for video grid generation."""
    grid_size: int = 4
    max_size: int = 480
    max_parallel: int = 2
    quality: int = 70


@dataclass
class VideoConversionConfig:
    """Configuration for video conversion."""
    codec: str = "libx264"
    preset: str = "fast"
    crf: int = 18
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    supported_codecs: List[str] = field(default_factory=lambda: ["h264", "hevc", "vp9", "av1"])
    supported_extensions: List[str] = field(default_factory=lambda: [".mp4", ".mov"])


class IImageProcessor(ABC):
    """Interface for image processing operations."""
    
    @abstractmethod
    def fix_orientation(self, image_path: Path, output_path: Optional[Path] = None) -> Path:
        """Fix EXIF orientation of an image."""
        pass
    
    @abstractmethod
    def resize(self, image_path: Path, output_path: Path, max_size: int) -> Path:
        """Resize an image to fit within max_size dimension."""
        pass


class IImageSelector(ABC):
    """Interface for image selection operations."""
    
    @abstractmethod
    def get_images(self, folder: Path, recursive: bool = False) -> List[Path]:
        """Get all valid image files from folder."""
        pass
    
    @abstractmethod
    def select_cover(self, images: List[Path]) -> Path:
        """Select the best image for cover."""
        pass
    
    @abstractmethod
    def select_distributed(self, images: List[Path], count: int) -> List[Path]:
        """Select evenly distributed images."""
        pass


class IPreviewGenerator(ABC):
    """Interface for preview generation."""
    
    @abstractmethod
    def generate(
        self, 
        folder: Path, 
        output_path: Optional[Path] = None, 
        config: Optional[PreviewConfig] = None
    ) -> Path:
        """Generate a preview image/video."""
        pass


class IVideoPreviewGenerator(ABC):
    """Interface for video preview generation."""
    
    @abstractmethod
    async def generate(self, output_path: Optional[Path] = None) -> Path:
        """Generate video grid preview asynchronously."""
        pass


class IArchiver(ABC):
    """Interface for archive creation."""
    
    @abstractmethod
    def create(
        self, 
        folder: Path, 
        output_name: str, 
        password: Optional[str] = None, 
        max_part_size: Optional[int] = None
    ) -> List[Path]:
        """Create archive from folder."""
        pass
    
    @abstractmethod
    def validate(self, archive_path: Path) -> bool:
        """Validate archive integrity."""
        pass


class ISetResizer(ABC):
    """Interface for batch image resizing."""
    
    @abstractmethod
    def resize_set(self, folder: Path, qualities: List[ResizeQuality]) -> None:
        """Resize all images in set to specified qualities."""
        pass
    
    @abstractmethod
    def get_dimensions(self, folder: Path) -> ImageDimensions:
        """Analyze and return max dimensions of images in folder."""
        pass


class ISetProcessor(ABC):
    """Interface for complete set processing."""
    
    @abstractmethod
    def process(self, folder: Path) -> SetMetadata:
        """Process a complete set (resize, generate previews, etc.)."""
        pass
    
    @abstractmethod
    def generate_preview(self, folder: Path, output_path: Optional[Path] = None) -> Path:
        """Generate preview for set."""
        pass
    
    @abstractmethod
    def select_cover(self, folder: Path) -> Path:
        """Select cover image for set."""
        pass


class IVideoInfoProvider(ABC):
    """Interface for video information extraction."""
    
    @abstractmethod
    async def load(self) -> None:
        """Load video metadata asynchronously."""
        pass
    
    @property
    @abstractmethod
    def duration(self) -> float:
        """Video duration in seconds."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> VideoDimensions:
        """Video dimensions."""
        pass
    
    @property
    @abstractmethod
    def codec(self) -> str:
        """Video codec name."""
        pass


class IVideoConverter(ABC):
    """Interface for video conversion operations."""
    
    @abstractmethod
    def convert(self, input_path: Path, output_path: Path) -> Path:
        """Convert video to target format."""
        pass
    
    @abstractmethod
    def needs_conversion(self, video_path: Path) -> bool:
        """Check if video needs conversion."""
        pass


class IThumbnailGenerator(ABC):
    """Interface for video thumbnail generation."""
    
    @abstractmethod
    def generate(self, video_path: Path, output_path: Optional[Path] = None) -> Path:
        """Generate thumbnail from video."""
        pass
    
    @abstractmethod
    async def generate_async(
        self, 
        video_path: Path, 
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate thumbnail asynchronously."""
        pass
