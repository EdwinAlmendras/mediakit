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
    
    def __init__(self, input_path: Path):
        self.input_path = Path(input_path)
        self._loaded = False
        self._exif = {}
    
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
            
            # Handle EXIF orientation
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
            except Exception:
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
