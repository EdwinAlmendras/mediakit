"""
Batch image resizing for sets.
Follows Single Responsibility and uses parallel processing.
"""
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from PIL import Image
import gc
import time
import logging
import subprocess
import tempfile

from ..core.interfaces import ISetResizer, ResizeQuality, ImageDimensions
from .processor import ImageProcessor
from .orientation import OrientationFixer

logger = logging.getLogger(__name__)


@dataclass
class ResizeConfig:
    """Configuration for set resizing."""
    qualities: List[ResizeQuality] = None
    max_workers: Optional[int] = None
    batch_size: int = 100
    output_format: str = "jpg"
    
    def __post_init__(self):
        if self.qualities is None:
            self.qualities = [ResizeQuality.SMALL]


def _process_single_image(args: Tuple[Path, Dict[str, Tuple[Path, int]]]) -> str:
    """Worker function for parallel processing (must be top-level for pickling)."""
    image_path, output_info = args
    
    try:
        with Image.open(image_path) as img:
            fixed_img = OrientationFixer.fix_pil_image(img)
            
            for size_name, (output_path, target_size) in output_info.items():
                if target_size > 0:
                    _resize_and_save(fixed_img, output_path, target_size)
        
        return f"OK:{image_path.name}"
        
    except Exception as e:
        error_msg = str(e).lower()
        if "broken data" in error_msg or "corrupt" in error_msg:
            try:
                return _fix_corrupt_image(image_path, output_info)
            except Exception as fix_error:
                return f"ERROR:{image_path.name}:{fix_error}"
        return f"ERROR:{image_path.name}:{e}"


def _resize_and_save(img: Image.Image, output_path: Path, max_size: int) -> None:
    """Resize image and save to output path."""
    w, h = img.size
    
    # Guard against invalid dimensions
    if w <= 0 or h <= 0:
        logger.warning(f"Invalid image dimensions: {w}x{h}, skipping")
        return
    
    if w > max_size or h > max_size:
        if w > h:
            new_w = max_size
            new_h = max(1, int(h * max_size / w))
        else:
            new_h = max_size
            new_w = max(1, int(w * max_size / h))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        resized = img
    
    if resized.mode in ("RGBA", "LA"):
        background = Image.new("RGB", resized.size, (255, 255, 255))
        alpha = resized.split()[-1]
        background.paste(resized.convert("RGB"), mask=alpha)
        resized = background
    elif resized.mode not in ("RGB", "L"):
        resized = resized.convert("RGB")
    
    resized.save(output_path, format="JPEG", quality=90, optimize=True, progressive=True)


def _fix_corrupt_image(image_path: Path, output_info: Dict[str, Tuple[Path, int]]) -> str:
    """Attempt to repair corrupt image using ImageMagick."""
    corrupt_backup = image_path.parent / f"{image_path.stem}_corrupt{image_path.suffix}"
    
    try:
        image_path.rename(corrupt_backup)
        
        temp_dir = Path(tempfile.mkdtemp(prefix="repair_", dir="/var/tmp"))
        temp_path = str(temp_dir / f"repaired{image_path.suffix}")
        
        cmd = ["convert", str(corrupt_backup), "-strip", "-interlace", "none", "-colorspace", "sRGB", temp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            corrupt_backup.rename(image_path)
            raise Exception(f"ImageMagick failed: {result.stderr}")
        
        Path(temp_path).rename(image_path)
        
        with Image.open(image_path) as img:
            fixed_img = OrientationFixer.fix_pil_image(img)
            for size_name, (output_path, target_size) in output_info.items():
                if target_size > 0:
                    _resize_and_save(fixed_img, output_path, target_size)
        
        return f"REPAIRED:{image_path.name}"
        
    except Exception as e:
        if corrupt_backup.exists() and not image_path.exists():
            corrupt_backup.rename(image_path)
        raise


class SetResizer(ISetResizer):
    """
    Resizes all images in a set to multiple quality levels.
    Uses parallel processing for performance.
    """
    
    QUALITY_FOLDERS = {
        ResizeQuality.SMALL: "m",
        ResizeQuality.MEDIUM: "x",
        ResizeQuality.LARGE: "xl",
    }
    
    def __init__(self, config: Optional[ResizeConfig] = None):
        self.config = config or ResizeConfig()
        self.processor = ImageProcessor()
    
    def resize_set(self, folder: Path, qualities: Optional[List[ResizeQuality]] = None) -> None:
        """Resize all images in set to specified qualities."""
        qualities = qualities or self.config.qualities
        
        if self._already_resized(folder, qualities):
            logger.info(f"Set already resized: {folder.name}")
            return
        
        start_time = time.time()
        
        images = self._get_images(folder)
        if not images:
            logger.warning(f"No images found in {folder}")
            return
        
        dimensions = self.get_dimensions(folder, images)
        active_qualities = self._filter_qualities(qualities, dimensions)
        
        self._create_output_dirs(folder, active_qualities)
        process_args = self._prepare_processing_args(folder, images, active_qualities)
        
        self._process_parallel(process_args, len(images))
        
        elapsed = time.time() - start_time
        logger.info(f"Resized {len(images)} images in {elapsed:.2f}s ({len(images)/elapsed:.1f} img/s)")
    
    def get_dimensions(self, folder: Path, images: Optional[List[Path]] = None) -> ImageDimensions:
        """Analyze and return max dimensions of images in folder."""
        images = images or self._get_images(folder)
        max_width = 0
        max_height = 0
        
        for i, image_path in enumerate(images):
            try:
                with Image.open(image_path) as img:
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
            except Exception as e:
                logger.warning(f"Error analyzing {image_path.name}: {e}")
            
            if i > 0 and i % 500 == 0:
                gc.collect()
        
        return ImageDimensions(max_width, max_height)
    
    def _already_resized(self, folder: Path, qualities: List[ResizeQuality]) -> bool:
        """Check if set is already resized."""
        for quality in qualities:
            folder_name = self.QUALITY_FOLDERS[quality]
            if not (folder / folder_name).exists():
                return False
        return True
    
    def _get_images(self, folder: Path) -> List[Path]:
        """Get all valid images from folder."""
        from natsort import natsorted
        images = [f for f in folder.glob("*.*") if ImageProcessor.is_valid_image(f)]
        return natsorted(images)
    
    def _filter_qualities(self, qualities: List[ResizeQuality], dimensions: ImageDimensions) -> List[ResizeQuality]:
        """Filter out quality levels larger than source images."""
        return [q for q in qualities if dimensions.min_dimension > q.value or q == ResizeQuality.SMALL]
    
    def _create_output_dirs(self, folder: Path, qualities: List[ResizeQuality]) -> None:
        """Create output directories for each quality level."""
        for quality in qualities:
            folder_name = self.QUALITY_FOLDERS[quality]
            (folder / folder_name).mkdir(parents=True, exist_ok=True)
            logger.info(f"Creating {folder_name}/ ({quality.value}px)")
    
    def _prepare_processing_args(
        self, 
        folder: Path, 
        images: List[Path], 
        qualities: List[ResizeQuality]
    ) -> List[Tuple[Path, Dict[str, Tuple[Path, int]]]]:
        """Prepare arguments for parallel processing."""
        convert_extensions = {".png", ".webp"}
        args = []
        
        for image_path in images:
            ext = image_path.suffix.lower()
            output_name = image_path.stem + ".jpg" if ext in convert_extensions else image_path.name
            
            output_info = {}
            for quality in qualities:
                folder_name = self.QUALITY_FOLDERS[quality]
                output_path = folder / folder_name / output_name
                output_info[folder_name] = (output_path, quality.value)
            
            args.append((image_path, output_info))
        
        return args
    
    def _process_parallel(self, args: List, total: int) -> None:
        """Process images in parallel."""
        max_workers = self.config.max_workers or max(1, min(cpu_count() - 1, total))
        processed = 0
        errors = 0
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_single_image, arg): arg[0] for arg in args}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    result = f"ERROR:worker:{e}"
                
                processed += 1
                
                if result.startswith("ERROR"):
                    errors += 1
                    logger.error(result)
                elif result.startswith("REPAIRED"):
                    logger.warning(result)
                
                if processed % 100 == 0 or processed == total:
                    logger.info(f"Progress: {processed}/{total} ({processed/total*100:.1f}%)")
                
                if processed % 50 == 0:
                    gc.collect()
        
        if errors:
            logger.warning(f"Completed with {errors} errors")
