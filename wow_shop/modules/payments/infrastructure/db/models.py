from __future__ import annotations

from enum import Enum as PyEnum
from datetime import datetime

from sqlalchemy import (
    Enum,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base


class PaymentStatus(str, PyEnum):
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class RefundType(str, PyEnum):
    FULL = "full"
    PARTIAL = "partial"


class Payment(Base):
    __tablename__ = "payments_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payments_payment_status_enum"),
        default=PaymentStatus.CONFIRMED,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    confirmed_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Refund(Base):
    __tablename__ = "payments_refunds"
    __table_args__ = (
        CheckConstraint(
            "amount_eur IS NULL OR amount_eur >= 0", name="amount_eur_positive"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    type: Mapped[RefundType] = mapped_column(
        Enum(RefundType, name="payments_refund_type_enum")
    )
    amount_eur: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
