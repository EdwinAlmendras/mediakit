"""
Video information extraction using ffprobe.
Follows Single Responsibility Principle - only handles video metadata extraction.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

from ..core.interfaces import IVideoInfoProvider, VideoDimensions

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo(IVideoInfoProvider):
    """
    Extracts and provides video metadata using ffprobe.
    Implements async loading for non-blocking I/O operations.
    """
    
    input_path: Path
    _format_data: Optional[dict] = None
    _stream_data: Optional[dict] = None
    _loaded: bool = False
    
    def __init__(self, input_path: Path):
        self.input_path = Path(input_path) if not isinstance(input_path, Path) else input_path
        self._format_data = None
        self._stream_data = None
        self._loaded = False
    
    async def load(self) -> None:
        """Load video metadata using ffprobe asynchronously."""
        if self._loaded:
            return
            
        self._validate_input()
        
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams",
            str(self.input_path)
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                self._handle_ffprobe_error(process.returncode, stdout, stderr)
            
            self._parse_output(stdout.decode().strip())
            self._loaded = True
            
        except FileNotFoundError:
            raise ValueError("ffprobe not found. Ensure ffprobe is installed and in PATH.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse ffprobe output for '{self.input_path.name}': {e}")
    
    def load_sync(self) -> None:
        """Load video metadata synchronously."""
        if self._loaded:
            return
            
        self._validate_input()
        
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams",
            str(self.input_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self._parse_output(result.stdout.strip())
            self._loaded = True
        except FileNotFoundError:
            raise ValueError("ffprobe not found. Ensure ffprobe is installed and in PATH.")
        except subprocess.CalledProcessError as e:
            raise ValueError(f"ffprobe failed for '{self.input_path.name}': {e.stderr}")
    
    def _validate_input(self) -> None:
        """Validate input file exists and is a file."""
        if not self.input_path.exists():
            raise ValueError(f"Video file does not exist: {self.input_path}")
        if not self.input_path.is_file():
            raise ValueError(f"Path is not a file: {self.input_path}")
    
    def _handle_ffprobe_error(self, returncode: int, stdout: bytes, stderr: bytes) -> None:
        """Handle ffprobe error with detailed message."""
        stderr_text = stderr.decode().strip()
        stdout_text = stdout.decode().strip()
        
        error_details = []
        if stderr_text:
            error_details.append(f"stderr: {stderr_text}")
        if stdout_text:
            error_details.append(f"stdout: {stdout_text}")
        
        error_msg = f"ffprobe failed for '{self.input_path.name}' (exit code {returncode})"
        if error_details:
            error_msg += f" - {', '.join(error_details)}"
        else:
            error_msg += " - File may be corrupted or not a valid video."
        
        raise ValueError(error_msg)
    
    def _parse_output(self, output: str) -> None:
        """Parse ffprobe JSON output."""
        if not output:
            raise ValueError(f"ffprobe returned empty output for '{self.input_path.name}'")
        
        data = json.loads(output)
        
        if "format" not in data:
            raise ValueError(f"Invalid ffprobe output: 'format' key not found")
        
        self._format_data = data["format"]
        self._all_streams = data.get("streams", [])
        
        video_stream = None
        for stream in self._all_streams:
            if stream.get("codec_type") == "video":
                video_stream = stream
                break
        
        if video_stream is None:
            raise ValueError(f"No video stream found in '{self.input_path.name}'")
        
        self._stream_data = video_stream
    
    def _ensure_loaded(self) -> None:
        """Ensure metadata is loaded before accessing properties."""
        if not self._loaded:
            raise RuntimeError("VideoInfo not loaded. Call load() or load_sync() first.")
    
    @property
    def duration(self) -> float:
        """Video duration in seconds."""
        self._ensure_loaded()
        return float(self._format_data.get("duration", 0))
    
    @property
    def codec(self) -> str:
        """Video codec name."""
        self._ensure_loaded()
        return self._stream_data.get("codec_name", "unknown")
    
    @property
    def codec_name(self) -> str:
        """Alias for codec property."""
        return self.codec
    
    @property
    def fps(self) -> float:
        """Frames per second."""
        self._ensure_loaded()
        
        def parse_fps(fps_str: str) -> float:
            if not fps_str or fps_str == "0/0":
                return 0.0
            try:
                num, den = map(int, fps_str.split("/"))
                return num / den if den != 0 else 0.0
            except (ValueError, ZeroDivisionError):
                return 0.0
        
        r_frame_rate = parse_fps(self._stream_data.get("r_frame_rate", ""))
        avg_frame_rate = parse_fps(self._stream_data.get("avg_frame_rate", ""))
        
        fps_value = avg_frame_rate if abs(avg_frame_rate - r_frame_rate) > 0.01 else r_frame_rate
        return round(fps_value, 2)
    
    @property
    def frame_count(self) -> Optional[int]:
        """Total number of frames."""
        self._ensure_loaded()
        nb_frames = self._stream_data.get("nb_frames")
        if nb_frames and nb_frames != "N/A":
            return int(nb_frames)
        if self.fps > 0:
            return int(self.duration * self.fps)
        return None
    
    @property
    def width(self) -> int:
        """Video width with SAR correction."""
        self._ensure_loaded()
        width = int(self._stream_data.get("width", 0))
        sar = self._get_sample_aspect_ratio()
        if sar[0] != sar[1]:
            width = int(width * sar[0] / sar[1])
        return width
    
    @property
    def height(self) -> int:
        """Video height."""
        self._ensure_loaded()
        return int(self._stream_data.get("height", 0))
    
    @property
    def rotation(self) -> int:
        """Video rotation in degrees, from tags, or side_data_list with fallback."""
        self._ensure_loaded()
        # Try from tags first
        
        side_data = self._stream_data.get("side_data_list", [])
        if isinstance(side_data, list):
            for entry in side_data:
                if (
                    isinstance(entry, dict)
                    and entry.get("side_data_type") == "Display Matrix"
                    and "rotation" in entry
                ):
                    try:
                        rot_dm = int(entry["rotation"])
                        return (-rot_dm) % 360 
                    except (ValueError, TypeError):
                        pass
        try:
            rotation = self._stream_data.get("tags", {}).get("rotate", None)
            if rotation not in (None, ""):
                return int(rotation)
        except (ValueError, KeyError, TypeError):
            pass

        return 0
    
    @property
    def dimensions(self) -> VideoDimensions:
        """Video dimensions with rotation-aware display dimensions."""
        self._ensure_loaded()
        width = self.width
        height = self.height
        
        if self.rotation in (90, 270):
            display_width, display_height = height, width
        else:
            display_width, display_height = width, height
        
        return VideoDimensions(
            width=width,
            height=height,
            display_width=display_width,
            display_height=display_height,
            rotation=self.rotation
        )
    
    @property
    def bitrate(self) -> int:
        """Video bitrate in bps."""
        self._ensure_loaded()
        return int(self._format_data.get("bit_rate", 0))
    
    def _get_sample_aspect_ratio(self) -> Tuple[int, int]:
        """Get sample aspect ratio as tuple."""
        sar = self._stream_data.get("sample_aspect_ratio", "1:1")
        try:
            parts = sar.split(":")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return 1, 1
    
    @property
    def sar(self) -> str:
        """Sample Aspect Ratio (pixel aspect ratio)."""
        self._ensure_loaded()
        return self._stream_data.get("sample_aspect_ratio", "1:1")
    
    @property
    def dar(self) -> str:
        """Display Aspect Ratio."""
        self._ensure_loaded()
        return self._stream_data.get("display_aspect_ratio", f"{self.width}:{self.height}")
    
    @property
    def container(self) -> str:
        """Container format (mp4, mkv, avi, etc)."""
        self._ensure_loaded()
        return self._format_data.get("format_name", "").split(",")[0]
    
    @property
    def video_codec(self) -> str:
        """Video codec name (h264, hevc, vp9, etc)."""
        return self.codec
    
    @property
    def video_codec_long(self) -> str:
        """Video codec long name."""
        self._ensure_loaded()
        return self._stream_data.get("codec_long_name", self.codec)
    
    @property
    def video_profile(self) -> Optional[str]:
        """Video codec profile (High, Main, Baseline, etc)."""
        self._ensure_loaded()
        return self._stream_data.get("profile")
    
    @property
    def video_level(self) -> Optional[int]:
        """Video codec level."""
        self._ensure_loaded()
        level = self._stream_data.get("level")
        return level if level and level != -99 else None
    
    @property
    def pix_fmt(self) -> str:
        """Pixel format (yuv420p, yuv444p, etc)."""
        self._ensure_loaded()
        return self._stream_data.get("pix_fmt", "unknown")
    
    @property
    def color_space(self) -> Optional[str]:
        """Color space (bt709, smpte170m, etc)."""
        self._ensure_loaded()
        return self._stream_data.get("color_space")
    
    @property
    def audio_codec(self) -> Optional[str]:
        """Audio codec name (aac, mp3, opus, etc)."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                return stream.get("codec_name")
        return None
    
    @property
    def audio_codec_long(self) -> Optional[str]:
        """Audio codec long name."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                return stream.get("codec_long_name")
        return None
    
    @property
    def audio_sample_rate(self) -> Optional[int]:
        """Audio sample rate in Hz."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                sr = stream.get("sample_rate")
                return int(sr) if sr else None
        return None
    
    @property
    def audio_channels(self) -> Optional[int]:
        """Number of audio channels."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                return stream.get("channels")
        return None
    
    @property
    def audio_bitrate(self) -> Optional[int]:
        """Audio bitrate in bps."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                br = stream.get("bit_rate")
                return int(br) if br else None
        return None
    
    @property
    def tags(self) -> dict:
        """Container tags (title, artist, encoder, creation_time, etc)."""
        self._ensure_loaded()
        
        tags = {}
        # Merge all tags from all streams, later values overwrite earlier ones.
        for stream in self._all_streams:
            stream_tags = stream.get("tags", {})
            if stream_tags:
                tags.update(stream_tags)
        
        return tags
    
    @property
    def video_tags(self) -> dict:
        """Video stream tags."""
        self._ensure_loaded()
        return self._stream_data.get("tags", {})
    
    @property
    def audio_tags(self) -> Optional[dict]:
        """Audio stream tags."""
        self._ensure_loaded()
        for stream in self._all_streams:
            if stream.get("codec_type") == "audio":
                return stream.get("tags", {})
        return None
    
    @property
    def creation_time(self) -> Optional[str]:
        """Creation time from container tags."""
        self._ensure_loaded()
        return self.video_tags.get("creation_time") or self.tags.get("creation_time")
    
    @property
    def encoder(self) -> Optional[str]:
        """Encoder used (from container tags)."""
        self._ensure_loaded()
        return self.tags.get("encoder")
    
    def get_proportional_dimensions(self, max_size: int = 720) -> Tuple[int, int]:
        """
        Calculate proportional dimensions scaling to max_size.
        The minimum dimension will equal max_size.
        """
        self._ensure_loaded()
        w, h = self.width, self.height
        
        if w <= h:
            new_width = max_size
            new_height = int((h * max_size) / w)
        else:
            new_height = max_size
            new_width = int((w * max_size) / h)
        
        return new_width, new_height
