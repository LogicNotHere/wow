from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    JSON,
    Enum as SQLEnum,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import (
    CreateUpdateMixin,
    CreatedAtMixin,
    CreatedByMixin,
)
from wow_shop.infrastructure.db.types import (
    int_pk,
    str32,
    str50,
    str255,
    str1024,
)


class OrderStatus(StrEnum):
    CREATED = auto()
    PAYMENT_PENDING = auto()
    PAID = auto()
    NEEDS_ADMIN_REVIEW = auto()
    ASSIGNED = auto()
    ACCEPTED = auto()
    REQUIREMENTS_PENDING = auto()
    IN_PROGRESS = auto()
    DONE = auto()
    CLOSED = auto()
    CANCELED = auto()
    DISPUTED = auto()
    REFUNDED = auto()
    PARTIAL_REFUND = auto()


class ExecutionMode(StrEnum):
    SELF_PLAY = auto()
    PILOTED = auto()
    ANYDESK = auto()


class ClaimStatus(StrEnum):
    PENDING = auto()
    APPROVED = auto()
    DECLINED = auto()


class GuestContact(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "orders_guest_contacts"

    id: Mapped[int_pk]
    channel: Mapped[str50]
    value: Mapped[str255]


class Order(CreateUpdateMixin, Base):
    __tablename__ = "orders_orders"

    id: Mapped[int_pk]
    public_number: Mapped[str32] = mapped_column(unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, name="orders_order_status_enum")
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        SQLEnum(ExecutionMode, name="orders_order_execution_mode_enum")
    )

    customer_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )
    guest_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders_guest_contacts.id")
    )
    booster_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )
    service_lot_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_service_lots.id")
    )

    selected_options_json: Mapped[dict | None] = mapped_column(JSON)
    price_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    internal_note: Mapped[str | None] = mapped_column(Text)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    in_progress_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MagicLink(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "orders_magic_links"

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders_orders.id"),
        unique=True,
    )
    token_hash: Mapped[str255]
    scope: Mapped[str50] = mapped_column(default="read_only")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderClaim(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "orders_order_claims"

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders_orders.id"), index=True
    )
    booster_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    status: Mapped[ClaimStatus] = mapped_column(
        SQLEnum(ClaimStatus, name="orders_order_claim_status_enum"),
        default=ClaimStatus.PENDING,
    )
    decided_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Checkpoint(CreatedAtMixin, Base):
    __tablename__ = "orders_checkpoints"

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    message: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str1024 | None]
