"""
Media analyzer - extract metadata from photos and videos.
"""
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Any, Union
from datetime import datetime
import secrets
import string

from mediakit.video.info import VideoInfo
from mediakit.image.info import ImageInfo


ALPHABET = string.ascii_letters + string.digits
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff"}


def generate_id(length: int = 6) -> str:
    """Generate random alphanumeric ID."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def sha256_file(path: Path, chunk_size: int = 65536) -> str:
    """Calculate SHA256 hash of file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def analyze_video(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Analyze video file.
    
    Returns:
        Dict with Document + AttributeVideo fields
    """
    path = Path(path)
    stat = path.stat()
    
    # Load video info
    info = VideoInfo(path)
    info.load_sync()
    
    mimetype, _ = mimetypes.guess_type(str(path))
    
    return {
        # Document fields
        "source_id": generate_id(),
        "sha256sum": sha256_file(path),
        "filename": path.name,
        "mimetype": mimetype or "video/mp4",
        "mtime": datetime.fromtimestamp(stat.st_mtime),
        "ctime": datetime.fromtimestamp(stat.st_ctime),
        # Video metadata fields
        "width": info.width,
        "height": info.height,
        "duration": info.duration,
        "bitrate": info.bitrate,
        "fps": info.fps,
        "container": info.container,
        "sar": info.sar,
        "dar": info.dar,
        # Video codec info
        "video_codec": info.video_codec,
        "video_codec_long": info.video_codec_long,
        "video_profile": info.video_profile,
        "video_level": info.video_level,
        "pix_fmt": info.pix_fmt,
        "color_space": info.color_space,
        # Audio info
        "audio_codec": info.audio_codec,
        "audio_codec_long": info.audio_codec_long,
        "audio_sample_rate": info.audio_sample_rate,
        "audio_channels": info.audio_channels,
        "audio_bitrate": info.audio_bitrate,
        # Tags
        "tags": info.tags,  # Container tags (title, encoder, creation_time, etc)
        "creation_time": info.creation_time,
        "encoder": info.encoder,
    }


def analyze_photo(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Analyze photo file.
    
    Returns:
        Dict with Document + AttributePhoto fields
    """
    path = Path(path)
    stat = path.stat()
    
    # Load image info
    info = ImageInfo(path)
    info.load()
    
    mimetype, _ = mimetypes.guess_type(str(path))
    
    return {
        # Document fields
        "source_id": generate_id(),
        "sha256sum": sha256_file(path),
        "filename": path.name,
        "mimetype": mimetype or f"image/{info.format.lower()}",
        "mtime": datetime.fromtimestamp(stat.st_mtime),
        "ctime": datetime.fromtimestamp(stat.st_ctime),
        # AttributePhoto fields
        "width": info.width,
        "height": info.height,
        "camera": info.camera,
        "orientation": info.orientation,
        "creation_date": info.creation_date,
        "tags": info.tags,
    }


def analyze(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Analyze any media file (auto-detect type).
    
    Returns:
        Dict with metadata
    """
    path = Path(path)
    ext = path.suffix.lower()
    
    if ext in VIDEO_EXTENSIONS:
        return analyze_video(path)
    elif ext in IMAGE_EXTENSIONS:
        return analyze_photo(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
