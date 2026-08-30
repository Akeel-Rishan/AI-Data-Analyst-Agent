"""Business logic for dataset ownership and persistence."""

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, User
from app.services.cleaner_service import (
    CleanerService,
    CleaningConfig,
    CleaningOperation,
)
from app.services.inspector_service import InspectorService
from app.utils.exceptions import AnalysisError, DatasetNotFoundError
from app.utils.logger import get_logger


logger = get_logger(__name__)


class DatasetService:
    """Coordinate dataset and anonymous-user database operations."""

    async def get_or_create_user(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> User:
        """Return the session owner, creating it when first encountered."""
        result = await db.execute(
            select(User).where(User.session_id == session_id)
        )
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(session_id=session_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created user for session %s", session_id)
        return user

    async def save_dataset_record(
        self,
        db: AsyncSession,
        user_id: int,
        filename: str,
        file_path: str,
        file_size: int,
        file_type: str,
    ) -> Dataset:
        """Persist metadata for a newly stored dataset file."""
        dataset = Dataset(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file_type,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)
        logger.info("Saved dataset %s for user %s", dataset.id, user_id)
        return dataset

    async def get_dataset_by_id(
        self,
        db: AsyncSession,
        dataset_id: int,
        user_id: int,
    ) -> Dataset:
        """Fetch a dataset only when it belongs to the specified user."""
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.user_id == user_id,
            )
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            logger.warning(
                "Dataset %s not found for user %s",
                dataset_id,
                user_id,
            )
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        return dataset

    async def list_user_datasets(
        self,
        db: AsyncSession,
        user_id: int,
    ) -> list[Dataset]:
        """List a user's datasets from newest to oldest."""
        result = await db.execute(
            select(Dataset)
            .where(Dataset.user_id == user_id)
            .order_by(Dataset.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_dataset(
        self,
        db: AsyncSession,
        dataset_id: int,
        user_id: int,
    ) -> bool:
        """Delete an owned dataset record and its stored file."""
        dataset = await self.get_dataset_by_id(db, dataset_id, user_id)
        stored_file = Path(dataset.file_path)
        if stored_file.exists():
            try:
                stored_file.unlink()
            except OSError:
                logger.exception("Failed to delete dataset file %s", stored_file)
                raise

        await db.delete(dataset)
        await db.commit()
        logger.info("Deleted dataset %s for user %s", dataset_id, user_id)
        return True

    async def update_dataset_profile(
        self,
        db: AsyncSession,
        dataset_id: int,
        profile: dict[str, Any],
        row_count: int,
        column_count: int,
    ) -> Dataset:
        """Store inspection results for a dataset."""
        result = await db.execute(
            select(Dataset).where(Dataset.id == dataset_id)
        )
        dataset = result.scalar_one_or_none()
        if dataset is None:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")

        dataset.profile = profile
        dataset.row_count = row_count
        dataset.column_count = column_count
        await db.commit()
        await db.refresh(dataset)
        logger.info("Updated profile for dataset %s", dataset_id)
        return dataset

    async def inspect_and_profile(
        self,
        db: AsyncSession,
        dataset_id: int,
        user_id: int,
    ) -> Dataset:
        """Inspect an owned dataset and persist its generated profile."""
        dataset = await self.get_dataset_by_id(db, dataset_id, user_id)
        inspector = InspectorService()
        profile = await inspector.inspect_dataset(
            dataset.file_path,
            dataset.file_type or "",
        )
        basic_info = profile["basic_info"]
        return await self.update_dataset_profile(
            db=db,
            dataset_id=dataset.id,
            profile=profile,
            row_count=int(basic_info["row_count"]),
            column_count=int(basic_info["column_count"]),
        )

    async def apply_cleaning(
        self,
        db: AsyncSession,
        dataset_id: int,
        user_id: int,
        config: CleaningConfig,
    ) -> dict[str, Any]:
        """Clean an owned dataset and refresh its cached profile when applied."""
        dataset = await self.get_dataset_by_id(db, dataset_id, user_id)
        cleaner = CleanerService()
        result = await cleaner.clean_dataset(
            dataset.file_path,
            dataset.file_type or "",
            config,
        )

        if not config.dry_run:
            inspector = InspectorService()
            profile = await inspector.inspect_dataset(
                dataset.file_path,
                dataset.file_type or "",
            )
            basic_info = profile["basic_info"]
            dataset.profile = profile
            dataset.row_count = int(basic_info["row_count"])
            dataset.column_count = int(basic_info["column_count"])
            dataset.file_size = Path(dataset.file_path).stat().st_size
            dataset.is_cleaned = True
            await db.commit()
            await db.refresh(dataset)
            logger.info("Refreshed profile after cleaning dataset %s", dataset_id)

        return result

    async def get_cleaning_suggestions(
        self,
        db: AsyncSession,
        dataset_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Recommend cleaning operations using an owned dataset's profile."""
        dataset = await self.get_dataset_by_id(db, dataset_id, user_id)
        if dataset.profile is None:
            raise AnalysisError(
                "Dataset must be inspected before getting cleaning suggestions"
            )

        profile = dataset.profile
        basic_info = profile["basic_info"]
        columns = profile["column_profiles"]
        issues = profile["potential_issues"]
        suggested: list[str] = []
        reasons: dict[str, str] = {}

        def add_suggestion(operation: CleaningOperation, reason: str) -> None:
            """Add a recommendation once while retaining its explanation."""
            if operation.value not in suggested:
                suggested.append(operation.value)
                reasons[operation.value] = reason

        if basic_info.get("has_duplicates"):
            add_suggestion(
                CleaningOperation.REMOVE_DUPLICATES,
                f"Dataset contains {basic_info.get('duplicate_count', 0)} "
                "duplicate rows",
            )
        high_null_columns = [
            item["name"]
            for item in columns
            if float(item.get("null_percentage", 0)) > 70
        ]
        if high_null_columns:
            add_suggestion(
                CleaningOperation.DROP_HIGH_NULL_COLUMNS,
                "Some columns contain more than 70% missing values",
            )
        numeric_missing = [
            item
            for item in columns
            if item.get("category") == "numeric" and item.get("null_count", 0)
        ]
        if numeric_missing:
            add_suggestion(
                CleaningOperation.IMPUTE_NUMERIC_MEDIAN,
                "Numeric columns contain missing values",
            )
        categorical_missing = [
            item
            for item in columns
            if item.get("category") == "categorical"
            and item.get("null_count", 0)
        ]
        if categorical_missing:
            add_suggestion(
                CleaningOperation.IMPUTE_CATEGORICAL_MODE,
                "Categorical columns contain missing values",
            )
        constant_warnings = [
            issue for issue in issues if "zero variance (constant values)" in issue
        ]
        if constant_warnings:
            add_suggestion(
                CleaningOperation.REMOVE_CONSTANT_COLUMNS,
                "The profile detected constant columns",
            )

        add_suggestion(
            CleaningOperation.STRIP_WHITESPACE,
            "Normalize leading and trailing whitespace in text values",
        )
        add_suggestion(
            CleaningOperation.STANDARDIZE_COLUMN_NAMES,
            "Normalize column names for reliable analysis",
        )

        return {
            "suggested_operations": suggested,
            "reasons": reasons,
            "estimated_changes": {
                "duplicate_rows": int(basic_info.get("duplicate_count", 0)),
                "high_null_columns": len(high_null_columns),
                "numeric_missing_values": sum(
                    int(item.get("null_count", 0)) for item in numeric_missing
                ),
                "categorical_missing_values": sum(
                    int(item.get("null_count", 0))
                    for item in categorical_missing
                ),
                "constant_columns": len(constant_warnings),
            },
        }


dataset_service = DatasetService()
