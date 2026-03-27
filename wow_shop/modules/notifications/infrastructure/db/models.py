from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    JSON,
    Enum as SQLEnum,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import CreatedAtMixin, CreatedByMixin
from wow_shop.infrastructure.db.types import int_pk, str100, str255


class NotificationChannel(StrEnum):
    IN_APP = auto()
    DISCORD = auto()
    TELEGRAM = auto()
    EMAIL = auto()


class NotificationStatus(StrEnum):
    QUEUED = auto()
    SENT = auto()
    FAILED = auto()


class NotificationEndpoint(Base):
    __tablename__ = "notifications_notification_endpoints"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(
            NotificationChannel,
            name="notifications_endpoint_channel_enum",
        )
    )
    endpoint_value: Mapped[str255]
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemNotification(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "notifications_system_notifications"

    id: Mapped[int_pk]
    event_type: Mapped[str100]
    target_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    channel: Mapped[NotificationChannel] = mapped_column(
        SQLEnum(NotificationChannel, name="notifications_system_channel_enum")
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[NotificationStatus] = mapped_column(
        SQLEnum(NotificationStatus, name="notifications_system_status_enum"),
        default=NotificationStatus.QUEUED,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InAppNotification(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "notifications_in_app_notifications"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    title: Mapped[str255]
    body: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
