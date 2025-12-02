"""
Pytest configuration and fixtures for MediaKit tests.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import numpy as np


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp(prefix="mediakit_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_image(temp_dir) -> Path:
    """Create a sample test image."""
    image_path = temp_dir / "test_image.jpg"
    img = Image.new("RGB", (800, 600), color="blue")
    img.save(image_path, "JPEG", quality=90)
    return image_path


@pytest.fixture
def sample_image_set(temp_dir) -> Path:
    """Create a sample image set with multiple images."""
    set_dir = temp_dir / "test_set"
    set_dir.mkdir()
    
    colors = ["red", "green", "blue", "yellow", "purple"]
    sizes = [(800, 600), (1024, 768), (640, 480), (1920, 1080), (600, 800)]
    
    for i, (color, size) in enumerate(zip(colors, sizes)):
        img_path = set_dir / f"image_{i:02d}.jpg"
        img = Image.new("RGB", size, color=color)
        img.save(img_path, "JPEG", quality=90)
    
    return set_dir


@pytest.fixture
def portrait_image(temp_dir) -> Path:
    """Create a portrait orientation image."""
    image_path = temp_dir / "portrait.jpg"
    img = Image.new("RGB", (600, 800), color="green")
    img.save(image_path, "JPEG", quality=90)
    return image_path


@pytest.fixture
def landscape_image(temp_dir) -> Path:
    """Create a landscape orientation image."""
    image_path = temp_dir / "landscape.jpg"
    img = Image.new("RGB", (800, 600), color="blue")
    img.save(image_path, "JPEG", quality=90)
    return image_path


@pytest.fixture
def png_image(temp_dir) -> Path:
    """Create a PNG image with transparency."""
    image_path = temp_dir / "transparent.png"
    img = Image.new("RGBA", (400, 400), color=(255, 0, 0, 128))
    img.save(image_path, "PNG")
    return image_path


@pytest.fixture
def empty_dir(temp_dir) -> Path:
    """Create an empty directory."""
    empty = temp_dir / "empty"
    empty.mkdir()
    return empty
