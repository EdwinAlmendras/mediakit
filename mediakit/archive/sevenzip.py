"""
7-Zip archive creation and validation.
Independent of any upload/telegram logic.
"""
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import subprocess
import logging
import math

from natsort import natsorted

from ..core.interfaces import IArchiver

logger = logging.getLogger(__name__)


@dataclass
class ArchiveConfig:
    """Configuration for archive creation."""
    compression_level: int = 0
    max_part_size: Optional[int] = None
    password: Optional[str] = None
    encrypt_names: bool = True
    files_only: bool = False
    output_dir: Optional[Path] = None


class SevenZipArchiver(IArchiver):
    """
    Creates and validates 7-Zip archives.
    Supports multi-part archives and encryption.
    """
    
    def __init__(self, config: Optional[ArchiveConfig] = None):
        self.config = config or ArchiveConfig()
    
    def create(
        self, 
        folder: Path, 
        output_name: str,
        password: Optional[str] = None,
        max_part_size: Optional[int] = None
    ) -> List[Path]:
        """
        Create 7z archive from folder.
        
        Args:
            folder: Source folder to archive
            output_name: Archive filename (without path)
            password: Optional password for encryption
            max_part_size: Max size per part in bytes (for splitting)
            
        Returns:
            List of created archive files
        """
        folder = Path(folder)
        if not folder.exists() or not folder.is_dir():
            logger.error(f"Folder not found: {folder}")
            return []
        
        if not output_name.endswith('.7z'):
            output_name += '.7z'
        
        output_dir = self.config.output_dir or (folder.parent / "files")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        archive_path = output_dir / output_name
        
        password = password or self.config.password
        max_part_size = max_part_size or self.config.max_part_size
        
        cmd = self._build_command(folder, archive_path, password, max_part_size)
        
        logger.info(f"Creating archive: {output_name}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=folder.parent,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line and not line.startswith('7-Zip'):
                    logger.debug(line)
            
            process.wait()
            
            if process.returncode == 0:
                return self._collect_archive_files(output_dir, output_name)
            else:
                logger.error(f"7z failed with code: {process.returncode}")
                return []
                
        except FileNotFoundError:
            logger.error("7zip not found. Install 7zip and add to PATH")
            return []
        except Exception as e:
            logger.error(f"Error creating archive: {e}")
            return []
    
    def validate(self, archive_path: Path) -> bool:
        """Validate archive integrity."""
        try:
            result = subprocess.run(
                ["7z", "t", str(archive_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _build_command(
        self, 
        folder: Path, 
        archive_path: Path,
        password: Optional[str],
        max_part_size: Optional[int]
    ) -> List[str]:
        """Build 7z command."""
        cmd = ["7z", "a", str(archive_path.resolve()), f"-mx{self.config.compression_level}"]
        
        if max_part_size:
            cmd.append(f"-v{max_part_size}b")
        
        if password:
            cmd.extend([f"-p{password}"])
            if self.config.encrypt_names:
                cmd.append("-mhe=on")
        
        if self.config.files_only:
            files = [f for f in folder.iterdir() if f.is_file()]
            files = natsorted(files)
            for f in files:
                cmd.append(f"{folder.name}/{f.name}")
        else:
            cmd.append(str(folder.name))
        
        return cmd
    
    def _collect_archive_files(self, output_dir: Path, archive_name: str) -> List[Path]:
        """Collect all created archive files (including parts)."""
        files = []
        for f in output_dir.iterdir():
            if f.is_file() and archive_name in f.name:
                files.append(f.absolute())
        return natsorted(files)
    
    @staticmethod
    def calculate_parts(folder: Path, max_part_size: int) -> int:
        """Calculate number of parts needed for folder."""
        total_size = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
        return math.ceil(total_size / max_part_size)
