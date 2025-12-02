"""
Video sprite sheet generation for video players.
Creates sprite sheets with WebVTT files for video preview thumbnails.
"""
import asyncio
import subprocess
import json
import math
import os
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpriteConfig:
    """Configuration for sprite sheet generation."""
    grid_size: int = 10
    interval: float = 5.0
    max_size: int = 320
    quality: int = 3
    output_prefix: str = "sprite_"


class DimensionCalculator:
    """Calculates video dimensions. Single Responsibility."""
    
    @staticmethod
    def get_dimensions(video_path: Path) -> Tuple[int, int]:
        """Get video dimensions with SAR correction."""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "v:0", str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        
        stream = data["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        
        sar = stream.get("sample_aspect_ratio", "1:1")
        try:
            sar_w, sar_h = map(int, sar.split(":"))
            if sar_w != sar_h:
                width = int(width * sar_w / sar_h)
        except (ValueError, ZeroDivisionError):
            pass
        
        return width, height
    
    @staticmethod
    def get_duration(video_path: Path) -> float:
        """Get video duration in seconds."""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    
    @staticmethod
    def get_rotation(video_path: Path) -> int:
        """Get video rotation in degrees."""
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream_tags=rotate",
            "-of", "csv=p=0", str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            rotation = result.stdout.strip()
            return int(rotation) if rotation else 0
        except (subprocess.CalledProcessError, ValueError):
            return 0
    
    @staticmethod
    def calculate_proportional(
        original_width: int,
        original_height: int,
        max_size: int = 320
    ) -> Tuple[int, int]:
        """Calculate proportional dimensions."""
        if original_width >= original_height:
            new_width = max_size
            new_height = int((original_height * max_size) / original_width)
        else:
            new_height = max_size
            new_width = int((original_width * max_size) / original_height)
        return new_width, new_height


class VTTGenerator:
    """Generates WebVTT files for sprite navigation. Single Responsibility."""
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Convert seconds to VTT time format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    @staticmethod
    def generate_entries(
        sprite_num: int,
        start_thumb: int,
        end_thumb: int,
        interval: float,
        width: int,
        height: int,
        grid_size: int,
        prefix: str
    ) -> str:
        """Generate VTT entries for a single sprite."""
        entries = ""
        
        for i in range(start_thumb, end_thumb):
            start_time = i * interval
            end_time = start_time + interval
            
            thumb_index = i - start_thumb
            col = thumb_index % grid_size
            row = thumb_index // grid_size
            
            x = col * width
            y = row * height
            
            start_fmt = VTTGenerator.format_time(start_time)
            end_fmt = VTTGenerator.format_time(end_time)
            
            entries += f"{start_fmt} --> {end_fmt}\n"
            entries += f"{prefix}{sprite_num + 1:03d}.jpg#xywh={x},{y},{width},{height}\n\n"
        
        return entries


class SpriteSheetCreator:
    """Creates sprite sheets from video. Single Responsibility."""
    
    async def create(
        self,
        video_path: Path,
        output_path: Path,
        grid_size: int,
        thumb_width: int,
        thumb_height: int,
        interval: float,
        start_time: float,
        actual_thumbs: int,
        quality: int = 3
    ) -> bool:
        """
        Create a single sprite sheet from video.
        
        Returns:
            True if creation succeeded
        """
        sprite_duration = actual_thumbs * interval
        
        rotation = DimensionCalculator.get_rotation(video_path)
        if rotation in (90, 270):
            thumb_width, thumb_height = thumb_height, thumb_width
        
        video_filter = (
            f"fps=1/{interval},"
            f"scale={thumb_width}:{thumb_height},"
            f"tile={grid_size}x{grid_size}"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(sprite_duration),
            "-i", str(video_path),
            "-vf", video_filter,
            "-frames:v", str(actual_thumbs),
            "-q:v", str(quality),
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.debug(f"Created sprite: {output_path}")
            return True
        
        logger.error(f"Sprite creation failed: {stderr.decode().strip()}")
        return False


class VideoSpriteGenerator:
    """
    Generates video sprite sheets with WebVTT files.
    Used for video player preview thumbnails.
    """
    
    def __init__(self, config: Optional[SpriteConfig] = None):
        self.config = config or SpriteConfig()
        self.dimension_calc = DimensionCalculator()
        self.vtt_generator = VTTGenerator()
        self.sprite_creator = SpriteSheetCreator()
    
    async def generate(
        self,
        video_path: Path,
        output_dir: Path
    ) -> Tuple[List[Path], Path]:
        """
        Generate sprite sheets and VTT file for video.
        
        Args:
            video_path: Path to video file
            output_dir: Output directory for sprites and VTT
            
        Returns:
            Tuple of (list of sprite paths, VTT file path)
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        duration = self.dimension_calc.get_duration(video_path)
        orig_width, orig_height = self.dimension_calc.get_dimensions(video_path)
        thumb_width, thumb_height = self.dimension_calc.calculate_proportional(
            orig_width, orig_height, self.config.max_size
        )
        
        total_thumbs = math.ceil(duration / self.config.interval)
        thumbs_per_sprite = self.config.grid_size * self.config.grid_size
        total_sprites = math.ceil(total_thumbs / thumbs_per_sprite)
        
        logger.info(f"Generating {total_sprites} sprites for {total_thumbs} thumbnails")
        
        tasks = []
        vtt_params = []
        
        for sprite_num in range(total_sprites):
            start_thumb = sprite_num * thumbs_per_sprite
            end_thumb = min(start_thumb + thumbs_per_sprite, total_thumbs)
            actual_thumbs = end_thumb - start_thumb
            
            if actual_thumbs > 0:
                sprite_file = output_dir / f"{self.config.output_prefix}{sprite_num + 1:03d}.jpg"
                start_time = sprite_num * thumbs_per_sprite * self.config.interval
                
                task = self.sprite_creator.create(
                    video_path, sprite_file, self.config.grid_size,
                    thumb_width, thumb_height, self.config.interval,
                    start_time, actual_thumbs, self.config.quality
                )
                tasks.append(task)
                
                vtt_params.append({
                    "sprite_num": sprite_num,
                    "start_thumb": start_thumb,
                    "end_thumb": end_thumb
                })
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        vtt_content = "WEBVTT\n\n"
        sprite_paths = []
        
        for i, result in enumerate(results):
            params = vtt_params[i]
            sprite_num = params["sprite_num"]
            sprite_path = output_dir / f"{self.config.output_prefix}{sprite_num + 1:03d}.jpg"
            
            if isinstance(result, Exception):
                logger.error(f"Sprite {sprite_num + 1} failed: {result}")
            elif result:
                sprite_paths.append(sprite_path)
                vtt_content += self.vtt_generator.generate_entries(
                    sprite_num, params["start_thumb"], params["end_thumb"],
                    self.config.interval, thumb_width, thumb_height,
                    self.config.grid_size, self.config.output_prefix
                )
        
        vtt_path = output_dir / f"{self.config.output_prefix}.vtt"
        vtt_path.write_text(vtt_content)
        
        logger.info(f"Generated {len(sprite_paths)} sprites and VTT file")
        return sprite_paths, vtt_path


async def generate_video_sprites(
    video_path: Path,
    output_dir: Path,
    grid_size: int = 10,
    interval: float = 5.0,
    max_size: int = 320
) -> Tuple[List[Path], Path]:
    """
    Convenience function to generate video sprites.
    
    Args:
        video_path: Path to video file
        output_dir: Output directory
        grid_size: Thumbnails per row/column
        interval: Seconds between thumbnails
        max_size: Maximum thumbnail dimension
        
    Returns:
        Tuple of (sprite paths, VTT file path)
    """
    config = SpriteConfig(
        grid_size=grid_size,
        interval=interval,
        max_size=max_size
    )
    generator = VideoSpriteGenerator(config)
    return await generator.generate(video_path, output_dir)
