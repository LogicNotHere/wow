from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import Enum as SQLEnum, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.types import int_pk, str50


class PromotionScope(StrEnum):
    CATEGORY = auto()
    LOT = auto()


class PromotionType(StrEnum):
    DISCOUNT_PERCENT = auto()
    DISCOUNT_FIXED = auto()
    TAG_ONLY = auto()


class Promotion(Base):
    __tablename__ = "pricing_promotions"

    id: Mapped[int_pk]
    scope_type: Mapped[PromotionScope] = mapped_column(
        SQLEnum(PromotionScope, name="pricing_promotion_scope_type_enum")
    )
    scope_id: Mapped[int]
    promo_type: Mapped[PromotionType] = mapped_column(
        SQLEnum(PromotionType, name="pricing_promotion_promo_type_enum")
    )
    value: Mapped[float | None] = mapped_column(Float)
    tag: Mapped[str50 | None]
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
