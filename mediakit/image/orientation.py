"""
Image orientation correction using EXIF data.
Follows Single Responsibility Principle - only handles orientation.
"""
from pathlib import Path
from typing import Optional
from PIL import Image, ExifTags
import logging

logger = logging.getLogger(__name__)


class OrientationFixer:
    """Fixes image orientation based on EXIF metadata."""
    
    ORIENTATION_TAG = 'Orientation'
    
    _TRANSFORMS = {
        2: lambda img: img.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        3: lambda img: img.rotate(180, expand=True),
        4: lambda img: img.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
        5: lambda img: img.rotate(-90, expand=True).transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        6: lambda img: img.rotate(-90, expand=True),
        7: lambda img: img.rotate(90, expand=True).transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        8: lambda img: img.rotate(90, expand=True),
    }
    
    @classmethod
    def _get_orientation_key(cls) -> Optional[int]:
        """Get the EXIF orientation tag key."""
        for tag, value in ExifTags.TAGS.items():
            if value == cls.ORIENTATION_TAG:
                return tag
        return None
    
    @classmethod
    def fix_pil_image(cls, img: Image.Image) -> Image.Image:
        """Fix orientation of a PIL Image object."""
        try:
            exif = getattr(img, "_getexif", lambda: None)()
            if exif is None:
                return img
            
            orientation_key = cls._get_orientation_key()
            if orientation_key is None or orientation_key not in exif:
                return img
            
            orientation = exif[orientation_key]
            transform = cls._TRANSFORMS.get(orientation)
            if transform:
                return transform(img)
                
        except Exception as e:
            logger.warning(f"Error fixing orientation: {e}")
        
        return img
    
    @classmethod
    def fix_file(cls, image_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Fix orientation of an image file.
        
        Args:
            image_path: Source image path
            output_path: Output path (defaults to overwriting source)
            
        Returns:
            Path to the fixed image
        """
        output_path = output_path or image_path
        
        try:
            with Image.open(image_path) as img:
                fixed = cls.fix_pil_image(img)
                fixed.save(output_path, exif=b'')
            return output_path
        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return image_path
