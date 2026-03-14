from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base


class OrderStatus(str, PyEnum):
    CREATED = "created"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    NEEDS_ADMIN_REVIEW = "needs_admin_review"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REQUIREMENTS_PENDING = "requirements_pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED = "closed"
    CANCELED = "canceled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class ExecutionMode(str, PyEnum):
    SELF_PLAY = "self_play"
    PILOTED = "piloted"
    ANYDESK = "anydesk"


class ClaimStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class GuestContact(Base):
    __tablename__ = "orders_guest_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Order(Base):
    __tablename__ = "orders_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_number: Mapped[str] = mapped_column(String(32), unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="orders_order_status_enum")
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        Enum(ExecutionMode, name="orders_order_execution_mode_enum")
    )

    customer_user_id: Mapped[int | None] = mapped_column(ForeignKey("auth_users.id"))
    guest_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders_guest_contacts.id")
    )
    booster_user_id: Mapped[int | None] = mapped_column(ForeignKey("auth_users.id"))
    service_lot_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_service_lots.id")
    )

    selected_options_json: Mapped[dict | None] = mapped_column(JSON)
    price_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    internal_note: Mapped[str | None] = mapped_column(Text)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("auth_users.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    in_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class MagicLink(Base):
    __tablename__ = "orders_magic_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders_orders.id"),
        unique=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(String(50), default="read_only")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OrderClaim(Base):
    __tablename__ = "orders_order_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"), index=True)
    booster_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="orders_order_claim_status_enum"),
        default=ClaimStatus.PENDING,
    )
    decided_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("auth_users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Checkpoint(Base):
    __tablename__ = "orders_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    message: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
