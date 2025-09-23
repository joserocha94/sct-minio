import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class LocalChangeHandler(FileSystemEventHandler):
    """Handles local filesystem events for output and backup directories."""

    def __init__(self, sync_manager):
        self.sync_manager = sync_manager

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            path = Path(event.src_path)
            folder = path.parts[len(self.sync_manager.base_path.parts)]

            if folder in ['output', 'backup']:
                logger.info(f"New file detected: {path}")
                self.sync_manager.sync_to_minio(path)

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            path = Path(event.src_path)
            folder = path.parts[len(self.sync_manager.base_path.parts)]

            if folder in ['output', 'backup']:
                logger.info(f"Modified file detected: {path}")
                self.sync_manager.sync_to_minio(path)
