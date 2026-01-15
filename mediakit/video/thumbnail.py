"""
Video thumbnail generation using ffmpeg.
Follows Single Responsibility Principle - only handles thumbnail extraction.
"""
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Union
import logging

from PIL import Image, ImageStat

from ..core.interfaces import IThumbnailGenerator

logger = logging.getLogger(__name__)


class FrameValidator:
    """Validates extracted video frames. Single Responsibility."""
    
    @staticmethod
    def is_valid(image_path: Path, threshold: float = 5.0) -> bool:
        """
        Check if frame is valid (not uniform black/white).
        
        Args:
            image_path: Path to frame image
            threshold: Standard deviation threshold (higher = stricter)
            
        Returns:
            True if frame has enough variation (not blank)
        """
        try:
            with Image.open(image_path) as img:
                stat = ImageStat.Stat(img)
                return max(stat.stddev) > threshold
        except Exception as e:
            logger.warning(f"Error validating frame: {e}")
            return False


class StepCalculator:
    """Calculates optimal step size for frame extraction. Strategy Pattern."""
    
    @staticmethod
    def calculate(duration: float) -> int:
        """
        Calculate step size based on video duration.
        
        Shorter videos use smaller steps to find valid frames.
        """
        if duration < 10:
            return 1
        elif duration < 60:
            return 2
        return 10


class ThumbnailGenerator(IThumbnailGenerator):
    """
    Generates thumbnails from videos.
    Finds valid (non-blank) frames automatically.
    """
    
    def __init__(self, quality: int = 2):
        """
        Args:
            quality: JPEG quality (1-31, lower is better)
        """
        self.quality = quality
        self.frame_validator = FrameValidator()
        self.step_calculator = StepCalculator()
    
    def generate(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        step: Optional[int] = None
    ) -> Path:
        """
        Generate thumbnail from video synchronously.
        
        Args:
            video_path: Path to video file
            output_path: Output path for thumbnail
            step: Time step for searching valid frames
            
        Returns:
            Path to generated thumbnail
        """
        video_path = Path(video_path)
        
        if output_path is None:
            output_path = self._create_temp_output()
        
        duration = self._get_duration(video_path)
        step_val = step or self.step_calculator.calculate(duration)
        
        t = 0.0
        while t < duration:
            if self._capture_and_validate(video_path, t, output_path):
                return output_path
            t += step_val
        
        if self._capture_and_validate(video_path, 0, output_path):
            return output_path
        
        raise ValueError(f"No valid frame found in {video_path}")
    
    async def generate_async(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        step: Optional[int] = None
    ) -> Path:
        """
        Generate thumbnail from video asynchronously.
        
        Args:
            video_path: Path to video file
            output_path: Output path for thumbnail
            step: Time step for searching valid frames
            
        Returns:
            Path to generated thumbnail
        """
        video_path = Path(video_path)
        
        if output_path is None:
            output_path = self._create_temp_output()
        
        duration = self._get_duration(video_path)
        step_val = step or self.step_calculator.calculate(duration)
        
        t = 0.0
        while t < duration:
            if await self._capture_and_validate_async(video_path, t, output_path):
                return output_path
            t += step_val
        
        if await self._capture_and_validate_async(video_path, 0, output_path):
            return output_path
        
        raise ValueError(f"No valid frame found in {video_path}")
    
    def _create_temp_output(self) -> Path:
        """Create temporary output file."""
        temp_dir = Path(tempfile.mkdtemp(prefix="thumb_", dir="/var/tmp"))
        return temp_dir / "thumbnail.jpg"
    
    def _get_duration(self, video_path: Path) -> float:
        """Get video duration."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0
    
    def _build_capture_command(
        self, 
        video_path: Path, 
        timestamp: float, 
        output_path: Path
    ) -> list:
        """Build ffmpeg frame capture command."""
        return [
            "ffmpeg", "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", str(self.quality),
            "-y", str(output_path)
        ]
    
    def _capture_and_validate(
        self, 
        video_path: Path, 
        timestamp: float, 
        output_path: Path
    ) -> bool:
        """Capture frame and validate it."""
        cmd = self._build_capture_command(video_path, timestamp, output_path)
        result = subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        
        if result.returncode == 0 and self.frame_validator.is_valid(output_path):
            return True
        
        Path(output_path).unlink(missing_ok=True)
        return False
    
    async def _capture_and_validate_async(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path
    ) -> bool:
        """Capture frame and validate it asynchronously."""
        cmd = self._build_capture_command(video_path, timestamp, output_path)
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await process.communicate()
        
        if process.returncode == 0 and self.frame_validator.is_valid(output_path):
            return True
        
        Path(output_path).unlink(missing_ok=True)
        return False
