"""Validation and filesystem helpers for uploaded dataset files."""

from pathlib import Path
from uuid import uuid4

from app.utils.exceptions import FileValidationError


ALLOWED_EXTENSIONS = {
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",
}
BYTES_PER_MB = 1024 * 1024


def validate_file_extension(filename: str) -> str:
    """Validate a dataset filename and return its normalized file type."""
    extension = Path(filename).suffix.lower()
    file_type = ALLOWED_EXTENSIONS.get(extension)
    if file_type is None:
        displayed_extension = extension or "(none)"
        raise FileValidationError(
            "Only CSV and Excel files are allowed. "
            f"Got: {displayed_extension}"
        )
    return file_type


def validate_file_size(file_size: int, max_mb: int) -> None:
    """Raise an error when a file exceeds the configured size limit."""
    if file_size > max_mb * BYTES_PER_MB:
        raise FileValidationError(
            f"File size {get_file_size_mb(file_size)} MB exceeds maximum "
            f"allowed size of {max_mb} MB"
        )


def generate_unique_filename(original_filename: str) -> str:
    """Prefix a safe original filename with a UUID for unique storage."""
    safe_filename = original_filename.replace("\\", "/").rsplit("/", 1)[-1]
    return f"{uuid4().hex}__{safe_filename}"


def get_file_size_mb(size_bytes: int) -> float:
    """Convert a byte count to mebibytes rounded to two decimal places."""
    return round(size_bytes / BYTES_PER_MB, 2)


def ensure_upload_dir(upload_dir: str) -> Path:
    """Create and return the configured upload directory."""
    directory = Path(upload_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FileValidationError("Failed to create upload directory") from exc
    return directory
