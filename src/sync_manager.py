import hashlib
import io
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

class MinioSyncManager:
    """
    Manages synchronization between local filesystem and MinIO storage.

    Handles three main directories:
    - input/: Downloads from MinIO to local, then deletes from MinIO
    - output/: Uploads from local to MinIO, then deletes from local
    - backup/: Same as output
    """

    def __init__(self):
        self._setup_minio_client()
        self.bucket_name = os.getenv('MINIO_BUCKET_NAME', 'storage')
        self.base_path = Path(os.getenv('FOLDER_PATH_SYNC', '/home/sign'))
        self.max_age_days = int(os.getenv('MAX_FILE_AGE_DAYS', '1'))

        self._initialize_storage()
        self.last_minio_state: Dict[str, Dict] = {}

    def _setup_minio_client(self) -> None:
        """Initialize MinIO client with proper configuration."""
        endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000').rstrip('/')
        access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')

        try:
            self.minio_client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=os.getenv('MINIO_SECURE', 'false').lower() == 'true'
            )
            logger.info(f"Successfully connected to MinIO at {endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise

    def _initialize_storage(self) -> None:
        """Initialize storage structures."""
        # create local directories
        for dir_name in ['input', 'output', 'backup']:
            dir_path = self.base_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured local directory exists: {dir_path}")

        # ensure MinIO bucket and input directory exist
        try:
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")

            self._ensure_input_directory()
        except S3Error as e:
            logger.error(f"Error initializing MinIO storage: {e}")
            raise

    def _ensure_input_directory(self) -> None:
        """Ensure input directory exists in MinIO with placeholder."""
        content = "This is a placeholder file to maintain the input directory structure."
        content_bytes = content.encode('utf-8')
        content_stream = io.BytesIO(content_bytes)

        try:
            self.minio_client.put_object(
                self.bucket_name,
                "input/.directory_placeholder",
                content_stream,
                len(content_bytes)
            )
            logger.info("Ensured MinIO input directory exists with placeholder")
        except Exception as e:
            logger.error(f"Error creating input directory placeholder: {e}")
            raise

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _verify_file_integrity(self, local_path: Path, minio_path: str) -> bool:
        """Verify file integrity between local and MinIO versions."""
        try:
            local_hash = self._calculate_file_hash(local_path)

            # get MinIO object's ETag (MD5 hash)
            stat = self.minio_client.stat_object(self.bucket_name, minio_path)
            minio_hash = stat.etag.strip('"')  # MinIO returns ETag in quotes

            return local_hash == minio_hash
        except Exception as e:
            logger.error(f"Error verifying file integrity: {e}")
            return False

    def clean_old_files(self) -> None:
        """
        Cleanup routine that runs periodically:
        1. Remove files older than MAX_FILE_AGE_DAYS
        2. Remove empty directories older than MAX_FILE_AGE_DAYS
        """
        cutoff_time = datetime.now() - timedelta(days=self.max_age_days)

        for dir_name in ['input', 'output', 'backup']:
            dir_path = self.base_path / dir_name
            try:
                # remove old files first
                for file_path in dir_path.rglob('*'):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time.timestamp():
                        try:
                            file_path.unlink()
                            logger.info(f"Deleted expired file from {dir_name}: {file_path}")
                        except Exception as e:
                            logger.error(f"Error deleting expired file {file_path}: {e}")

                # then clean up empty directories that are too old
                if dir_name in ['output', 'backup']:
                    for dirpath in sorted(dir_path.rglob('*'), reverse=True):  # bottom-up traversal
                        if dirpath.is_dir():
                            try:
                                # check if directory is empty and old enough
                                if not any(dirpath.iterdir()) and \
                                   dirpath.stat().st_mtime < cutoff_time.timestamp():
                                    dirpath.rmdir()
                                    logger.info(f"Removed old empty directory: {dirpath}")
                            except Exception as e:
                                logger.debug(f"Could not remove directory {dirpath}: {e}")
                                continue

            except Exception as e:
                logger.error(f"Error cleaning old files in {dir_name}: {e}")

    def sync_from_minio(self) -> None:
        """Sync files from MinIO input directory to local."""
        try:
            objects = self.minio_client.list_objects(self.bucket_name, prefix='input/')
            for obj in objects:
                # skip placeholder
                if obj.object_name.endswith('.directory_placeholder'):
                    continue

                local_path = self.base_path / obj.object_name
                local_path.parent.mkdir(parents=True, exist_ok=True)

                # download file
                self.minio_client.fget_object(
                    self.bucket_name,
                    obj.object_name,
                    str(local_path)
                )
                logger.info(f"Downloaded from MinIO: {obj.object_name}")

                # verify and delete from MinIO if successful
                if self._verify_file_integrity(local_path, obj.object_name):
                    self.minio_client.remove_object(self.bucket_name, obj.object_name)
                    logger.info(f"Verified and removed from MinIO: {obj.object_name}")
                else:
                    logger.error(f"File integrity check failed: {obj.object_name}")
                    local_path.unlink()  # remove potentially corrupted local file

        except Exception as e:
            logger.error(f"Error syncing from MinIO: {e}")

    def sync_to_minio(self, local_path: Path) -> None:
        """
        Sync file to MinIO. Upon successful sync:
        1. Remove the file
        2. Remove its parent directory if empty
        """
        try:
            if not local_path.is_file():
                return

            rel_path = local_path.relative_to(self.base_path)
            folder = rel_path.parts[0]

            if folder not in ['output', 'backup']:
                return

            logger.info(f"Starting sync for file: {rel_path}")

            try:
                # check if the folder exists
                objects = list(self.minio_client.list_objects(
                    self.bucket_name, 
                    prefix=f"{folder}/", 
                    recursive=False,
                    include_user_meta=False
                ))
                
                if not objects:
                    logger.info(f"Directory {folder}/ doesn't exist in MinIO, creating it")
                    # folder does not exist, - create an empty object with a trailing slash
                    self.minio_client.put_object(
                        self.bucket_name,
                        f"{folder}/",
                        io.BytesIO(b''),
                        0
                    )
            except Exception as e:
                logger.warning(f"Error checking/creating MinIO directory {folder}/: {e}")

            # get all files in the same directory
            parent_dir = local_path.parent
            files_to_sync = list(parent_dir.glob('*'))

            # track successful syncs
            all_syncs_successful = True

            for file_path in files_to_sync:
                if not file_path.is_file():
                    continue

                try:
                    file_rel_path = str(file_path.relative_to(self.base_path))

                    # upload to MinIO
                    self.minio_client.fput_object(
                        self.bucket_name,
                        file_rel_path,
                        str(file_path)
                    )
                    logger.info(f"Uploaded to MinIO: {file_rel_path}")

                    # verify upload
                    if self._verify_file_integrity(file_path, file_rel_path):
                        file_path.unlink()
                        logger.info(f"Verified and removed local file: {file_rel_path}")
                    else:
                        logger.error(f"Upload verification failed: {file_rel_path}")
                        all_syncs_successful = False

                except Exception as e:
                    logger.error(f"Error syncing file {file_path}: {e}")
                    all_syncs_successful = False

            # if all files were synced successfully, try to remove the directory
            if all_syncs_successful:
                try:
                    # check if directory is empty
                    if not any(parent_dir.iterdir()):
                        parent_dir.rmdir()
                        logger.info(f"Removed empty directory after successful sync: {parent_dir}")
                except Exception as e:
                    logger.warning(f"Could not remove directory {parent_dir} after sync: {e}")

        except Exception as e:
            logger.error(f"Error in sync operation: {e}")

    def _cleanup_empty_directories(self, directory: Path, base_folder: str) -> None:
        """
        Recursively clean up directories that are either:
        - Empty and older than MAX_FILE_AGE_DAYS
        - Contain only successfully synced files
        """
        try:
            base_dir = self.base_path / base_folder
            current_dir = directory

            while current_dir != base_dir:
                if self._is_directory_safe_to_remove(current_dir):
                    try:
                        current_dir.rmdir()
                        logger.info(f"Removed directory: {current_dir}")
                    except Exception as e:
                        logger.debug(f"Could not remove directory {current_dir}: {e}")
                        break
                else:
                    break

                current_dir = current_dir.parent

        except Exception as e:
            logger.error(f"Error cleaning up directories: {e}")

    def _is_directory_safe_to_remove(self, directory: Path) -> bool:
        """
        Check if a directory is safe to remove:
        - Empty AND older than MAX_FILE_AGE_DAYS OR
        - All files must be successfully synced to MinIO
        """
        try:
            # check if directory is empty
            if not any(directory.iterdir()):
                # if empty, check its age to rip him off
                dir_mtime = directory.stat().st_mtime
                cutoff_time = (datetime.now() - timedelta(days=self.max_age_days)).timestamp()
                if dir_mtime < cutoff_time:
                    logger.info(f"Directory {directory} is empty and older than {self.max_age_days} days")
                    return True
                else:
                    logger.debug(f"Directory {directory} is empty but not old enough to remove")
                    return False

            # if not empty, check each file
            for item in directory.rglob('*'):
                if item.is_file():
                    # get the relative path for MinIO comparison
                    rel_path = str(item.relative_to(self.base_path))

                    # check if file exists in MinIO and verify integrity
                    try:
                        if not self._verify_file_integrity(item, rel_path):
                            return False
                    except Exception as e:
                        logger.debug(f"File verification failed for {item}: {e}")
                        return False

            # if we get here, all files are synced
            return True

        except Exception as e:
            logger.error(f"Error checking directory safety: {e}")
            return False
