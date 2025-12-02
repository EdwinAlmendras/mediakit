"""
Example: Video Processing with MediaKit

This example demonstrates how to:
- Extract video information
- Generate video thumbnails
- Create video grid previews
- Generate video sprite sheets for players
"""
import asyncio
from pathlib import Path
from mediakit.video import (
    VideoInfo,
    VideoConverter,
    ThumbnailGenerator,
    VideoGridGenerator,
    VideoSpriteGenerator,
    VideoGridConfig,
    SpriteConfig,
    generate_video_grid,
)


async def get_video_info(video_path: Path):
    """Extract and display video information."""
    info = VideoInfo(video_path)
    await info.load()
    
    print(f"Video: {video_path.name}")
    print(f"  Duration: {info.duration:.2f}s")
    print(f"  Dimensions: {info.width}x{info.height}")
    print(f"  Display: {info.dimensions.display_width}x{info.dimensions.display_height}")
    print(f"  Rotation: {info.rotation}°")
    print(f"  Codec: {info.codec}")
    print(f"  FPS: {info.fps}")
    print(f"  Bitrate: {info.bitrate // 1000} kbps")
    
    if info.frame_count:
        print(f"  Frames: {info.frame_count}")
    
    return info


def check_and_convert_video(video_path: Path):
    """Check if video needs conversion and convert if necessary."""
    converter = VideoConverter()
    
    if converter.needs_conversion(video_path):
        print(f"Video needs conversion: {video_path.name}")
        output = converter.convert(video_path)
        print(f"Converted to: {output}")
        return output
    
    print(f"Video is compatible: {video_path.name}")
    return video_path


def generate_thumbnail(video_path: Path, output_path: Path = None):
    """Generate a thumbnail from video."""
    generator = ThumbnailGenerator(quality=2)
    
    thumbnail = generator.generate(video_path, output_path)
    print(f"Thumbnail generated: {thumbnail}")
    
    return thumbnail


async def generate_grid_preview(video_path: Path, output_path: Path = None):
    """Generate a grid preview from video."""
    config = VideoGridConfig(
        grid_size=4,
        max_size=480,
        max_parallel=8
    )
    
    generator = VideoGridGenerator(video_path, config, output_path)
    grid = await generator.generate()
    
    print(f"Grid preview generated: {grid}")
    return grid


async def generate_sprites(video_path: Path, output_dir: Path):
    """Generate sprite sheets for video player preview."""
    config = SpriteConfig(
        grid_size=10,
        interval=5.0,
        max_size=160,
        output_prefix="sprite_"
    )
    
    generator = VideoSpriteGenerator(config)
    sprites, vtt = await generator.generate(video_path, output_dir)
    
    print(f"Generated {len(sprites)} sprite sheets")
    print(f"VTT file: {vtt}")
    
    return sprites, vtt


async def main():
    """Main example entry point."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_processing.py <video_path>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        sys.exit(1)
    
    print("=" * 50)
    print("Video Information")
    print("=" * 50)
    await get_video_info(video_path)
    
    print("\n" + "=" * 50)
    print("Thumbnail Generation")
    print("=" * 50)
    generate_thumbnail(video_path)
    
    print("\n" + "=" * 50)
    print("Grid Preview Generation")
    print("=" * 50)
    await generate_grid_preview(video_path)
    
    print("\n" + "=" * 50)
    print("Quick Grid (convenience function)")
    print("=" * 50)
    grid = await generate_video_grid(video_path, grid_size=3, max_size=320)
    print(f"Quick grid: {grid}")


if __name__ == "__main__":
    asyncio.run(main())
