"""
BucketStore — physical file-system layer for bucket storage.

Directory layout (rooted at this file's directory):
    <bucket_id>/
    image/
    video/
        files/
        audio/
    other/

Stored paths in the DB are relative to this root, e.g. "abc123/image/photo.jpg".
"""

import shutil
from hashlib import md5
from pathlib import Path
from uuid import uuid4

BUCKET_SUBFOLDERS = ["image", "audio", "video", "files", "other"]

# file extension → subfolder mapping
_FORMAT_MAP: dict[str, str] = {
    # image
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
    "svg": "image",
    "bmp": "image",
    "tiff": "image",
    "ico": "image",
    # video
    "mp4": "video",
    "avi": "video",
    "mov": "video",
    "mkv": "video",
    "wmv": "video",
    "flv": "video",
    "webm": "video",
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
        # Keep file storage rooted at src/store/bucket even if this module moves.
        self.root: Path = root or (
            Path(__file__).resolve().parents[1] / "store" / "bucket"
        )

    # ------------------------------------------------------------------ helpers

    def _bucket_path(self, bucket_id: str) -> Path:
        return self.root / bucket_id

    def _subfolder_for_format(self, file_format: str) -> str:
        ext = file_format.lstrip(".").lower()
        return _FORMAT_MAP.get(ext, "other")

    def _rel_path(self, bucket_id: str, subfolder: str, file_name: str) -> str:
        """Return relative path string stored in the DB."""
        return f"{bucket_id}/{subfolder}/{file_name}"

    def _workspace_rel_path(self, section: str, file_name: str) -> str:
        """Return relative workspace-asset path stored in DB."""
        return f"workspace/{section}/{file_name}"

    def abs_path(self, rel_path: str) -> Path:
        """Resolve a stored relative path to an absolute Path."""
        return self.root / rel_path

    def resolve_asset_path(self, stored_path: str) -> Path:
        """
        Resolve and validate stored path to prevent directory traversal.
        Supports plain relative paths and "/bucket/assets/<path>" URLs.
        """
        normalized = stored_path.strip().lstrip("/")
        if normalized.startswith("bucket/assets/"):
            normalized = normalized[len("bucket/assets/") :]

        resolved = (self.root / normalized).resolve()
        root_resolved = self.root.resolve()
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise ValueError("Invalid asset path") from exc
        return resolved

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

    def save_workspace_asset(
        self,
        asset_type: str,
        original_file_name: str,
        content: bytes,
    ) -> str:
        """
        Save workspace banner/icon file using unique md5 name.

        asset_type: "banner" or "icons"
        Returns relative path (e.g. "workspace/banner/<md5>.png").
        """
        if asset_type not in {"banner", "icons"}:
            raise ValueError("asset_type must be 'banner' or 'icons'")

        ext = Path(original_file_name).suffix.lower() or ".bin"
        unique_hash = md5(
            (str(uuid4()) + str(len(content))).encode("utf-8") + content
        ).hexdigest()
        file_name = f"{unique_hash}{ext}"

        rel_path = self._workspace_rel_path(asset_type, file_name)
        dest = self.root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return rel_path

    def build_asset_url(self, stored_path: str) -> str:
        """Build API asset URL from a stored relative path."""
        normalized = stored_path.lstrip("/")
        return f"/bucket/assets/{normalized}"

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
