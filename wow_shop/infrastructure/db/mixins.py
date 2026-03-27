from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column


def _get_current_auth_user_id() -> int | None:
    from wow_shop.shared.auth.context import get_auth_user_id

    return get_auth_user_id()


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreatedByMixin:
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id"),
        nullable=True,
        default=_get_current_auth_user_id,
    )


class UpdatedByMixin:
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id"),
        nullable=True,
        default=_get_current_auth_user_id,
        onupdate=_get_current_auth_user_id,
    )


class CreateUpdateMixin(
    CreatedAtMixin, CreatedByMixin, UpdatedAtMixin, UpdatedByMixin
):
    pass
