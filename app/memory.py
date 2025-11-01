"""Persistent chat memory implementation backed by SQLAlchemy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from sqlalchemy import DateTime, Integer, String, Text, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base, session_scope


class ChatMessage(Base):
    """ORM model representing a single chat message."""

    __tablename__ = "memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class SQLiteMemory:
    """Thread-safe chat memory backed by SQLAlchemy sessions."""

    def save(self, role: str, content: str) -> None:
        with session_scope() as session:
            session.add(ChatMessage(role=role, content=content))

    def load(self, limit: int = 20) -> List[Tuple[str, str]]:
        with session_scope() as session:
            return [(message.role, message.content) for message in self._latest_messages(session, limit)]

    def reset(self) -> None:
        with session_scope() as session:
            session.execute(delete(ChatMessage))

    @staticmethod
    def _latest_messages(session: Session, limit: int) -> Iterable[ChatMessage]:
        stmt = select(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit)
        return session.scalars(stmt)

