from __future__ import annotations

from decimal import Decimal
from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    Numeric,
    Index,
    Enum as SQLEnum,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.types import int_pk


class PromotionDiscountType(StrEnum):
    PERCENT = auto()
    FIXED_AMOUNT = auto()


class PromotionBadgeTag(StrEnum):
    HOT = auto()
    SALE = auto()
    NEW = auto()
    HIT = auto()


class PromotionAudience(StrEnum):
    PUBLIC = auto()
    PERSONAL = auto()


class Promotion(Base):
    __tablename__ = "pricing_promotions"
    __table_args__ = (
        CheckConstraint(
            "(lot_id IS NOT NULL AND category_id IS NULL) OR "
            "(lot_id IS NULL AND category_id IS NOT NULL)",
            name="scope_target_xor",
        ),
        CheckConstraint(
            "(discount_type IS NULL AND discount_percent_value IS NULL "
            "AND discount_amount_eur IS NULL) OR "
            "(discount_type = 'PERCENT' AND discount_percent_value IS NOT NULL "
            "AND discount_amount_eur IS NULL) OR "
            "(discount_type = 'FIXED_AMOUNT' AND discount_percent_value IS NULL "
            "AND discount_amount_eur IS NOT NULL)",
            name="discount_consistency",
        ),
        CheckConstraint(
            "discount_type IS NOT NULL OR badge_tag IS NOT NULL",
            name="has_discount_or_badge",
        ),
        CheckConstraint(
            "discount_percent_value IS NULL OR discount_percent_value >= 0",
            name="discount_percent_positive",
        ),
        CheckConstraint(
            "discount_percent_value IS NULL OR discount_percent_value <= 100",
            name="discount_percent_max_100",
        ),
        CheckConstraint(
            "discount_amount_eur IS NULL OR discount_amount_eur >= 0",
            name="discount_amount_eur_positive",
        ),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at <= ends_at",
            name="activity_window_valid",
        ),
        Index(
            "uq_pricing_promotions__public_lot_id",
            "lot_id",
            unique=True,
            postgresql_where=text(
                "audience = 'PUBLIC' AND lot_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_pricing_promotions__public_category_id",
            "category_id",
            unique=True,
            postgresql_where=text(
                "audience = 'PUBLIC' AND category_id IS NOT NULL"
            ),
        ),
    )

    id: Mapped[int_pk]
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    audience: Mapped[PromotionAudience] = mapped_column(
        SQLEnum(
            PromotionAudience,
            name="pricing_promotion_audience_enum",
        ),
        default=PromotionAudience.PUBLIC,
    )
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_service_lots.id")
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_service_categories.id")
    )
    discount_type: Mapped[PromotionDiscountType | None] = mapped_column(
        SQLEnum(
            PromotionDiscountType,
            name="pricing_promotion_discount_type_enum",
        )
    )
    discount_percent_value: Mapped[int | None]
    discount_amount_eur: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2)
    )
    badge_tag: Mapped[PromotionBadgeTag | None] = mapped_column(
        SQLEnum(PromotionBadgeTag, name="pricing_promotion_badge_tag_enum")
    )
    display_priority: Mapped[int] = mapped_column(default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    personal_assignments: Mapped[list[PersonalPromotionAssignment]] = (
        relationship(
            back_populates="promotion",
            cascade="all, delete-orphan",
        )
    )
    usages: Mapped[list[PromotionUsage]] = relationship(
        back_populates="promotion",
    )


class PersonalPromotionAssignment(Base):
    __tablename__ = "pricing_personal_promotion_assignments"
    __table_args__ = (
        UniqueConstraint(
            "promotion_id",
            "user_id",
            name="uq_pricing_personal_promotion_assignments__promotion_id_user_id",
        ),
    )

    id: Mapped[int_pk]
    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_promotions.id")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    is_one_time: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promotion: Mapped[Promotion] = relationship(
        back_populates="personal_assignments",
    )


class PromotionUsage(Base):
    __tablename__ = "pricing_promotion_usages"
    __table_args__ = (
        Index(
            "ix_pricing_promotion_usages__promotion_id_user_id",
            "promotion_id",
            "user_id",
        ),
        CheckConstraint(
            "price_before_eur >= 0",
            name="price_before_eur_positive",
        ),
        CheckConstraint(
            "discount_amount_eur >= 0",
            name="discount_amount_eur_positive",
        ),
        CheckConstraint(
            "price_after_eur >= 0",
            name="price_after_eur_positive",
        ),
    )

    id: Mapped[int_pk]
    promotion_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_promotions.id")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders_orders.id"))
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    price_before_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    price_after_eur: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    promotion: Mapped[Promotion] = relationship(back_populates="usages")
