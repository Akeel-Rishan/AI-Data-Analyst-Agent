"""Conversation and message database models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult
    from app.models.dataset import Dataset
    from app.models.user import User


class Conversation(TimestampMixin, Base):
    """Represent a user's conversation about one dataset."""

    __tablename__ = "conversations"

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
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="conversations")
    dataset: Mapped[Dataset] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    analysis_results: Mapped[list[AnalysisResult]] = relationship(
        back_populates="conversation",
    )

    def __repr__(self) -> str:
        """Return a concise developer representation of the conversation."""
        return f"<Conversation id={self.id!r} title={self.title!r}>"


class Message(Base):
    """Represent one user or assistant message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        nullable=False,
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_results.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    analysis_result: Mapped[AnalysisResult | None] = relationship(
        back_populates="messages",
    )

    def __repr__(self) -> str:
        """Return a concise developer representation of the message."""
        return f"<Message id={self.id!r} role={self.role!r}>"
