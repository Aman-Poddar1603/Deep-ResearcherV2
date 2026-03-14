"""
BucketStore — physical file-system layer for bucket storage.

Directory layout (rooted at this file's directory):
    <bucket_id>/
        images/
        videos/
        files/
        audio/
        others/

Stored paths in the DB are relative to this root, e.g. "abc123/images/photo.jpg".
"""

import shutil
from pathlib import Path

BUCKET_SUBFOLDERS = ["images", "videos", "files", "audio", "others"]

# file extension → subfolder mapping
_FORMAT_MAP: dict[str, str] = {
    # images
    "jpg": "images",
    "jpeg": "images",
    "png": "images",
    "gif": "images",
    "webp": "images",
    "svg": "images",
    "bmp": "images",
    "tiff": "images",
    "ico": "images",
    # videos
    "mp4": "videos",
    "avi": "videos",
    "mov": "videos",
    "mkv": "videos",
    "wmv": "videos",
    "flv": "videos",
    "webm": "videos",
    # audio
    "mp3": "audio",
    "wav": "audio",
    "ogg": "audio",
    "flac": "audio",
    "aac": "audio",
    "m4a": "audio",
    # documents / general files
    "pdf": "files",
    "doc": "files",
    "docx": "files",
    "xls": "files",
    "xlsx": "files",
    "ppt": "files",
    "pptx": "files",
    "txt": "files",
    "csv": "files",
    "json": "files",
    "xml": "files",
    "zip": "files",
    "tar": "files",
    "gz": "files",
    "rar": "files",
}


class BucketStore:
    """Manages physical file storage for buckets."""

    def __init__(self, root: Path | None = None) -> None:
        # Default root is the directory this module lives in
        self.root: Path = root or Path(__file__).parent

    # ------------------------------------------------------------------ helpers

    def _bucket_path(self, bucket_id: str) -> Path:
        return self.root / bucket_id

    def _subfolder_for_format(self, file_format: str) -> str:
        ext = file_format.lstrip(".").lower()
        return _FORMAT_MAP.get(ext, "others")

    def _rel_path(self, bucket_id: str, subfolder: str, file_name: str) -> str:
        """Return relative path string stored in the DB."""
        return f"{bucket_id}/{subfolder}/{file_name}"

    def abs_path(self, rel_path: str) -> Path:
        """Resolve a stored relative path to an absolute Path."""
        return self.root / rel_path

    # ----------------------------------------------------------- bucket dirs

    def create_bucket_directory(self, bucket_id: str) -> None:
        """Create the bucket directory tree with all standard subfolders."""
        bucket_path = self._bucket_path(bucket_id)
        for subfolder in BUCKET_SUBFOLDERS:
            (bucket_path / subfolder).mkdir(parents=True, exist_ok=True)

    def delete_bucket_directory(self, bucket_id: str) -> None:
        """Recursively delete the entire bucket directory."""
        bucket_path = self._bucket_path(bucket_id)
        if bucket_path.exists():
            shutil.rmtree(bucket_path)

    # ----------------------------------------------------------- file ops

    def save_file(
        self,
        bucket_id: str,
        file_format: str,
        file_name: str,
        content: bytes,
    ) -> str:
        """
        Write bytes to the correct subfolder.
        Returns the relative path string (for DB storage).
        """
        subfolder = self._subfolder_for_format(file_format)
        dest = self._bucket_path(bucket_id) / subfolder / file_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return self._rel_path(bucket_id, subfolder, file_name)

    def delete_file(self, stored_path: str) -> bool:
        """
        Delete a file by its stored path (relative or absolute).
        Returns True if the file was deleted, False if it did not exist.
        """
        path = Path(stored_path)
        if not path.is_absolute():
            path = self.root / path
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False

    # ----------------------------------------------------------- stats

    def get_file_count(self, bucket_id: str) -> int:
        """Count all files inside the bucket directory."""
        bucket_path = self._bucket_path(bucket_id)
        if not bucket_path.exists():
            return 0
        return sum(1 for f in bucket_path.rglob("*") if f.is_file())

    def get_bucket_size(self, bucket_id: str) -> int:
        """Return total size in bytes of all files inside the bucket directory."""
        bucket_path = self._bucket_path(bucket_id)
        if not bucket_path.exists():
            return 0
        return sum(f.stat().st_size for f in bucket_path.rglob("*") if f.is_file())


# Singleton used by the bucket orchestrator
bucket_store = BucketStore()
