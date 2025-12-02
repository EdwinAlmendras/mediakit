"""
Tests for preview generation components.
"""
import pytest
from pathlib import Path
from PIL import Image

from mediakit.preview import ImagePreviewGenerator, GridConfig


class TestImagePreviewGenerator:
    """Tests for ImagePreviewGenerator class."""
    
    def test_generate(self, sample_image_set, temp_dir):
        generator = ImagePreviewGenerator(cell_size=100)
        output = temp_dir / "preview.jpg"
        
        result = generator.generate(sample_image_set, output)
        
        assert result == output
        assert output.exists()
    
    def test_generate_with_config(self, sample_image_set, temp_dir):
        generator = ImagePreviewGenerator(cell_size=100)
        output = temp_dir / "preview.jpg"
        config = GridConfig(rows=2, cols=2, cell_size=100)
        
        result = generator.generate(sample_image_set, output, config)
        
        assert output.exists()
        
        with Image.open(output) as img:
            assert img.size == (200, 200)
    
    def test_generate_temp_output(self, sample_image_set):
        generator = ImagePreviewGenerator(cell_size=100)
        
        result = generator.generate(sample_image_set)
        
        assert result.exists()
        assert result.suffix == ".jpg"
        
        result.unlink()
    
    def test_generate_empty_folder_raises(self, empty_dir):
        generator = ImagePreviewGenerator()
        
        with pytest.raises(ValueError, match="No images found"):
            generator.generate(empty_dir)
    
    def test_generate_from_images(self, sample_image_set, temp_dir):
        generator = ImagePreviewGenerator(cell_size=100)
        from mediakit.image import ImageSelector
        
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        output = temp_dir / "preview.jpg"
        
        result = generator.generate_from_images(images, output)
        
        assert result == output
        assert output.exists()


class TestGridConfig:
    """Tests for GridConfig dataclass."""
    
    def test_defaults(self):
        config = GridConfig()
        
        assert config.rows == 4
        assert config.cols == 3
        assert config.cell_size == 400
        assert config.randomize is False
        assert config.recursive is False
    
    def test_max_images(self):
        config = GridConfig(rows=5, cols=4)
        
        assert config.max_images == 20
    
    def test_custom_values(self):
        config = GridConfig(
            rows=3,
            cols=3,
            cell_size=200,
            randomize=True,
            recursive=True
        )
        
        assert config.rows == 3
        assert config.randomize is True
        assert config.recursive is True
