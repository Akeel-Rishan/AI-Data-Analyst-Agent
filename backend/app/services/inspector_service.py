"""Comprehensive structural and quality profiling for uploaded datasets."""

from datetime import date, datetime, timezone
import math
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.utils.exceptions import AnalysisError, FileValidationError
from app.utils.file_utils import get_file_size_mb
from app.utils.logger import get_logger


logger = get_logger(__name__)


class InspectorService:
    """Load CSV or Excel datasets and generate JSON-safe profiles."""

    async def inspect_dataset(
        self,
        file_path: str,
        file_type: str,
    ) -> dict[str, Any]:
        """Load and comprehensively profile a stored dataset file."""
        started_at = perf_counter()
        logger.info("Starting dataset profiling for %s", file_path)
        try:
            dataframe = self._load_file(file_path, file_type)
            basic_info = self._get_basic_info(dataframe, file_path)
            column_profiles = self._get_column_profiles(dataframe)
            missing_analysis = self._get_missing_analysis(dataframe)
            numeric_summary = self._get_numeric_summary(dataframe)
            issues = self._detect_potential_issues(dataframe, column_profiles)
            profile = self._build_full_profile(
                dataframe,
                file_path,
                file_type,
                basic_info,
                column_profiles,
                missing_analysis,
                numeric_summary,
                issues,
            )
            safe_profile = self._make_json_safe(profile)
            elapsed_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "Completed dataset profiling for %s in %.2fms",
                file_path,
                elapsed_ms,
            )
            return safe_profile
        except Exception as exc:
            logger.exception("Dataset profiling failed for %s", file_path)
            raise AnalysisError(str(exc)) from exc

    def _load_file(self, file_path: str, file_type: str) -> pd.DataFrame:
        """Load a CSV or Excel file into a new DataFrame."""
        try:
            if file_type == "csv":
                try:
                    return pd.read_csv(file_path)
                except UnicodeDecodeError:
                    return pd.read_csv(file_path, encoding="latin-1")
            if file_type == "excel":
                return pd.read_excel(file_path)
            raise FileValidationError(
                f"Unsupported dataset file type: {file_type}"
            )
        except FileValidationError:
            raise
        except Exception as exc:
            raise FileValidationError(
                f"Failed to parse dataset file: {exc}"
            ) from exc

    def _get_basic_info(
        self,
        df: pd.DataFrame,
        file_path: str,
    ) -> dict[str, Any]:
        """Summarize dataset size, memory usage, duplicates, and missingness."""
        row_count, column_count = df.shape
        duplicate_count = int(df.duplicated().sum())
        total_missing = int(df.isna().sum().sum())
        total_cells = row_count * column_count
        missing_percentage = (
            round((total_missing / total_cells) * 100, 2)
            if total_cells
            else 0.0
        )
        file_size_bytes = Path(file_path).stat().st_size
        memory_usage_mb = round(
            float(df.memory_usage(deep=True).sum()) / (1024**2),
            2,
        )
        return {
            "row_count": int(row_count),
            "column_count": int(column_count),
            "file_size_bytes": int(file_size_bytes),
            "file_size_mb": get_file_size_mb(file_size_bytes),
            "memory_usage_mb": memory_usage_mb,
            "has_duplicates": duplicate_count > 0,
            "duplicate_count": duplicate_count,
            "has_missing": total_missing > 0,
            "total_missing": total_missing,
            "missing_percentage": missing_percentage,
        }

    def _get_column_profiles(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Generate type, completeness, sample, and distribution details."""
        profiles: list[dict[str, Any]] = []
        row_count = len(df)
        distinct_rows = df.drop_duplicates()

        for column in df.columns:
            series = df[column].copy()
            non_null = series.dropna()
            null_count = int(series.isna().sum())
            unique_count = int(series.nunique(dropna=True))
            category = self._detect_category(series)
            profile: dict[str, Any] = {
                "name": str(column),
                "dtype": str(series.dtype),
                "category": category,
                "null_count": null_count,
                "null_percentage": self._percentage(null_count, row_count),
                "unique_count": unique_count,
                "unique_percentage": self._percentage(unique_count, row_count),
                "sample_values": [str(value) for value in non_null.head(5)],
            }

            if category == "numeric":
                profile.update(self._get_numeric_column_stats(series))
            elif category == "categorical":
                distribution = distinct_rows[column].dropna().value_counts().head(10)
                profile["top_values"] = [
                    {
                        "value": str(value),
                        "count": int(count),
                        "percentage": self._percentage(int(count), row_count),
                    }
                    for value, count in distribution.items()
                ]
                profile["is_high_cardinality"] = unique_count > 50
            elif category == "datetime":
                profile.update(self._get_datetime_column_stats(series))

            profiles.append(profile)
        return profiles

    def _get_missing_analysis(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Describe incomplete columns and suggest an appropriate response."""
        analysis: list[dict[str, Any]] = []
        row_count = len(df)
        for column in df.columns:
            series = df[column].copy()
            missing_count = int(series.isna().sum())
            if missing_count == 0:
                continue

            missing_percentage = self._percentage(missing_count, row_count)
            category = self._detect_category(series)
            if missing_percentage > 70:
                action = "Consider dropping this column"
            elif missing_percentage > 30:
                action = "Consider imputation or dropping"
            elif category == "numeric":
                action = "Impute with mean or median"
            elif category == "categorical":
                action = "Impute with mode or 'Unknown'"
            else:
                action = "Review and handle manually"

            analysis.append(
                {
                    "column": str(column),
                    "missing_count": missing_count,
                    "missing_percentage": missing_percentage,
                    "suggested_action": action,
                }
            )
        return analysis

    def _get_numeric_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """Calculate correlation data for a manageable number of numerics."""
        numeric_columns = [
            str(column)
            for column in df.columns
            if self._detect_category(df[column]) == "numeric"
        ]
        correlation_matrix: dict[str, Any] = {}
        high_correlations: list[dict[str, Any]] = []

        if numeric_columns and len(numeric_columns) <= 20 and not df.empty:
            try:
                correlations = df[numeric_columns].corr().round(3)
                correlation_matrix = correlations.to_dict()
                for index, col1 in enumerate(numeric_columns):
                    for col2 in numeric_columns[index + 1 :]:
                        correlation = self._safe_float(
                            correlations.loc[col1, col2]
                        )
                        if correlation is not None and abs(correlation) > 0.7:
                            high_correlations.append(
                                {
                                    "col1": col1,
                                    "col2": col2,
                                    "correlation": correlation,
                                }
                            )
            except Exception:
                logger.exception("Failed to calculate numeric correlations")
                correlation_matrix = {}
                high_correlations = []

        return {
            "numeric_columns": numeric_columns,
            "correlation_matrix": self._make_json_safe(correlation_matrix),
            "high_correlations": high_correlations,
        }

    def _get_datetime_columns(self, df: pd.DataFrame) -> list[str]:
        """Return columns stored as or safely parseable as datetimes."""
        return [
            str(column)
            for column in df.columns
            if self._detect_category(df[column]) == "datetime"
        ]

    def _detect_potential_issues(
        self,
        df: pd.DataFrame,
        column_profiles: list[dict[str, Any]],
    ) -> list[str]:
        """Identify common data-quality and analysis-readiness warnings."""
        issues: list[str] = []
        row_count = len(df)

        for profile in column_profiles:
            name = profile["name"]
            if profile["null_percentage"] > 50:
                issues.append(f"Column '{name}' has over 50% missing values")
            if row_count > 0 and profile["unique_count"] == row_count:
                issues.append(
                    f"Column '{name}' appears to be an identifier column "
                    "(all values unique)"
                )
            if profile["category"] == "numeric" and profile.get("std") == 0:
                issues.append(
                    f"Column '{name}' has zero variance (constant values)"
                )

        duplicate_count = int(df.duplicated().sum())
        if duplicate_count:
            issues.append(f"Dataset contains {duplicate_count} duplicate rows")

        if column_profiles and all(
            profile["category"] == "numeric" for profile in column_profiles
        ):
            issues.append(
                "No categorical columns detected — dataset may be purely numerical"
            )
        if row_count < 10:
            issues.append(
                f"Dataset is very small ({row_count} rows) — analysis may be limited"
            )
        return issues

    def _build_full_profile(
        self,
        df: pd.DataFrame,
        file_path: str,
        file_type: str,
        basic_info: dict[str, Any],
        column_profiles: list[dict[str, Any]],
        missing_analysis: list[dict[str, Any]],
        numeric_summary: dict[str, Any],
        issues: list[str],
    ) -> dict[str, Any]:
        """Assemble the individual inspection results into one profile."""
        _ = (file_path, file_type)
        return {
            "basic_info": basic_info,
            "column_profiles": column_profiles,
            "missing_analysis": missing_analysis,
            "numeric_summary": numeric_summary,
            "datetime_columns": self._get_datetime_columns(df),
            "categorical_columns": [
                profile["name"]
                for profile in column_profiles
                if profile["category"] == "categorical"
            ],
            "numeric_columns": [
                profile["name"]
                for profile in column_profiles
                if profile["category"] == "numeric"
            ],
            "potential_issues": issues,
            "profiled_at": datetime.now(timezone.utc).isoformat(),
        }

    def _detect_category(self, series: pd.Series) -> str:
        """Classify a column using its dtype and safe datetime inference."""
        dtype = series.dtype
        if pd.api.types.is_bool_dtype(dtype):
            return "boolean"
        if pd.api.types.is_numeric_dtype(dtype):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "datetime"
        if pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(
            dtype
        ):
            non_null = series.dropna().copy()
            if not non_null.empty:
                try:
                    pd.to_datetime(non_null, errors="raise", format="mixed")
                    return "datetime"
                except (TypeError, ValueError, OverflowError):
                    pass
            return "categorical"
        return "unknown"

    def _get_numeric_column_stats(
        self,
        series: pd.Series,
    ) -> dict[str, Any]:
        """Calculate JSON-safe descriptive statistics for a numeric column."""
        values = series.dropna().copy()
        return {
            "min": self._numeric_stat(values, lambda item: item.min()),
            "max": self._numeric_stat(values, lambda item: item.max()),
            "mean": self._numeric_stat(values, lambda item: item.mean()),
            "median": self._numeric_stat(values, lambda item: item.median()),
            "std": self._numeric_stat(values, lambda item: item.std()),
            "q25": self._numeric_stat(values, lambda item: item.quantile(0.25)),
            "q75": self._numeric_stat(values, lambda item: item.quantile(0.75)),
            "skewness": self._numeric_stat(values, lambda item: item.skew()),
            "kurtosis": self._numeric_stat(values, lambda item: item.kurt()),
            "has_negative": bool((values < 0).any()) if not values.empty else False,
            "has_zeros": bool((values == 0).any()) if not values.empty else False,
        }

    def _get_datetime_column_stats(
        self,
        series: pd.Series,
    ) -> dict[str, Any]:
        """Calculate the observed bounds and range for a datetime column."""
        try:
            values = pd.to_datetime(
                series.dropna().copy(),
                errors="raise",
                format="mixed",
            )
            if values.empty:
                return {
                    "min_date": None,
                    "max_date": None,
                    "date_range_days": 0,
                }
            minimum = values.min()
            maximum = values.max()
            return {
                "min_date": minimum.isoformat(),
                "max_date": maximum.isoformat(),
                "date_range_days": int((maximum - minimum).days),
            }
        except Exception:
            logger.exception("Failed to calculate datetime column statistics")
            return {
                "min_date": None,
                "max_date": None,
                "date_range_days": 0,
            }

    def _numeric_stat(
        self,
        values: pd.Series,
        operation: Callable[[pd.Series], Any],
    ) -> float | None:
        """Execute one numeric calculation with a safe null fallback."""
        if values.empty:
            return None
        try:
            return self._safe_float(operation(values))
        except Exception:
            logger.exception("Failed to calculate numeric column statistic")
            return None

    def _safe_float(self, value: Any) -> float | None:
        """Convert a numeric scalar to a finite native float."""
        try:
            converted = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return converted if math.isfinite(converted) else None

    def _percentage(self, count: int, total: int) -> float:
        """Return a percentage rounded to two decimal places."""
        return round((count / total) * 100, 2) if total else 0.0

    def _make_json_safe(self, value: Any) -> Any:
        """Recursively convert Pandas and NumPy values to JSON-safe objects."""
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, (float, np.floating)):
            return self._safe_float(value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (pd.Timestamp, datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {
                str(key): self._make_json_safe(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set, np.ndarray)):
            return [self._make_json_safe(item) for item in value]
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        return str(value)
