"""Pydantic schemas returned by dataset API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DatasetResponse(BaseModel):
    """Public metadata describing one uploaded dataset."""

    id: int
    filename: str
    file_size: int
    file_type: str
    row_count: int | None
    column_count: int | None
    is_cleaned: bool
    created_at: datetime
    profile: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(BaseModel):
    """Collection of datasets and its total item count."""

    datasets: list[DatasetResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """Result returned after a dataset file is uploaded."""

    message: str
    dataset: DatasetResponse

    model_config = ConfigDict(from_attributes=True)
