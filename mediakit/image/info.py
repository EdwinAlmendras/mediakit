"""
Image information extraction.
"""
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import logging

from .quality import estimate_quality
from .perceptual import calculate_phash, calculate_avg_color_lab

logger = logging.getLogger(__name__)


@dataclass
class ImageInfo:
    """Extracts and provides image metadata."""
    
    input_path: Path
    _loaded: bool = False
    _width: int = 0
    _height: int = 0
    _format: str = ""
    _mode: str = ""
    _exif: Dict[str, Any] = None
    _quality: Optional[int] = None
    _phash: Optional[str] = None
    _avg_color_lab: Optional[list[float]] = None
    
    def __init__(self, input_path: Path, phash: Optional[str] = None, avg_color_lab: Optional[list[float]] = None):
        self.input_path = Path(input_path)
        self._loaded = False
        self._exif = {}
        # Allow pre-calculated values to be passed (for optimization)
        self._phash = phash
        self._avg_color_lab = avg_color_lab
    
    def load(self) -> None:
        """Load image metadata."""
        if self._loaded:
            return
        
        if not self.input_path.exists():
            raise ValueError(f"Image file does not exist: {self.input_path}")
        
        with Image.open(self.input_path) as img:
            self._width, self._height = img.size
            self._format = img.format or ""
            self._mode = img.mode
            
            # Handle EXIF orientation and extract metadata
            try:
                exif = img.getexif()
                orientation = exif.get(0x0112)
                if orientation in (6, 8):
                    self._width, self._height = self._height, self._width
                
                # Extract all EXIF tags
                for tag_id, value in exif.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    try:
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        self._exif[tag_name] = value
                    except Exception:
                        pass
                
                # Calculate JPEG quality if available (JPEG quantization table)
                if self._format.upper() in ("JPEG", "JPG"):
                    try:
                        # Try to get quantization table from EXIF
                        # JPEG quantization tables are typically in tag 0x0102 (JPEGQTables)
                        # or we can try to get it from the image's quantize attribute
                        quant_table = None
                        
                        # Method 1: Try EXIF tag 0x0102 (JPEGQTables)
                        if 0x0102 in exif:
                            quant_table = exif[0x0102]
                        # Method 2: Try to get from image's quantize attribute (if available)
                        elif hasattr(img, 'quantization') and img.quantization:
                            # PIL stores quantization tables as dict with keys 0 (luma) and 1 (chroma)
                            # We use the luma table (key 0)
                            quant_table = img.quantization[0]
                        if quant_table:
                            # quant_table should be a list/array of 64 values (8x8 block)
                            if isinstance(quant_table, (list, tuple)) and len(quant_table) == 64:
                                self._quality = estimate_quality(quant_table)
                    except Exception as e:
                        logger.debug(f"Could not estimate JPEG quality: {e}")
                        pass
            except Exception:
                pass
        
        # Calculate perceptual features (pHash and avg_color LAB) only if not already provided
        # These are calculated after closing the image since the functions open it themselves
        if self._phash is None or self._avg_color_lab is None:
            try:
                # Calculate pHash (perceptual hash for near-duplicate detection) if not provided
                if self._phash is None:
                    self._phash = calculate_phash(self.input_path)
                
                # Calculate average color in LAB space (perceptually uniform) if not provided
                if self._avg_color_lab is None:
                    self._avg_color_lab = calculate_avg_color_lab(self.input_path)
            except Exception as e:
                logger.debug(f"Could not calculate perceptual features: {e}")
                pass
        
        self._loaded = True
    
    def _ensure_loaded(self) -> None:
        if not self._loaded:
            raise RuntimeError("ImageInfo not loaded. Call load() first.")
    
    @property
    def width(self) -> int:
        self._ensure_loaded()
        return self._width
    
    @property
    def height(self) -> int:
        self._ensure_loaded()
        return self._height
    
    @property
    def format(self) -> str:
        self._ensure_loaded()
        return self._format
    
    @property
    def mode(self) -> str:
        self._ensure_loaded()
        return self._mode
    
    @property
    def orientation(self) -> Optional[int]:
        self._ensure_loaded()
        return self._exif.get("Orientation")
    
    @property
    def camera(self) -> Optional[str]:
        self._ensure_loaded()
        make = self._exif.get("Make", "")
        model = self._exif.get("Model", "")
        return f"{make} {model}".strip() or None
    
    @property
    def creation_date(self) -> Optional[datetime]:
        self._ensure_loaded()
        date_str = self._exif.get("DateTimeOriginal") or self._exif.get("DateTime")
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
        return None
    
    @property
    def tags(self) -> Dict[str, Any]:
        self._ensure_loaded()
        return self._exif.copy()
    
    @property
    def quality(self) -> Optional[int]:
        """
        Estimated JPEG quality (1-100).
        
        Only available for JPEG images with quantization tables in EXIF.
        Returns None for non-JPEG images or if quality cannot be estimated.
        """
        self._ensure_loaded()
        return self._quality
    
    @property
    def phash(self) -> Optional[str]:
        """
        Perceptual hash (pHash) for near-duplicate detection.
        
        Returns a hexadecimal string (64 characters for 8x8 hash).
        Useful for finding similar/duplicate images.
        """
        self._ensure_loaded()
        return self._phash
    
    @property
    def avg_color_lab(self) -> Optional[list[float]]:
        """
        Average color in LAB color space [L, a, b].
        
        LAB is perceptually uniform, ideal for color-based filtering.
        - L: Lightness (0-100)
        - a: Green-Red axis (-128 to 127)
        - b: Blue-Yellow axis (-128 to 127)
        """
        self._ensure_loaded()
        return self._avg_color_lab
