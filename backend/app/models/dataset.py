"""Uploaded dataset database model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult
    from app.models.conversation import Conversation
    from app.models.user import User


class Dataset(TimestampMixin, Base):
    """Represent an uploaded dataset and its generated profile."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_cleaned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="datasets")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    analysis_results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return a concise developer representation of the dataset."""
        return f"<Dataset id={self.id!r} filename={self.filename!r}>"
