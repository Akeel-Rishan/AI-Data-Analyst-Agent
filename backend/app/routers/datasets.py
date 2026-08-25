"""Dataset upload, retrieval, listing, profile, and deletion routes."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Header, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas import DatasetListResponse, DatasetResponse, UploadResponse
from app.services.dataset_service import dataset_service
from app.utils.exceptions import FileValidationError
from app.utils.file_utils import (
    ensure_upload_dir,
    generate_unique_filename,
    get_file_size_mb,
    validate_file_extension,
    validate_file_size,
)
from app.utils.logger import get_logger
from app.utils.responses import success_response


router = APIRouter(prefix="/api/datasets", tags=["datasets"])
logger = get_logger(__name__)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: Annotated[UploadFile, File(...)],
    session_id: Annotated[str, Header(alias="X-Session-ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Validate, store, and register a dataset uploaded by a session."""
    original_filename = file.filename or ""
    stored_path: Path | None = None

    try:
        file_type = validate_file_extension(original_filename)
        contents = await file.read()
        file_size = len(contents)
        validate_file_size(file_size, settings.MAX_FILE_SIZE_MB)

        unique_filename = generate_unique_filename(original_filename)
        upload_directory = ensure_upload_dir(settings.UPLOAD_DIR)
        stored_path = upload_directory / unique_filename
        try:
            stored_path.write_bytes(contents)
        except OSError as exc:
            logger.exception("Failed to write uploaded file %s", stored_path)
            raise FileValidationError("Failed to save file to disk") from exc

        try:
            user = await dataset_service.get_or_create_user(db, session_id)
            dataset = await dataset_service.save_dataset_record(
                db=db,
                user_id=user.id,
                filename=original_filename,
                file_path=str(stored_path),
                file_size=file_size,
                file_type=file_type,
            )
        except Exception:
            if stored_path.exists():
                stored_path.unlink(missing_ok=True)
            logger.exception(
                "Failed to register uploaded dataset %s",
                original_filename,
            )
            raise

        logger.info(
            "Uploaded %s (%.2f MB) for session %s",
            original_filename,
            get_file_size_mb(file_size),
            session_id,
        )
        upload_response = UploadResponse(
            message="File uploaded successfully",
            dataset=DatasetResponse.model_validate(dataset),
        )
        return success_response(
            upload_response,
            "File uploaded successfully",
            status.HTTP_201_CREATED,
        )
    except FileValidationError:
        logger.warning(
            "Rejected upload %s for session %s",
            original_filename,
            session_id,
        )
        raise


@router.get("")
async def list_datasets(
    session_id: Annotated[str, Header(alias="X-Session-ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """List all datasets owned by the requesting browser session."""
    user = await dataset_service.get_or_create_user(db, session_id)
    datasets = await dataset_service.list_user_datasets(db, user.id)
    response = DatasetListResponse(
        datasets=[DatasetResponse.model_validate(item) for item in datasets],
        total=len(datasets),
    )
    return success_response(response)


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Return one dataset after enforcing session ownership."""
    user = await dataset_service.get_or_create_user(db, session_id)
    dataset = await dataset_service.get_dataset_by_id(db, dataset_id, user.id)
    return success_response(DatasetResponse.model_validate(dataset))


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: int,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Delete an owned dataset and its file from persistent storage."""
    user = await dataset_service.get_or_create_user(db, session_id)
    await dataset_service.delete_dataset(db, dataset_id, user.id)
    return success_response({"deleted": True, "dataset_id": dataset_id})


@router.get("/{dataset_id}/profile")
async def get_dataset_profile(
    dataset_id: int,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Return an owned dataset's profile or its not-yet-profiled state."""
    user = await dataset_service.get_or_create_user(db, session_id)
    dataset = await dataset_service.get_dataset_by_id(db, dataset_id, user.id)
    if dataset.profile is None:
        return success_response(
            {
                "profile": None,
                "message": (
                    "Dataset not yet profiled. Call the inspect endpoint."
                ),
            }
        )
    return success_response({"profile": dataset.profile})
