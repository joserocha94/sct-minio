import logging
import os
import time
from pathlib import Path

from watchdog.observers import Observer

from .handlers import LocalChangeHandler
from .sync_manager import MinioSyncManager

# configure stdout logging to later be synced with logstash
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=os.getenv('LOG_LEVEL', 'INFO'),
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    observer = None  # define observer (inotify) outside try block

    try:
        sync_manager = MinioSyncManager()
        event_handler = LocalChangeHandler(sync_manager)

        # set up local file monitoring for output and backup
        observer = Observer()
        for dir_name in ['output', 'backup']:
            path = sync_manager.base_path / dir_name
            observer.schedule(event_handler, str(path), recursive=True)

        observer.start()

        logger.info("Starting file synchronization service")
        logger.info("Configurations:")
        logger.info(f"- Base path: {sync_manager.base_path}")
        logger.info(f"- Max file age: {sync_manager.max_age_days} days")
        logger.info(f"- Sync interval: {os.getenv('SYNC_INTERVAL', '5')} seconds")
        logger.info("Monitoring:")
        logger.info("- MinIO 'input' directory for downloads")
        logger.info("- Local 'output' and 'backup' directories for uploads")

        while True:
            sync_manager.sync_from_minio()  # check for new files in MinIO
            sync_manager.clean_old_files()   # clean old files from input directory
            time.sleep(int(os.getenv('SYNC_INTERVAL', '5')))

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if observer:  # only stop and join if observer was created
            observer.stop()
            observer.join()

if __name__ == "__main__":
    main()
