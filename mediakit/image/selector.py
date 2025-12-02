"""
Image selection strategies.
Follows Strategy Pattern for different selection algorithms.
"""
from pathlib import Path
from typing import List, Optional, Protocol
from PIL import Image
from natsort import natsorted
import logging

from ..core.interfaces import IImageSelector
from .processor import ImageProcessor

logger = logging.getLogger(__name__)


class SelectionStrategy(Protocol):
    """Protocol for image selection strategies."""
    def select(self, images: List[Path], count: int) -> List[Path]: ...


class DistributedSelection:
    """Selects evenly distributed images from the list."""
    
    def select(self, images: List[Path], count: int) -> List[Path]:
        if len(images) <= count:
            return images[:count]
        
        step = len(images) / count
        return [images[int(i * step)] for i in range(count)]


class RandomSelection:
    """Selects random images from the list."""
    
    def select(self, images: List[Path], count: int) -> List[Path]:
        import random
        if len(images) <= count:
            return images[:count]
        
        return random.sample(images, count)


class ImageSelector(IImageSelector):
    """
    Selects images from folders using configurable strategies.
    Follows Open/Closed Principle - new strategies can be added without modification.
    """
    
    IGNORED_FOLDERS = {'m', 'x', 'xl', '.previews', '.covers'}
    
    def __init__(self, selection_strategy: Optional[SelectionStrategy] = None):
        self.selection_strategy = selection_strategy or DistributedSelection()
    
    def get_images(self, folder: Path, recursive: bool = False) -> List[Path]:
        """Get all valid image files from folder."""
        if recursive:
            images = [
                f for f in folder.rglob('*')
                if ImageProcessor.is_valid_image(f)
                and not self._is_in_ignored_folder(f)
            ]
        else:
            images = [
                f for f in folder.iterdir()
                if ImageProcessor.is_valid_image(f)
            ]
        
        return natsorted(images)
    
    def _is_in_ignored_folder(self, path: Path) -> bool:
        """Check if path is within an ignored folder."""
        return any(ignored in path.parts for ignored in self.IGNORED_FOLDERS)
    
    def select_cover(self, images: List[Path]) -> Path:
        """
        Select the best image for cover.
        Prefers vertical JPEG images.
        """
        if not images:
            raise ValueError("No images provided for cover selection")
        
        sorted_images = natsorted(images)
        
        for pic in sorted_images:
            try:
                with Image.open(pic) as img:
                    width, height = img.size
                    if pic.suffix.lower() in (".jpg", ".jpeg") and height > width:
                        return pic
            except Exception as e:
                logger.warning(f"Corrupt image skipped: {pic.name} - {e}")
                continue
        
        return sorted_images[0]
    
    def select_distributed(self, images: List[Path], count: int) -> List[Path]:
        """Select evenly distributed images."""
        return self.selection_strategy.select(images, count)
    
    def with_strategy(self, strategy: SelectionStrategy) -> 'ImageSelector':
        """Return new selector with different strategy (Fluent interface)."""
        return ImageSelector(strategy)
