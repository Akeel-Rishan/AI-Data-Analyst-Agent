"""Business logic for dataset ownership and persistence."""

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, User
from app.utils.exceptions import DatasetNotFoundError
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


dataset_service = DatasetService()
