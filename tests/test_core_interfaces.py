"""
Tests for core interfaces and data types.
"""
import pytest
from pathlib import Path
from mediakit.core.interfaces import (
    ImageDimensions,
    VideoDimensions,
    SetMetadata,
    PreviewConfig,
    ResizeQuality,
    VideoGridConfig,
    VideoConversionConfig,
)


class TestImageDimensions:
    """Tests for ImageDimensions dataclass."""
    
    def test_creation(self):
        dims = ImageDimensions(width=1920, height=1080)
        assert dims.width == 1920
        assert dims.height == 1080
    
    def test_min_dimension(self):
        dims = ImageDimensions(width=1920, height=1080)
        assert dims.min_dimension == 1080
    
    def test_max_dimension(self):
        dims = ImageDimensions(width=1920, height=1080)
        assert dims.max_dimension == 1920
    
    def test_megapixels(self):
        dims = ImageDimensions(width=1920, height=1080)
        expected = (1920 * 1080) / 1_000_000
        assert abs(dims.megapixels - expected) < 0.001
    
    def test_aspect_ratio(self):
        dims = ImageDimensions(width=1920, height=1080)
        expected = 1920 / 1080
        assert abs(dims.aspect_ratio - expected) < 0.001
    
    def test_is_portrait(self):
        portrait = ImageDimensions(width=1080, height=1920)
        landscape = ImageDimensions(width=1920, height=1080)
        
        assert portrait.is_portrait is True
        assert landscape.is_portrait is False
    
    def test_is_landscape(self):
        portrait = ImageDimensions(width=1080, height=1920)
        landscape = ImageDimensions(width=1920, height=1080)
        
        assert portrait.is_landscape is False
        assert landscape.is_landscape is True


class TestVideoDimensions:
    """Tests for VideoDimensions dataclass."""
    
    def test_creation_with_defaults(self):
        dims = VideoDimensions(width=1920, height=1080)
        assert dims.width == 1920
        assert dims.height == 1080
        assert dims.display_width == 1920
        assert dims.display_height == 1080
        assert dims.rotation == 0
    
    def test_creation_with_rotation(self):
        dims = VideoDimensions(
            width=1920, 
            height=1080,
            display_width=1080,
            display_height=1920,
            rotation=90
        )
        assert dims.rotation == 90
        assert dims.display_width == 1080
        assert dims.display_height == 1920


class TestSetMetadata:
    """Tests for SetMetadata dataclass."""
    
    def test_creation(self):
        dims = ImageDimensions(1920, 1080)
        metadata = SetMetadata(
            path=Path("/test/set"),
            image_count=50,
            max_dimensions=dims,
            cover_path=Path("/test/set/cover.jpg")
        )
        
        assert metadata.image_count == 50
        assert metadata.max_dimensions.width == 1920
        assert metadata.cover_path is not None


class TestResizeQuality:
    """Tests for ResizeQuality enum."""
    
    def test_values(self):
        assert ResizeQuality.SMALL.value == 320
        assert ResizeQuality.MEDIUM.value == 1280
        assert ResizeQuality.LARGE.value == 2048


class TestPreviewConfig:
    """Tests for PreviewConfig dataclass."""
    
    def test_defaults(self):
        config = PreviewConfig()
        assert config.rows == 4
        assert config.cols == 3
        assert config.cell_size == 400
        assert config.randomize is False
    
    def test_custom_values(self):
        config = PreviewConfig(rows=5, cols=4, cell_size=300, randomize=True)
        assert config.rows == 5
        assert config.cols == 4
        assert config.randomize is True


class TestVideoGridConfig:
    """Tests for VideoGridConfig dataclass."""
    
    def test_defaults(self):
        config = VideoGridConfig()
        assert config.grid_size == 4
        assert config.max_size == 480
        assert config.max_parallel == 8


class TestVideoConversionConfig:
    """Tests for VideoConversionConfig dataclass."""
    
    def test_defaults(self):
        config = VideoConversionConfig()
        assert config.codec == "libx264"
        assert config.preset == "fast"
        assert config.crf == 18
        assert "h264" in config.supported_codecs
        assert ".mp4" in config.supported_extensions
