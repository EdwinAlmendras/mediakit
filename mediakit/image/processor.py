"""
Image processing operations.
Follows Open/Closed Principle - extensible through composition.
"""
from pathlib import Path
from typing import Optional
from PIL import Image
from PIL.ImageFile import ImageFile
import logging

from .orientation import OrientationFixer
from ..core.interfaces import IImageProcessor

logger = logging.getLogger(__name__)

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 1_000_000_000


class ImageProcessor(IImageProcessor):
    """Processes individual images with various transformations."""
    
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
    
    def __init__(self, default_quality: int = 90, progressive: bool = True):
        self.default_quality = default_quality
        self.progressive = progressive
        self.orientation_fixer = OrientationFixer()
    
    def fix_orientation(self, image_path: Path, output_path: Optional[Path] = None) -> Path:
        """Fix EXIF orientation."""
        return OrientationFixer.fix_file(image_path, output_path)
    
    def resize(self, image_path: Path, output_path: Path, max_size: int) -> Path:
        """Resize image to fit within max_size dimension while maintaining aspect ratio."""
        try:
            with Image.open(image_path) as img:
                fixed_img = OrientationFixer.fix_pil_image(img)
                resized = self._resize_image(fixed_img, max_size)
                self._save_image(resized, output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error resizing {image_path}: {e}")
            raise
    
    def _resize_image(self, img: Image.Image, max_size: int) -> Image.Image:
        """Resize image maintaining aspect ratio."""
        w, h = img.size
        
        if w <= max_size and h <= max_size:
            return img
        
        if w > h:
            new_w = max_size
            new_h = int(h * max_size / w)
        else:
            new_h = max_size
            new_w = int(w * max_size / h)
        
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    def _prepare_for_jpeg(self, img: Image.Image) -> Image.Image:
        """Convert image to RGB mode for JPEG saving."""
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[-1]
            background.paste(img.convert("RGB"), mask=alpha)
            return background
        if img.mode in ("P",):
            return img.convert("RGB")
        if img.mode not in ("RGB", "L"):
            return img.convert("RGB")
        return img
    
    def _save_image(self, img: Image.Image, output_path: Path) -> None:
        """Save image with appropriate format settings."""
        suffix = output_path.suffix.lower()
        
        if suffix in (".jpg", ".jpeg"):
            img_to_save = self._prepare_for_jpeg(img)
            img_to_save.save(
                output_path,
                format="JPEG",
                quality=self.default_quality,
                optimize=True,
                progressive=self.progressive
            )
        else:
            img.save(output_path)
    
    def smart_crop_to_square(self, image_path: Path, size: int) -> Image.Image:
        """Crop image to square, preserving important content."""
        with Image.open(image_path) as img:
            fixed_img = OrientationFixer.fix_pil_image(img)
            w, h = fixed_img.size
            
            if w == h:
                return fixed_img.resize((size, size), Image.Resampling.LANCZOS)
            elif w > h:
                crop_size = h
                left = (w - h) // 2
                cropped = fixed_img.crop((left, 0, left + crop_size, h))
            else:
                crop_size = w
                top = (h - w) // 4
                cropped = fixed_img.crop((0, top, w, top + crop_size))
            
            return cropped.resize((size, size), Image.Resampling.LANCZOS)
    
    @classmethod
    def is_valid_image(cls, path: Path) -> bool:
        """Check if path is a valid image file."""
        return path.is_file() and path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
