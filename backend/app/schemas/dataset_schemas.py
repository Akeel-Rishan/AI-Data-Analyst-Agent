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


class ColumnProfile(BaseModel):
    """Structural, completeness, and distribution details for one column."""

    name: str
    dtype: str
    category: str
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    sample_values: list[Any]
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q25: float | None = None
    q75: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None
    has_negative: bool | None = None
    has_zeros: bool | None = None
    top_values: list[dict[str, Any]] | None = None
    is_high_cardinality: bool | None = None
    min_date: str | None = None
    max_date: str | None = None
    date_range_days: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DatasetProfile(BaseModel):
    """Complete cached inspection profile for a dataset."""

    basic_info: dict[str, Any]
    column_profiles: list[ColumnProfile]
    missing_analysis: list[dict[str, Any]]
    numeric_summary: dict[str, Any]
    datetime_columns: list[str]
    categorical_columns: list[str]
    numeric_columns: list[str]
    potential_issues: list[str]
    profiled_at: str

    model_config = ConfigDict(from_attributes=True)


class ProfileResponse(BaseModel):
    """Dataset identity paired with its generated inspection profile."""

    dataset_id: int
    filename: str
    profile: DatasetProfile

    model_config = ConfigDict(from_attributes=True)
