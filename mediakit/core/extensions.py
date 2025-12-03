"""
Centralized media file extensions.

Used by: mediakit, uploader, social, kmp
"""

VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.3gp', '.ogv', '.mts', '.m2ts', '.ts', '.mpeg', '.mpg', '.mp2',
    '.mpe', '.mpv', '.m4p', '.m4b', '.m4r', '.f4v', '.f4p', '.f4a', '.f4b',
}

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw', '.dng',
}

AUDIO_EXTENSIONS = {
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
    '.aiff', '.ape', '.alac',
}

ARCHIVE_EXTENSIONS = {
    '.7z', '.zip', '.rar', '.tar', '.gz', '.bz2', '.xz', '.tar.gz',
}

DOCUMENT_EXTENSIONS = {
    '.htm', '.html', '.pdf', '.txt', '.doc', '.docx', '.csv', '.json',
}


def is_video(path) -> bool:
    """Check if path is a video file."""
    from pathlib import Path
    return Path(path).suffix.lower() in VIDEO_EXTENSIONS


def is_image(path) -> bool:
    """Check if path is an image file."""
    from pathlib import Path
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def is_audio(path) -> bool:
    """Check if path is an audio file."""
    from pathlib import Path
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def is_archive(path) -> bool:
    """Check if path is an archive file."""
    from pathlib import Path
    return Path(path).suffix.lower() in ARCHIVE_EXTENSIONS


def get_media_type(path) -> str:
    """Get media type: video, image, audio, archive, or unknown."""
    from pathlib import Path
    ext = Path(path).suffix.lower()
    
    if ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in ARCHIVE_EXTENSIONS:
        return "archive"
    else:
        return "unknown"
