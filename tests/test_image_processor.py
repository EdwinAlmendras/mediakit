"""
Tests for image processing components.
"""
import pytest
from pathlib import Path
from PIL import Image

from mediakit.image import (
    ImageProcessor,
    ImageSelector,
    OrientationFixer,
)


class TestImageProcessor:
    """Tests for ImageProcessor class."""
    
    def test_is_valid_image(self, sample_image):
        assert ImageProcessor.is_valid_image(sample_image) is True
    
    def test_is_valid_image_false_for_directory(self, temp_dir):
        assert ImageProcessor.is_valid_image(temp_dir) is False
    
    def test_is_valid_image_false_for_nonexistent(self, temp_dir):
        fake_path = temp_dir / "nonexistent.jpg"
        assert ImageProcessor.is_valid_image(fake_path) is False
    
    def test_is_valid_image_false_for_wrong_extension(self, temp_dir):
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("not an image")
        assert ImageProcessor.is_valid_image(txt_file) is False
    
    def test_resize(self, sample_image, temp_dir):
        processor = ImageProcessor()
        output = temp_dir / "resized.jpg"
        
        result = processor.resize(sample_image, output, max_size=200)
        
        assert result == output
        assert output.exists()
        
        with Image.open(output) as img:
            assert max(img.size) <= 200
    
    def test_resize_preserves_aspect_ratio(self, sample_image, temp_dir):
        processor = ImageProcessor()
        output = temp_dir / "resized.jpg"
        
        processor.resize(sample_image, output, max_size=400)
        
        with Image.open(sample_image) as original:
            original_ratio = original.width / original.height
        
        with Image.open(output) as resized:
            resized_ratio = resized.width / resized.height
        
        assert abs(original_ratio - resized_ratio) < 0.01
    
    def test_smart_crop_to_square(self, sample_image):
        processor = ImageProcessor()
        
        result = processor.smart_crop_to_square(sample_image, 200)
        
        assert result.size == (200, 200)


class TestImageSelector:
    """Tests for ImageSelector class."""
    
    def test_get_images(self, sample_image_set):
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        
        assert len(images) == 5
        assert all(isinstance(p, Path) for p in images)
    
    def test_get_images_empty_dir(self, empty_dir):
        selector = ImageSelector()
        images = selector.get_images(empty_dir)
        
        assert len(images) == 0
    
    def test_get_images_sorted(self, sample_image_set):
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        
        names = [p.name for p in images]
        assert names == sorted(names)
    
    def test_select_cover(self, sample_image_set):
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        
        cover = selector.select_cover(images)
        
        assert cover in images
        assert cover.suffix.lower() in (".jpg", ".jpeg")
    
    def test_select_cover_prefers_portrait(self, temp_dir):
        portrait = temp_dir / "01_portrait.jpg"
        landscape = temp_dir / "02_landscape.jpg"
        
        Image.new("RGB", (600, 800)).save(portrait, "JPEG")
        Image.new("RGB", (800, 600)).save(landscape, "JPEG")
        
        selector = ImageSelector()
        images = selector.get_images(temp_dir)
        cover = selector.select_cover(images)
        
        assert cover == portrait
    
    def test_select_cover_empty_list_raises(self):
        selector = ImageSelector()
        
        with pytest.raises(ValueError, match="No images provided"):
            selector.select_cover([])
    
    def test_select_distributed(self, sample_image_set):
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        
        selected = selector.select_distributed(images, 3)
        
        assert len(selected) == 3
        assert all(img in images for img in selected)
    
    def test_select_distributed_more_than_available(self, sample_image_set):
        selector = ImageSelector()
        images = selector.get_images(sample_image_set)
        
        selected = selector.select_distributed(images, 100)
        
        assert len(selected) == len(images)


class TestOrientationFixer:
    """Tests for OrientationFixer class."""
    
    def test_fix_pil_image_no_exif(self, sample_image):
        with Image.open(sample_image) as img:
            original_size = img.size
            fixed = OrientationFixer.fix_pil_image(img)
            assert fixed.size == original_size
    
    def test_fix_file(self, sample_image, temp_dir):
        output = temp_dir / "fixed.jpg"
        
        result = OrientationFixer.fix_file(sample_image, output)
        
        assert result == output
        assert output.exists()
