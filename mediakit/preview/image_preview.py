"""
Grid preview generator for image sets.
Creates visual grid previews from a collection of images.
"""
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image
import tempfile
import random
import logging

from ..core.interfaces import IPreviewGenerator, PreviewConfig
from ..image.selector import ImageSelector
from ..image.processor import ImageProcessor

logger = logging.getLogger(__name__)


@dataclass
class GridConfig:
    """Configuration for grid generation."""
    rows: int = 4
    cols: int = 3
    cell_size: int = 400
    randomize: bool = False
    recursive: bool = False
    
    @property
    def max_images(self) -> int:
        return self.rows * self.cols


class GridLayoutCalculator:
    """Calculates optimal grid layout based on image count."""
    
    @staticmethod
    def calculate(total_images: int) -> Tuple[int, int]:
        """Returns (rows, cols) for optimal vertical layout."""
        if total_images < 50:
            return (4, 3)
        else:
            return (5, 3)


class GridComposer:
    """Composes final grid image from individual images."""
    
    def __init__(self, cell_size: int = 400):
        self.cell_size = cell_size
        self.processor = ImageProcessor()
    
    def compose(self, image_paths: List[Path], rows: int, cols: int) -> Image.Image:
        """Create grid from selected images."""
        grid_width = cols * self.cell_size
        grid_height = rows * self.cell_size
        
        grid = Image.new('RGB', (grid_width, grid_height), color='white')
        
        for i, img_path in enumerate(image_paths):
            if i >= rows * cols:
                break
            
            row = i // cols
            col = i % cols
            
            try:
                square = self.processor.smart_crop_to_square(img_path, self.cell_size)
                x = col * self.cell_size
                y = row * self.cell_size
                grid.paste(square, (x, y))
            except Exception as e:
                logger.warning(f"Error processing {img_path.name}: {e}")
                continue
        
        return grid


class ImagePreviewGenerator(IPreviewGenerator):
    """
    Generates grid preview images from a set of images.
    Facade that orchestrates selection, layout calculation, and composition.
    """
    
    def __init__(self, cell_size: int = 400):
        self.cell_size = cell_size
        self.selector = ImageSelector()
        self.layout_calculator = GridLayoutCalculator()
        self.composer = GridComposer(cell_size)
    
    def generate(
        self, 
        folder: Path, 
        output_path: Optional[Path] = None,
        config: Optional[GridConfig] = None
    ) -> Path:
        """
        Generate grid preview for an image set.
        
        Args:
            folder: Folder containing images
            output_path: Output file path (uses temp if not specified)
            config: Grid configuration options
            
        Returns:
            Path to generated preview image
        """
        config = config or GridConfig()
        
        images = self.selector.get_images(folder, recursive=config.recursive)
        
        if not images:
            raise ValueError(f"No images found in {folder}")
        
        if config.randomize:
            images = images.copy()
            random.shuffle(images)
        
        rows, cols = config.rows, config.cols
        if rows == 4 and cols == 3:
            rows, cols = self.layout_calculator.calculate(len(images))
        
        max_images = rows * cols
        selected = self.selector.select_distributed(images, max_images)
        
        grid = self.composer.compose(selected, rows, cols)
        
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            output_path = Path(temp_file.name)
            temp_file.close()
        
        grid.save(output_path, 'JPEG', quality=85, optimize=True)
        
        logger.info(f"Preview generated: {output_path}")
        logger.info(f"Grid: {rows}x{cols} ({len(selected)}/{len(images)} images)")
        
        return output_path
    
    def generate_from_images(
        self,
        images: List[Path],
        output_path: Optional[Path] = None,
        config: Optional[GridConfig] = None
    ) -> Path:
        """Generate preview from a specific list of images."""
        config = config or GridConfig()
        
        if not images:
            raise ValueError("No images provided")
        
        if config.randomize:
            images = images.copy()
            random.shuffle(images)
        
        rows, cols = config.rows, config.cols
        max_images = rows * cols
        selected = self.selector.select_distributed(images, max_images)
        
        grid = self.composer.compose(selected, rows, cols)
        
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            output_path = Path(temp_file.name)
            temp_file.close()
        
        grid.save(output_path, 'JPEG', quality=85, optimize=True)
        
        return output_path
