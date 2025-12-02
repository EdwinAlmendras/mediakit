"""
Video conversion operations using ffmpeg.
Follows Open/Closed Principle - extensible through configuration.
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field
import logging

from ..core.interfaces import IVideoConverter, VideoConversionConfig

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Result of a video conversion operation."""
    success: bool
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    conversion_type: str = "none"


class VideoCodecDetector:
    """Detects video codec using ffprobe. Single Responsibility."""
    
    @staticmethod
    def get_codec(video_path: Path) -> str:
        """Get video codec name."""
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name", "-of", "csv=p=0",
            str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                codec = line.strip()
                if codec:
                    return codec.lower()
            return ""
        except subprocess.CalledProcessError:
            return ""
    
    @staticmethod
    def get_audio_codec(video_path: Path) -> str:
        """Get audio codec name."""
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "default=nokey=1:noprint_wrappers=1",
            str(video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout.strip().lower()
        except subprocess.CalledProcessError:
            return ""
    
    @staticmethod
    def is_h264(video_path: Path) -> bool:
        """Check if video uses H.264 codec."""
        return VideoCodecDetector.get_codec(video_path) == "h264"


class VideoDurationProvider:
    """Provides video duration. Single Responsibility."""
    
    @staticmethod
    def get_duration(video_path: Path) -> float:
        """Get video duration in seconds."""
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


class CreationTimeHandler:
    """Handles video creation time metadata. Single Responsibility."""
    
    @staticmethod
    def get_creation_time(video_path: Path) -> Optional[str]:
        """Extract creation time from video metadata."""
        from datetime import datetime
        
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format_tags=creation_time:stream_tags=creation_time",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            return None
        
        tag_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        ffprobe_times = []
        
        for t in tag_lines:
            try:
                ffprobe_times.append(datetime.fromisoformat(t.replace("Z", "+00:00")))
            except Exception:
                pass
        
        if ffprobe_times:
            return min(ffprobe_times).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        file_stat = video_path.stat()
        mtime = datetime.fromtimestamp(file_stat.st_mtime)
        ctime = datetime.fromtimestamp(file_stat.st_ctime)
        min_time = min(mtime, ctime)
        
        return min_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    @staticmethod
    def get_metadata_params(creation_time: str) -> List[str]:
        """Get ffmpeg parameters to set creation time metadata."""
        return [
            "-metadata", f"creation_time={creation_time}",
            "-metadata:s:v:0", f"creation_time={creation_time}",
            "-metadata:s:a:0", f"creation_time={creation_time}",
        ]


class PresetSelector:
    """Selects encoding preset based on duration. Strategy Pattern."""
    
    @staticmethod
    def select(duration: float) -> str:
        """Select preset based on video duration for optimal speed/quality."""
        if duration < 60:
            return "slow"
        elif duration < 120:
            return "medium"
        elif duration < 240:
            return "fast"
        elif duration < 600:
            return "veryfast"
        return "ultrafast"


class VideoConverter(IVideoConverter):
    """
    Converts videos to compatible formats.
    Orchestrates codec detection, conversion, and metadata handling.
    """
    
    def __init__(self, config: Optional[VideoConversionConfig] = None):
        self.config = config or VideoConversionConfig()
        self.codec_detector = VideoCodecDetector()
        self.duration_provider = VideoDurationProvider()
        self.creation_time_handler = CreationTimeHandler()
        self.preset_selector = PresetSelector()
    
    def needs_conversion(self, video_path: Path) -> bool:
        """Check if video needs conversion based on codec and container."""
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        codec = self.codec_detector.get_codec(video_path)
        extension = video_path.suffix.lower()
        
        needs_codec_conversion = codec not in self.config.supported_codecs
        needs_container_conversion = extension not in self.config.supported_extensions
        
        return needs_codec_conversion or needs_container_conversion
    
    def convert(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Convert video to compatible format.
        
        Args:
            input_path: Source video path
            output_path: Optional output path. If None, uses temp directory.
            
        Returns:
            Path to converted video or original if no conversion needed.
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Video file not found: {input_path}")
        
        codec = self.codec_detector.get_codec(input_path)
        extension = input_path.suffix.lower()
        
        needs_codec = codec not in self.config.supported_codecs
        needs_container = extension not in self.config.supported_extensions
        
        if not needs_codec and not needs_container:
            logger.debug(f"No conversion needed for {input_path.name}")
            return input_path
        
        temp_dir = tempfile.mkdtemp(prefix="video_convert_")
        temp_path = Path(temp_dir) / f"{input_path.stem}.temp.mp4"
        final_path = output_path or Path(temp_dir) / f"{input_path.stem}.mp4"
        
        creation_time = self.creation_time_handler.get_creation_time(input_path)
        audio_codec = self.codec_detector.get_audio_codec(input_path)
        
        cmd = self._build_convert_command(
            input_path, temp_path, codec, audio_codec, creation_time, needs_codec
        )
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            temp_path.replace(final_path)
            logger.info(f"Converted: {input_path.name} -> {final_path.name}")
            return final_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Conversion failed for {input_path.name}: {e}")
            raise
    
    def _build_convert_command(
        self,
        input_path: Path,
        output_path: Path,
        video_codec: str,
        audio_codec: str,
        creation_time: Optional[str],
        needs_video_conversion: bool
    ) -> List[str]:
        """Build ffmpeg conversion command."""
        duration = self.duration_provider.get_duration(input_path)
        
        cmd = [
            "ffmpeg", "-i", str(input_path),
            "-y", "-map_metadata", "0", "-movflags", "faststart"
        ]
        
        if creation_time:
            cmd.extend(self.creation_time_handler.get_metadata_params(creation_time))
        
        if audio_codec == "aac":
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", self.config.audio_codec, "-b:a", self.config.audio_bitrate])
        
        if needs_video_conversion:
            preset = self.preset_selector.select(duration)
            cmd.extend([
                "-c:v", self.config.codec,
                "-preset", preset,
                "-crf", str(self.config.crf),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2"
            ])
        else:
            cmd.extend(["-c:v", "copy"])
        
        cmd.append(str(output_path))
        return cmd
    
    def convert_to_h264(
        self, 
        input_path: Path, 
        output_path: Path,
        extra_params: Optional[List[str]] = None
    ) -> Path:
        """Convert video to H.264 with full re-encoding."""
        cmd = [
            "ffmpeg", "-i", str(input_path),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            *(extra_params or []),
            "-y", "-map_metadata", "0",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"H.264 conversion completed: {output_path}")
        return output_path
    
    def remux_to_mp4(
        self, 
        input_path: Path, 
        output_path: Path,
        extra_params: Optional[List[str]] = None
    ) -> Path:
        """Remux video to MP4 container without re-encoding."""
        cmd = [
            "ffmpeg", "-i", str(input_path),
            "-c:v", "copy",
            *(extra_params or []),
            "-map_metadata", "0",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"Container conversion completed: {output_path}")
        return output_path
