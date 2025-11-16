from pathlib import Path
import shutil
import logging
from typing import Dict, Union


def ensure_directory(path: Union[str, Path]) -> Path:
    """Create directory if it doesn't exist and return its Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def copy_items(
    file_map: Dict[Union[str, Path], Union[str, Path]], *, logger: logging.Logger
) -> None:
    """Copy files according to the provided mapping.

    Args:
        file_map: Mapping of source paths to destination paths.
        logger: Logger instance for status messages.
    """
    for src, dst in file_map.items():
        src_path = Path(src)
        dst_path = Path(dst)
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                logger.info(f"Copied {src_path} to {dst_path}")
            else:
                logger.error(f"Source file not found: {src_path}")
        except Exception as exc:
            logger.error(f"Failed to copy {src_path} to {dst_path}: {exc}")
