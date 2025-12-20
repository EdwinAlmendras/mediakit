"""
Centralized media file extensions.

Used by: mediakit, uploader, social, kmp
"""
video_extensions = ['webm', 'mkv', 'flv', 'vob', 'ogv', 'ogg', 'rrc', 'gifv', 'mts', 'mng', 'mov', 'avi', 'qt', 'wmv', 'yuv', 'rm', 'asf', 'amv', 'mp4', 'm4p', 'm4v', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv', 'm4v', 'svi', '3gp', '3g2', 'mxf', 'roq', 'nsv', 'flv', 'f4v', 'f4p', 'f4a', 'f4b', 'mod'] 
VIDEO_EXTENSIONS = set(f".{extension}" for extension in video_extensions)

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
