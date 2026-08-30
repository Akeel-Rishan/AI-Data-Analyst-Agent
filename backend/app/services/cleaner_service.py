"""Configurable data-cleaning operations for CSV and Excel datasets."""

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from pathlib import Path
import re
from typing import Any

import pandas as pd

from app.utils.exceptions import AnalysisError, FileValidationError
from app.utils.logger import get_logger


logger = get_logger(__name__)


class CleaningOperation(str, Enum):
    """Operations supported by the dataset cleaner."""

    REMOVE_DUPLICATES = "remove_duplicates"
    DROP_HIGH_NULL_COLUMNS = "drop_high_null_columns"
    IMPUTE_NUMERIC_MEAN = "impute_numeric_mean"
    IMPUTE_NUMERIC_MEDIAN = "impute_numeric_median"
    IMPUTE_CATEGORICAL_MODE = "impute_categorical_mode"
    IMPUTE_CATEGORICAL_UNKNOWN = "impute_categorical_unknown"
    FIX_DATETIME_COLUMNS = "fix_datetime_columns"
    STRIP_WHITESPACE = "strip_whitespace"
    STANDARDIZE_COLUMN_NAMES = "standardize_column_names"
    REMOVE_CONSTANT_COLUMNS = "remove_constant_columns"


@dataclass
class CleaningConfig:
    """Ordered cleaning operations and their execution settings."""

    operations: list[CleaningOperation] = field(default_factory=list)
    null_threshold_pct: float = 70.0
    dry_run: bool = False


@dataclass
class CleaningChange:
    """One operation's effect on a dataset."""

    operation: str
    description: str
    affected_columns: list[str]
    rows_affected: int = 0
    columns_affected: int = 0


class CleanerService:
    """Apply ordered cleaning operations and report every attempted change."""

    async def clean_dataset(
        self,
        file_path: str,
        file_type: str,
        config: CleaningConfig,
    ) -> dict[str, Any]:
        """Clean a stored dataset or preview the same operations without saving."""
        logger.info(
            "Starting dataset cleaning for %s. Dry run: %s",
            file_path,
            config.dry_run,
        )
        try:
            source = self._load_file(file_path, file_type)
            cleaned = source.copy(deep=True)
            original_rows, original_columns = cleaned.shape
            changes: list[CleaningChange] = []

            for operation in config.operations:
                cleaned, change = self._apply_operation(
                    cleaned,
                    operation,
                    config.null_threshold_pct,
                )
                changes.append(change)
                logger.info(
                    "Applied cleaning operation %s: %s",
                    operation.value,
                    change.description,
                )

            cleaned_rows, cleaned_columns = cleaned.shape
            if not config.dry_run:
                self._save_file(cleaned, file_path, file_type)

            summary = self._build_summary(changes)
            logger.info("Dataset cleaning complete for %s: %s", file_path, summary)
            return {
                "dry_run": config.dry_run,
                "original_shape": {
                    "rows": int(original_rows),
                    "columns": int(original_columns),
                },
                "cleaned_shape": {
                    "rows": int(cleaned_rows),
                    "columns": int(cleaned_columns),
                },
                "rows_removed": int(original_rows - cleaned_rows),
                "columns_removed": int(original_columns - cleaned_columns),
                "changes": [asdict(change) for change in changes],
                "summary": summary,
            }
        except Exception as exc:
            logger.exception("Dataset cleaning failed for %s", file_path)
            if isinstance(exc, AnalysisError):
                raise
            raise AnalysisError(str(exc)) from exc

    def _apply_operation(
        self,
        df: pd.DataFrame,
        operation: CleaningOperation,
        null_threshold_pct: float,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Dispatch one configured operation to its implementation."""
        if operation == CleaningOperation.REMOVE_DUPLICATES:
            return self._remove_duplicates(df)
        if operation == CleaningOperation.DROP_HIGH_NULL_COLUMNS:
            return self._drop_high_null_columns(df, null_threshold_pct)
        if operation == CleaningOperation.IMPUTE_NUMERIC_MEAN:
            return self._impute_numeric_mean(df)
        if operation == CleaningOperation.IMPUTE_NUMERIC_MEDIAN:
            return self._impute_numeric_median(df)
        if operation == CleaningOperation.IMPUTE_CATEGORICAL_MODE:
            return self._impute_categorical_mode(df)
        if operation == CleaningOperation.IMPUTE_CATEGORICAL_UNKNOWN:
            return self._impute_categorical_unknown(df)
        if operation == CleaningOperation.FIX_DATETIME_COLUMNS:
            return self._fix_datetime_columns(df)
        if operation == CleaningOperation.STRIP_WHITESPACE:
            return self._strip_whitespace(df)
        if operation == CleaningOperation.STANDARDIZE_COLUMN_NAMES:
            return self._standardize_column_names(df)
        if operation == CleaningOperation.REMOVE_CONSTANT_COLUMNS:
            return self._remove_constant_columns(df)
        raise AnalysisError(f"Unsupported cleaning operation: {operation}")

    def _remove_duplicates(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Remove exact duplicate rows."""
        working = df.copy(deep=True)
        duplicate_count = int(working.duplicated().sum())
        if duplicate_count:
            working = working.drop_duplicates().copy()
            description = f"Removed {duplicate_count} duplicate rows"
        else:
            description = "No changes needed"
        return working, CleaningChange(
            operation=CleaningOperation.REMOVE_DUPLICATES.value,
            description=description,
            affected_columns=[],
            rows_affected=duplicate_count,
        )

    def _drop_high_null_columns(
        self,
        df: pd.DataFrame,
        threshold: float,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Drop columns whose missing percentage exceeds the threshold."""
        working = df.copy(deep=True)
        if len(working):
            null_percentages = working.isna().mean() * 100
            columns = [
                str(column)
                for column in working.columns
                if float(null_percentages[column]) > threshold
            ]
        else:
            columns = []
        if columns:
            working = working.drop(columns=columns).copy()
            description = (
                f"Dropped {len(columns)} columns above {threshold}% missing values"
            )
        else:
            description = "No changes needed"
        return working, CleaningChange(
            operation=CleaningOperation.DROP_HIGH_NULL_COLUMNS.value,
            description=description,
            affected_columns=columns,
            columns_affected=len(columns),
        )

    def _impute_numeric_mean(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Fill missing numeric values with rounded column means."""
        return self._impute_numeric(
            df,
            CleaningOperation.IMPUTE_NUMERIC_MEAN,
            "mean",
        )

    def _impute_numeric_median(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Fill missing numeric values with rounded column medians."""
        return self._impute_numeric(
            df,
            CleaningOperation.IMPUTE_NUMERIC_MEDIAN,
            "median",
        )

    def _impute_numeric(
        self,
        df: pd.DataFrame,
        operation: CleaningOperation,
        strategy: str,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Apply one aggregate-based numeric imputation strategy."""
        working = df.copy(deep=True)
        affected_columns: list[str] = []
        values_imputed = 0
        for column in working.columns:
            series = working[column]
            if not pd.api.types.is_numeric_dtype(series.dtype):
                continue
            missing_count = int(series.isna().sum())
            if not missing_count:
                continue
            try:
                aggregate = series.mean() if strategy == "mean" else series.median()
                fill_value = float(aggregate)
                if not math.isfinite(fill_value):
                    continue
                working[column] = series.fillna(round(fill_value, 2))
                affected_columns.append(str(column))
                values_imputed += missing_count
            except Exception:
                logger.exception(
                    "Unable to impute numeric column %s using %s",
                    column,
                    strategy,
                )

        description = (
            f"Imputed {values_imputed} missing values in "
            f"{len(affected_columns)} numeric columns using {strategy}"
            if values_imputed
            else "No changes needed"
        )
        return working, CleaningChange(
            operation=operation.value,
            description=description,
            affected_columns=affected_columns,
            rows_affected=values_imputed,
            columns_affected=len(affected_columns),
        )

    def _impute_categorical_mode(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Fill missing non-numeric values with each column's mode."""
        working = df.copy(deep=True)
        affected_columns: list[str] = []
        values_imputed = 0
        for column in working.columns:
            series = working[column]
            if pd.api.types.is_numeric_dtype(series.dtype):
                continue
            missing_count = int(series.isna().sum())
            if not missing_count:
                continue
            try:
                modes = series.mode(dropna=True)
                if modes.empty:
                    continue
                working[column] = series.fillna(modes.iloc[0])
                affected_columns.append(str(column))
                values_imputed += missing_count
            except Exception:
                logger.exception("Unable to impute categorical column %s", column)

        description = (
            f"Imputed {values_imputed} missing values in "
            f"{len(affected_columns)} categorical columns using mode"
            if values_imputed
            else "No changes needed"
        )
        return working, CleaningChange(
            operation=CleaningOperation.IMPUTE_CATEGORICAL_MODE.value,
            description=description,
            affected_columns=affected_columns,
            rows_affected=values_imputed,
            columns_affected=len(affected_columns),
        )

    def _impute_categorical_unknown(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Fill missing object values with the literal ``Unknown``."""
        working = df.copy(deep=True)
        affected_columns: list[str] = []
        values_imputed = 0
        for column in working.columns:
            series = working[column]
            if not self._is_text_dtype(series):
                continue
            missing_count = int(series.isna().sum())
            if not missing_count:
                continue
            working[column] = series.fillna("Unknown")
            affected_columns.append(str(column))
            values_imputed += missing_count

        description = (
            f"Imputed {values_imputed} missing values in "
            f"{len(affected_columns)} categorical columns with 'Unknown'"
            if values_imputed
            else "No changes needed"
        )
        return working, CleaningChange(
            operation=CleaningOperation.IMPUTE_CATEGORICAL_UNKNOWN.value,
            description=description,
            affected_columns=affected_columns,
            rows_affected=values_imputed,
            columns_affected=len(affected_columns),
        )

    def _fix_datetime_columns(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Convert mostly parseable object columns to datetime values."""
        working = df.copy(deep=True)
        converted_columns: list[str] = []
        for column in working.columns:
            series = working[column]
            if not self._is_text_dtype(series) or series.empty:
                continue
            try:
                parsed = pd.to_datetime(series.copy(), errors="coerce", format="mixed")
                if float(parsed.isna().mean()) < 0.5:
                    working[column] = parsed
                    converted_columns.append(str(column))
            except Exception:
                logger.exception("Unable to parse datetime column %s", column)

        description = (
            f"Converted {len(converted_columns)} columns to datetime"
            if converted_columns
            else "No changes needed"
        )
        return working, CleaningChange(
            operation=CleaningOperation.FIX_DATETIME_COLUMNS.value,
            description=description,
            affected_columns=converted_columns,
            columns_affected=len(converted_columns),
        )

    def _strip_whitespace(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Remove leading and trailing whitespace from object values."""
        working = df.copy(deep=True)
        affected_columns: list[str] = []
        cells_changed = 0
        for column in working.columns:
            series = working[column]
            if not self._is_text_dtype(series):
                continue
            stripped = series.map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
            changed = series.ne(stripped) & ~(series.isna() & stripped.isna())
            changed_count = int(changed.fillna(False).sum())
            if changed_count:
                working[column] = stripped
                affected_columns.append(str(column))
                cells_changed += changed_count

        description = (
            f"Stripped whitespace from {cells_changed} values across "
            f"{len(affected_columns)} columns"
            if cells_changed
            else "No changes needed"
        )
        return working, CleaningChange(
            operation=CleaningOperation.STRIP_WHITESPACE.value,
            description=description,
            affected_columns=affected_columns,
            rows_affected=cells_changed,
            columns_affected=len(affected_columns),
        )

    def _standardize_column_names(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Normalize column names to lowercase alphanumeric snake case."""
        working = df.copy(deep=True)
        rename_mapping: dict[Any, str] = {}
        display_mapping: list[str] = []
        for column in working.columns:
            original = str(column)
            normalized = re.sub(r"[\s-]+", "_", original.strip().lower())
            normalized = re.sub(r"[^a-z0-9_]", "", normalized)
            if normalized != original:
                rename_mapping[column] = normalized
                display_mapping.append(f"{original} → {normalized}")

        if rename_mapping:
            working = working.rename(columns=rename_mapping).copy()
            description = "Renamed columns: " + ", ".join(display_mapping)
        else:
            description = "No changes needed"
        affected_columns = [str(column) for column in rename_mapping]
        return working, CleaningChange(
            operation=CleaningOperation.STANDARDIZE_COLUMN_NAMES.value,
            description=description,
            affected_columns=affected_columns,
            columns_affected=len(rename_mapping),
        )

    def _remove_constant_columns(
        self,
        df: pd.DataFrame,
    ) -> tuple[pd.DataFrame, CleaningChange]:
        """Drop columns containing at most one distinct non-null value."""
        working = df.copy(deep=True)
        columns = [
            str(column)
            for column in working.columns
            if int(working[column].nunique(dropna=True)) <= 1
        ]
        if columns:
            working = working.drop(columns=columns).copy()
            description = f"Removed {len(columns)} constant columns"
        else:
            description = "No changes needed"
        return working, CleaningChange(
            operation=CleaningOperation.REMOVE_CONSTANT_COLUMNS.value,
            description=description,
            affected_columns=columns,
            columns_affected=len(columns),
        )

    def _build_summary(self, changes: list[CleaningChange]) -> str:
        """Combine effective operation descriptions into a readable summary."""
        descriptions = [
            change.description.rstrip(".")
            for change in changes
            if change.rows_affected or change.columns_affected
        ]
        if not descriptions:
            return "No changes needed."
        return ". ".join(descriptions) + "."

    def _is_text_dtype(self, series: pd.Series) -> bool:
        """Return whether a series uses an object or native string dtype."""
        return pd.api.types.is_object_dtype(
            series.dtype
        ) or pd.api.types.is_string_dtype(series.dtype)

    def _load_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Load a stored CSV or Excel file without mutating its contents."""
        try:
            if file_type == "csv":
                try:
                    return pd.read_csv(file_path)
                except UnicodeDecodeError:
                    return pd.read_csv(file_path, encoding="latin-1")
            if file_type == "excel":
                return pd.read_excel(file_path)
            raise FileValidationError(f"Unsupported dataset file type: {file_type}")
        except FileValidationError:
            raise
        except Exception as exc:
            raise FileValidationError(
                f"Failed to parse dataset file: {exc}"
            ) from exc

    def _save_file(
        self,
        df: pd.DataFrame,
        file_path: str,
        file_type: str,
    ) -> None:
        """Overwrite a stored dataset while preserving its source format."""
        path = Path(file_path)
        if file_type == "csv":
            df.to_csv(path, index=False)
            return
        if file_type == "excel":
            df.to_excel(path, index=False)
            return
        raise FileValidationError(f"Unsupported dataset file type: {file_type}")
