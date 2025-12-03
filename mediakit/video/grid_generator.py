"""
Video grid preview generator using ffmpeg.
Creates visual grid previews from video frames.
Follows Facade Pattern - orchestrates frame extraction and composition.
"""
import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

from PIL import Image

from ..core.interfaces import IVideoPreviewGenerator, VideoGridConfig
from .info import VideoInfo

logger = logging.getLogger(__name__)


@dataclass
class GridLayoutConfig:
    """Configuration for grid layout calculation."""
    min_duration_for_grid: float = 5.0
    short_video_threshold: float = 180.0
    medium_video_threshold: float = 1800.0


class GridSizeCalculator:
    """Calculates optimal grid size based on video duration. Strategy Pattern."""
    
    def __init__(self, config: Optional[GridLayoutConfig] = None):
        self.config = config or GridLayoutConfig()
    
    def calculate(self, duration: float) -> Optional[int]:
        """
        Calculate grid size based on video duration.
        
        Returns:
            Grid size (3-5) or None if video too short
        """
        if duration < self.config.min_duration_for_grid:
            logger.warning(f"Video too short ({duration}s) for grid generation")
            return None
        
        if duration > self.config.medium_video_threshold:
            return 5
        elif duration > self.config.short_video_threshold:
            return 4
        return 3


class FrameExtractor:
    """Extracts frames from video using ffmpeg. Single Responsibility."""
    
    def __init__(self, max_parallel: int = 8):
        self.semaphore = asyncio.Semaphore(max_parallel)
    
    async def extract_frame(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float,
        width: int,
        height: int
    ) -> bool:
        """
        Extract a single frame from video asynchronously.
        
        Args:
            video_path: Source video path
            output_path: Output frame path
            timestamp: Time in seconds
            width: Target width
            height: Target height
            
        Returns:
            True if extraction succeeded
        """
        async with self.semaphore:
            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", str(video_path),
                "-vf", f"scale={width}:{height}",
                "-frames:v", "1",
                "-q:v", "3",
                str(output_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.debug(f"Extracted frame at {timestamp}s")
                return True
            
            logger.error(f"Frame extraction failed: {stderr.decode().strip()}")
            return False


class GridComposer:
    """Composes grid image from individual frames. Single Responsibility."""
    
    def compose(
        self,
        frame_paths: List[Path],
        grid_size: int,
        cell_width: int,
        cell_height: int,
        output_path: Path,
        quality: int = 85
    ) -> Path:
        """
        Compose grid image from frames.
        
        Args:
            frame_paths: List of frame image paths
            grid_size: Grid dimension (grid_size x grid_size)
            cell_width: Width of each cell
            cell_height: Height of each cell
            output_path: Output path for grid image
            quality: JPEG quality (1-100)
            
        Returns:
            Path to composed grid image
        """
        grid_width = cell_width * grid_size
        grid_height = cell_height * grid_size
        
        grid_image = Image.new("RGB", (grid_width, grid_height), color="black")
        
        for i, frame_path in enumerate(frame_paths):
            if not frame_path.exists():
                continue
            
            try:
                with Image.open(frame_path) as frame:
                    row = i // grid_size
                    col = i % grid_size
                    x = col * cell_width
                    y = row * cell_height
                    
                    resized = frame.resize(
                        (cell_width, cell_height),
                        Image.Resampling.LANCZOS
                    )
                    grid_image.paste(resized, (x, y))
                    logger.debug(f"Added frame {i} at ({x}, {y})")
            except Exception as e:
                logger.error(f"Error processing frame {frame_path}: {e}")
        
        grid_image.save(output_path, "JPEG", quality=quality)
        logger.info(f"Grid saved to {output_path}")
        return output_path


class VideoGridGenerator(IVideoPreviewGenerator):
    """
    Generates grid preview images from videos.
    Facade that orchestrates video info, frame extraction, and composition.
    """
    
    def __init__(
        self,
        video_path: Path,
        config: Optional[VideoGridConfig] = None,
        output_path: Optional[Path] = None
    ):
        """
        Args:
            video_path: Path to video file
            config: Grid generation configuration
            output_path: Output path for grid image
        """
        self.video_path = Path(video_path)
        self.config = config or VideoGridConfig()
        self.output_path = output_path
        
        self.video_info: Optional[VideoInfo] = None
        self.grid_size: Optional[int] = None
        
        self.size_calculator = GridSizeCalculator()
        self.frame_extractor = FrameExtractor(self.config.max_parallel)
        self.composer = GridComposer()
    
    async def generate(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate video grid preview asynchronously.
        
        Args:
            output_path: Optional output path override
            
        Returns:
            Path to generated grid image
        """
        output = output_path or self.output_path
        if output is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            temp_file.close()
            output = Path(temp_file.name)
        
        if self.video_info is None:
            self.video_info = VideoInfo(self.video_path)
            await self.video_info.load()
        
        if self.grid_size is None:
            self.grid_size = self.config.grid_size or self.size_calculator.calculate(
                self.video_info.duration
            )
        
        if self.grid_size is None:
            raise ValueError("Video too short to generate grid preview")
        
        frame_paths = await self._extract_all_frames()
        
        thumb_width, thumb_height = self._get_thumbnail_dimensions()
        
        self.composer.compose(
            frame_paths,
            self.grid_size,
            thumb_width,
            thumb_height,
            output,
            quality=self.config.quality
        )
        
        self._cleanup_frames(frame_paths)
        
        return output
    
    async def _extract_all_frames(self) -> List[Path]:
        """Extract all frames needed for grid."""
        frames_needed = self.grid_size * self.grid_size
        duration = self.video_info.duration
        time_interval = (duration - 1) / frames_needed
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            frame_paths = []
            
            thumb_width, thumb_height = self._get_thumbnail_dimensions()
            
            tasks = []
            for i in range(frames_needed):
                timestamp = 1.0 if i == 0 else i * time_interval
                frame_path = temp_path / f"frame_{i:02d}.jpg"
                frame_paths.append(frame_path)
                
                task = self.frame_extractor.extract_frame(
                    self.video_path,
                    frame_path,
                    timestamp,
                    thumb_width,
                    thumb_height
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            persistent_paths = []
            persist_dir = Path(tempfile.mkdtemp(prefix="grid_frames_"))
            for i, fp in enumerate(frame_paths):
                if fp.exists():
                    new_path = persist_dir / fp.name
                    fp.rename(new_path)
                    persistent_paths.append(new_path)
                else:
                    persistent_paths.append(fp)
            
            return persistent_paths
    
    def _get_thumbnail_dimensions(self) -> Tuple[int, int]:
        """Get thumbnail dimensions accounting for rotation."""
        thumb_width, thumb_height = self.video_info.get_proportional_dimensions(
            self.config.max_size
        )
        
        if self.video_info.rotation in (90, 270):
            thumb_width, thumb_height = thumb_height, thumb_width
        
        return thumb_width, thumb_height
    
    def _cleanup_frames(self, frame_paths: List[Path]) -> None:
        """Clean up temporary frame files."""
        for path in frame_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        
        if frame_paths and frame_paths[0].parent.exists():
            try:
                frame_paths[0].parent.rmdir()
            except Exception:
                pass


async def generate_video_grid(
    video_path: Path,
    output_path: Optional[Path] = None,
    grid_size: int = 4,
    max_size: int = 480,
    quality: int = 70
) -> Path:
    """
    Convenience function to generate video grid.
    
    Args:
        video_path: Path to video file
        output_path: Output path for grid image
        grid_size: Grid dimension
        max_size: Maximum thumbnail size
        
    Returns:
        Path to generated grid image
    """
    config = VideoGridConfig(grid_size=grid_size, max_size=max_size, quality=quality)
    generator = VideoGridGenerator(video_path, config, output_path)
    return await generator.generate()
