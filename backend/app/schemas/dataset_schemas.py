"""Pydantic schemas returned by dataset API endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.cleaner_service import CleaningOperation


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


class CleaningConfigRequest(BaseModel):
    """User-selected cleaning operations and preview configuration."""

    operations: list[str]
    null_threshold_pct: float = Field(default=70.0, ge=0, le=100)
    dry_run: bool = False

    model_config = ConfigDict(from_attributes=True)

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, operations: list[str]) -> list[str]:
        """Reject operation names that the cleaner does not support."""
        valid_options = [operation.value for operation in CleaningOperation]
        invalid = [item for item in operations if item not in valid_options]
        if invalid:
            raise ValueError(
                f"Invalid cleaning operation(s): {', '.join(invalid)}. "
                f"Valid options: {', '.join(valid_options)}"
            )
        return operations


class CleaningChangeResponse(BaseModel):
    """Public report for one attempted cleaning operation."""

    operation: str
    description: str
    affected_columns: list[str]
    rows_affected: int
    columns_affected: int

    model_config = ConfigDict(from_attributes=True)


class CleaningResultResponse(BaseModel):
    """Shape changes and detailed results from a cleaning request."""

    dry_run: bool
    original_shape: dict[str, int]
    cleaned_shape: dict[str, int]
    rows_removed: int
    columns_removed: int
    changes: list[CleaningChangeResponse]
    summary: str

    model_config = ConfigDict(from_attributes=True)


class CleaningSuggestionsResponse(BaseModel):
    """Profile-derived cleaning recommendations and rough impact counts."""

    suggested_operations: list[str]
    reasons: dict[str, str]
    estimated_changes: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
