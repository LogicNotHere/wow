from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import CreatedAtMixin, CreatedByMixin
from wow_shop.infrastructure.db.types import int_pk, str20, str1024


class ChatThread(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "chat_threads"

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders_orders.id"),
        unique=True,
    )


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("thread_id", "user_id"),)

    id: Mapped[int_pk]
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    role_in_thread: Mapped[str20]
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ChatMessage(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[int_pk]
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    author_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    body: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str1024 | None]
