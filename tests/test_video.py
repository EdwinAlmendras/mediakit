"""
Tests for video processing components.

Note: These tests require ffmpeg and ffprobe to be installed.
Video-related tests may be skipped if no test video is available.
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from mediakit.video import (
    VideoInfo,
    VideoConverter,
    ThumbnailGenerator,
    VideoGridGenerator,
    VideoCodecDetector,
    VideoDurationProvider,
)
from mediakit.video.grid_generator import GridSizeCalculator
from mediakit.video.thumbnail import FrameValidator, StepCalculator


class TestVideoInfo:
    """Tests for VideoInfo class."""
    
    def test_creation(self, temp_dir):
        video_path = temp_dir / "test.mp4"
        video_path.touch()
        
        info = VideoInfo(video_path)
        
        assert info.input_path == video_path
        assert info._loaded is False
    
    def test_ensure_loaded_raises_when_not_loaded(self, temp_dir):
        video_path = temp_dir / "test.mp4"
        video_path.touch()
        
        info = VideoInfo(video_path)
        
        with pytest.raises(RuntimeError, match="not loaded"):
            _ = info.duration
    
    def test_validate_nonexistent_file(self, temp_dir):
        video_path = temp_dir / "nonexistent.mp4"
        
        info = VideoInfo(video_path)
        
        with pytest.raises(ValueError, match="does not exist"):
            info._validate_input()
    
    def test_validate_directory_raises(self, temp_dir):
        info = VideoInfo(temp_dir)
        
        with pytest.raises(ValueError, match="not a file"):
            info._validate_input()


class TestVideoCodecDetector:
    """Tests for VideoCodecDetector class."""
    
    def test_get_codec_nonexistent_file(self, temp_dir):
        fake_path = temp_dir / "fake.mp4"
        
        codec = VideoCodecDetector.get_codec(fake_path)
        
        assert codec == ""


class TestVideoDurationProvider:
    """Tests for VideoDurationProvider class."""
    
    def test_get_duration_nonexistent_file(self, temp_dir):
        fake_path = temp_dir / "fake.mp4"
        
        duration = VideoDurationProvider.get_duration(fake_path)
        
        assert duration == 0.0


class TestGridSizeCalculator:
    """Tests for GridSizeCalculator class."""
    
    def test_short_video_returns_none(self):
        calculator = GridSizeCalculator()
        
        result = calculator.calculate(3.0)
        
        assert result is None
    
    def test_medium_video_returns_3(self):
        calculator = GridSizeCalculator()
        
        result = calculator.calculate(60.0)
        
        assert result == 3
    
    def test_long_video_returns_4(self):
        calculator = GridSizeCalculator()
        
        result = calculator.calculate(600.0)
        
        assert result == 4
    
    def test_very_long_video_returns_5(self):
        calculator = GridSizeCalculator()
        
        result = calculator.calculate(3600.0)
        
        assert result == 5


class TestStepCalculator:
    """Tests for StepCalculator class."""
    
    def test_very_short_video(self):
        step = StepCalculator.calculate(5.0)
        assert step == 1
    
    def test_short_video(self):
        step = StepCalculator.calculate(30.0)
        assert step == 2
    
    def test_long_video(self):
        step = StepCalculator.calculate(120.0)
        assert step == 10


class TestFrameValidator:
    """Tests for FrameValidator class."""
    
    def test_is_valid_nonexistent_file(self, temp_dir):
        fake_path = temp_dir / "fake.jpg"
        
        result = FrameValidator.is_valid(fake_path)
        
        assert result is False
    
    def test_is_valid_blank_image(self, temp_dir):
        from PIL import Image
        
        blank = temp_dir / "blank.jpg"
        img = Image.new("RGB", (100, 100), color="black")
        img.save(blank, "JPEG")
        
        result = FrameValidator.is_valid(blank)
        
        assert result is False
    
    def test_is_valid_colorful_image(self, temp_dir):
        from PIL import Image
        import random
        
        colorful = temp_dir / "colorful.jpg"
        img = Image.new("RGB", (100, 100))
        pixels = img.load()
        for i in range(100):
            for j in range(100):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img.save(colorful, "JPEG")
        
        result = FrameValidator.is_valid(colorful)
        
        assert result is True


class TestThumbnailGenerator:
    """Tests for ThumbnailGenerator class."""
    
    def test_creation(self):
        generator = ThumbnailGenerator(quality=3)
        
        assert generator.quality == 3
    
    def test_create_temp_output(self):
        generator = ThumbnailGenerator()
        
        output = generator._create_temp_output()
        
        assert output.suffix == ".jpg"
        
        output.unlink(missing_ok=True)


class TestVideoConverter:
    """Tests for VideoConverter class."""
    
    def test_creation(self):
        converter = VideoConverter()
        
        assert converter.config is not None
        assert "h264" in converter.config.supported_codecs
    
    def test_needs_conversion_nonexistent_raises(self, temp_dir):
        converter = VideoConverter()
        fake_path = temp_dir / "fake.mp4"
        
        with pytest.raises(FileNotFoundError):
            converter.needs_conversion(fake_path)
