"""Analysis result database model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation, Message
    from app.models.dataset import Dataset


class AnalysisResult(Base):
    """Store the plan, execution output, and explanation for an analysis."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=True,
        index=True,
    )
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_plan: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    code_executed: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_results: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    charts: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_success: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    dataset: Mapped[Dataset] = relationship(back_populates="analysis_results")
    conversation: Mapped[Conversation | None] = relationship(
        back_populates="analysis_results",
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="analysis_result",
    )

    def __repr__(self) -> str:
        """Return a concise developer representation of the analysis result."""
        return (
            "<AnalysisResult "
            f"id={self.id!r} success={self.execution_success!r}>"
        )
