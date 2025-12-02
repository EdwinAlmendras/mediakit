"""
Tests for SetProcessor facade.
"""
import pytest
from pathlib import Path
from PIL import Image

from mediakit import SetProcessor, SetProcessorConfig, ResizeQuality


class TestSetProcessorConfig:
    """Tests for SetProcessorConfig dataclass."""
    
    def test_defaults(self):
        config = SetProcessorConfig()
        
        assert len(config.resize_qualities) == 3
        assert ResizeQuality.SMALL in config.resize_qualities
        assert config.preview_cell_size == 400
        assert config.archive_compression == 0
        assert config.archive_max_part_size is None
    
    def test_custom_qualities(self):
        config = SetProcessorConfig(
            resize_qualities=[ResizeQuality.SMALL]
        )
        
        assert len(config.resize_qualities) == 1
        assert config.resize_qualities[0] == ResizeQuality.SMALL


class TestSetProcessor:
    """Tests for SetProcessor class."""
    
    def test_creation(self):
        processor = SetProcessor()
        
        assert processor.config is not None
        assert processor.selector is not None
        assert processor.resizer is not None
    
    def test_creation_with_config(self):
        config = SetProcessorConfig(preview_cell_size=300)
        processor = SetProcessor(config)
        
        assert processor.config.preview_cell_size == 300
    
    def test_get_metadata(self, sample_image_set):
        processor = SetProcessor()
        
        metadata = processor.get_metadata(sample_image_set)
        
        assert metadata.image_count == 5
        assert metadata.path == sample_image_set
        assert metadata.cover_path is not None
        assert metadata.max_dimensions.width > 0
    
    def test_get_metadata_empty_raises(self, empty_dir):
        processor = SetProcessor()
        
        with pytest.raises(ValueError, match="No images found"):
            processor.get_metadata(empty_dir)
    
    def test_select_cover(self, sample_image_set):
        processor = SetProcessor()
        
        cover = processor.select_cover(sample_image_set)
        
        assert cover.exists()
        assert cover.suffix.lower() in (".jpg", ".jpeg", ".png")
    
    def test_generate_preview(self, sample_image_set, temp_dir):
        processor = SetProcessor()
        output = temp_dir / "preview.jpg"
        
        result = processor.generate_preview(sample_image_set, output)
        
        assert result == output
        assert output.exists()
    
    def test_get_caption(self, sample_image_set):
        processor = SetProcessor()
        
        caption = processor.get_caption(sample_image_set)
        
        assert "MP" in caption
        assert "pics" in caption
    
    def test_get_caption_empty_returns_empty(self, empty_dir):
        processor = SetProcessor()
        
        caption = processor.get_caption(empty_dir)
        
        assert caption == ""
