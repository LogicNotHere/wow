from __future__ import annotations

from enum import Enum as PyEnum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Enum,
    Text,
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base


class NotificationChannel(str, PyEnum):
    IN_APP = "in_app"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    EMAIL = "email"


class NotificationStatus(str, PyEnum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class NotificationEndpoint(Base):
    __tablename__ = "notifications_notification_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notifications_endpoint_channel_enum")
    )
    endpoint_value: Mapped[str] = mapped_column(String(255))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemNotification(Base):
    __tablename__ = "notifications_system_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100))
    target_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notifications_system_channel_enum")
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notifications_system_status_enum"),
        default=NotificationStatus.QUEUED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InAppNotification(Base):
    __tablename__ = "notifications_in_app_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
