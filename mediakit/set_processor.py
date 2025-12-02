"""
SetProcessor - Main facade for processing image sets.
Orchestrates resizing, preview generation, cover selection, and archiving.
Follows Facade Pattern for simplified API.
"""
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from PIL import Image
import logging

from .core.interfaces import (
    ISetProcessor, 
    SetMetadata, 
    ImageDimensions,
    ResizeQuality,
    PreviewConfig
)
from .image.selector import ImageSelector
from .image.resizer import SetResizer, ResizeConfig
from .image.processor import ImageProcessor
from .preview.image_preview import ImagePreviewGenerator, GridConfig
from .archive.sevenzip import SevenZipArchiver, ArchiveConfig

logger = logging.getLogger(__name__)


@dataclass
class SetProcessorConfig:
    """Configuration for set processing."""
    resize_qualities: List[ResizeQuality] = None
    preview_cell_size: int = 400
    archive_compression: int = 0
    archive_max_part_size: Optional[int] = None
    
    def __post_init__(self):
        if self.resize_qualities is None:
            self.resize_qualities = [ResizeQuality.SMALL, ResizeQuality.MEDIUM, ResizeQuality.LARGE]


class SetProcessor(ISetProcessor):
    """
    Main facade for processing image sets.
    Provides unified API for all set operations.
    
    Example:
        processor = SetProcessor()
        
        # Full processing
        metadata = processor.process(Path("my_set"))
        
        # Individual operations
        cover = processor.select_cover(Path("my_set"))
        preview = processor.generate_preview(Path("my_set"))
        archives = processor.create_archive(Path("my_set"), "my_set.7z")
    """
    
    def __init__(self, config: Optional[SetProcessorConfig] = None):
        self.config = config or SetProcessorConfig()
        
        self.selector = ImageSelector()
        self.resizer = SetResizer(ResizeConfig(qualities=self.config.resize_qualities))
        self.processor = ImageProcessor()
        self.preview_generator = ImagePreviewGenerator(self.config.preview_cell_size)
        self.archiver = SevenZipArchiver(ArchiveConfig(
            compression_level=self.config.archive_compression,
            max_part_size=self.config.archive_max_part_size
        ))
    
    def process(self, folder: Path) -> SetMetadata:
        """
        Process a complete set: analyze, resize, and prepare metadata.
        
        Args:
            folder: Path to the image set folder
            
        Returns:
            SetMetadata with processing results
        """
        folder = Path(folder)
        logger.info(f"Processing set: {folder.name}")
        
        images = self.selector.get_images(folder)
        if not images:
            raise ValueError(f"No images found in {folder}")
        
        dimensions = self.resizer.get_dimensions(folder, images)
        
        self.resizer.resize_set(folder)
        
        cover = self.selector.select_cover(images)
        
        return SetMetadata(
            path=folder,
            image_count=len(images),
            max_dimensions=dimensions,
            cover_path=cover
        )
    
    def generate_preview(
        self, 
        folder: Path, 
        output_path: Optional[Path] = None,
        recursive: bool = False,
        randomize: bool = False,
        rows: int = None,
        cols: int = None
    ) -> Path:
        """Generate grid preview for the set."""
        config = GridConfig(
            rows=rows or 4,
            cols=cols or 3,
            cell_size=self.config.preview_cell_size,
            randomize=randomize,
            recursive=recursive
        )
        return self.preview_generator.generate(folder, output_path, config)
    
    def select_cover(self, folder: Path) -> Path:
        """Select the best cover image from the set."""
        images = self.selector.get_images(folder)
        if not images:
            raise ValueError(f"No images found in {folder}")
        return self.selector.select_cover(images)
    
    def resize(self, folder: Path, qualities: Optional[List[ResizeQuality]] = None) -> None:
        """Resize all images in set to specified qualities."""
        self.resizer.resize_set(folder, qualities)
    
    def create_archive(
        self, 
        folder: Path, 
        output_name: str,
        password: Optional[str] = None,
        max_part_size: Optional[int] = None
    ) -> List[Path]:
        """Create 7z archive of the set."""
        max_part_size = max_part_size or self.config.archive_max_part_size
        return self.archiver.create(folder, output_name, password, max_part_size)
    
    def get_metadata(self, folder: Path) -> SetMetadata:
        """Get metadata without processing."""
        folder = Path(folder)
        images = self.selector.get_images(folder)
        
        if not images:
            raise ValueError(f"No images found in {folder}")
        
        dimensions = self.resizer.get_dimensions(folder, images)
        cover = self.selector.select_cover(images)
        
        return SetMetadata(
            path=folder,
            image_count=len(images),
            max_dimensions=dimensions,
            cover_path=cover
        )
    
    def get_caption(self, folder: Path, include_date: bool = True) -> str:
        """
        Generate caption for the set.
        
        Args:
            folder: Path to the set
            include_date: Whether to include file date in caption
            
        Returns:
            Caption string like "2.5 MP - 150 pics - 2024.01.15"
        """
        images = self.selector.get_images(folder)
        if not images:
            return ""
        
        cover = self.selector.select_cover(images)
        
        with Image.open(cover) as img:
            mp = (img.width * img.height) / 1_000_000
            mp_str = f"{mp:.2f}".rstrip("0").rstrip(".")
        
        caption = f"{mp_str} MP - {len(images)} pics"
        
        if include_date:
            file_ctime = cover.stat().st_ctime
            file_mtime = cover.stat().st_mtime
            min_date = min(file_ctime, file_mtime)
            date_str = datetime.fromtimestamp(min_date).strftime("%Y.%m.%d")
            today = datetime.now().strftime("%Y.%m.%d")
            
            if date_str != today:
                caption += f" - {date_str}"
        
        return caption
