from __future__ import annotations

from enum import Enum as PyEnum
from datetime import datetime

from sqlalchemy import Enum, Float, String, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from wow_shop.infrastructure.db.base import Base


class PromotionScope(str, PyEnum):
    CATEGORY = "category"
    LOT = "lot"


class PromotionType(str, PyEnum):
    DISCOUNT_PERCENT = "discount_percent"
    DISCOUNT_FIXED = "discount_fixed"
    TAG_ONLY = "tag_only"


class Promotion(Base):
    __tablename__ = "pricing_promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[PromotionScope] = mapped_column(
        Enum(PromotionScope, name="pricing_promotion_scope_type_enum")
    )
    scope_id: Mapped[int] = mapped_column(Integer)
    promo_type: Mapped[PromotionType] = mapped_column(
        Enum(PromotionType, name="pricing_promotion_promo_type_enum")
    )
    value: Mapped[float | None] = mapped_column(Float)
    tag: Mapped[str | None] = mapped_column(String(50))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
