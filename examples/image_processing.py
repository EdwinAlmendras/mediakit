"""
Example: Image Set Processing with MediaKit

This example demonstrates how to:
- Process an image set (resize, generate preview, create archive)
- Use individual components for specific tasks
"""
from pathlib import Path
from mediakit import (
    SetProcessor,
    SetProcessorConfig,
    ResizeQuality,
    ImageSelector,
    ImagePreviewGenerator,
    SevenZipArchiver,
)


def process_complete_set(folder: Path):
    """Process a complete image set using the facade."""
    config = SetProcessorConfig(
        resize_qualities=[ResizeQuality.SMALL, ResizeQuality.MEDIUM],
        preview_cell_size=400,
        archive_compression=0,
    )
    
    processor = SetProcessor(config)
    
    metadata = processor.process(folder)
    print(f"Processed {metadata.image_count} images")
    print(f"Max dimensions: {metadata.max_dimensions.width}x{metadata.max_dimensions.height}")
    print(f"Cover image: {metadata.cover_path}")
    
    preview_path = processor.generate_preview(folder)
    print(f"Preview generated: {preview_path}")
    
    archives = processor.create_archive(folder, f"{folder.name}.7z")
    print(f"Archives created: {archives}")
    
    caption = processor.get_caption(folder)
    print(f"Caption: {caption}")
    
    return metadata


def use_individual_components(folder: Path):
    """Use individual components for specific tasks."""
    selector = ImageSelector()
    images = selector.get_images(folder)
    print(f"Found {len(images)} images")
    
    cover = selector.select_cover(images)
    print(f"Selected cover: {cover}")
    
    distributed = selector.select_distributed(images, 12)
    print(f"Selected {len(distributed)} distributed images")
    
    preview_gen = ImagePreviewGenerator(cell_size=300)
    preview = preview_gen.generate(folder, folder / "preview.jpg")
    print(f"Preview: {preview}")
    
    archiver = SevenZipArchiver()
    archives = archiver.create(folder, "output.7z", password="secret123")
    print(f"Encrypted archives: {archives}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python image_processing.py <folder_path>")
        sys.exit(1)
    
    folder = Path(sys.argv[1])
    if not folder.exists():
        print(f"Folder not found: {folder}")
        sys.exit(1)
    
    process_complete_set(folder)
