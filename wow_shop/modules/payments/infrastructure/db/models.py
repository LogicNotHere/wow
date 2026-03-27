from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    Enum as SQLEnum,
    Text,
    Float,
    DateTime,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import CreatedAtMixin, CreatedByMixin
from wow_shop.infrastructure.db.types import int_pk


class PaymentStatus(StrEnum):
    CONFIRMED = auto()
    CANCELED = auto()


class RefundType(StrEnum):
    FULL = auto()
    PARTIAL = auto()


class Payment(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "payments_payments"

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payments_payment_status_enum"),
        default=PaymentStatus.CONFIRMED,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    confirmed_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )


class Refund(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "payments_refunds"
    __table_args__ = (
        CheckConstraint(
            "amount_eur IS NULL OR amount_eur >= 0", name="amount_eur_positive"
        ),
    )

    id: Mapped[int_pk]
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    type: Mapped[RefundType] = mapped_column(
        SQLEnum(RefundType, name="payments_refund_type_enum")
    )
    amount_eur: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id")
    )
