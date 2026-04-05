from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    JSON,
    Index,
    Enum as SQLEnum,
    ForeignKey,
    Text,
    Float,
    Boolean,
    DateTime,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import CreateUpdateMixin
from wow_shop.infrastructure.db.types import int_pk, str100, str255, str50
from wow_shop.modules.catalog.infrastructure.db.types import (
    category_fk,
    category_parent_fk,
    game_fk,
    lot_fk,
    option_fk,
    option_value_fk,
    page_fk,
)


class ServicePageStatus(StrEnum):
    DRAFT = auto()
    PUBLISHED = auto()


class LotOptionInputType(StrEnum):
    CHECKBOX = auto()
    RADIO = auto()
    SELECT = auto()
    MULTISELECT = auto()


class ServiceLotStatus(StrEnum):
    DRAFT = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DELETED = auto()


class GameStatus(StrEnum):
    DRAFT = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DELETED = auto()


class ServiceCategoryStatus(StrEnum):
    DRAFT = auto()
    ACTIVE = auto()
    INACTIVE = auto()
    DELETED = auto()


class Game(Base):
    __tablename__ = "catalog_games"

    id: Mapped[int_pk]
    name: Mapped[str255]
    slug: Mapped[str255] = mapped_column(unique=True)
    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(GameStatus, name="catalog_game_status_enum"),
        default=GameStatus.DRAFT,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    sort_order: Mapped[int] = mapped_column(default=0)

    categories: Mapped[list[ServiceCategory]] = relationship(
        back_populates="game"
    )


class ServiceCategory(Base):
    __tablename__ = "catalog_service_categories"
    __table_args__ = (
        UniqueConstraint("game_id", "parent_id", "slug"),
        Index(
            "uq_catalog_service_categories__game_id_slug__root",
            "game_id",
            "slug",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
        ),
    )

    id: Mapped[int_pk]
    game_id: Mapped[game_fk]
    name: Mapped[str255]
    slug: Mapped[str255]
    parent_id: Mapped[category_parent_fk | None]
    status: Mapped[ServiceCategoryStatus] = mapped_column(
        SQLEnum(
            ServiceCategoryStatus,
            name="catalog_service_category_status_enum",
        ),
        default=ServiceCategoryStatus.DRAFT,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    sort_order: Mapped[int] = mapped_column(default=0)

    game: Mapped[Game] = relationship(back_populates="categories")
    parent: Mapped[ServiceCategory | None] = relationship(
        remote_side="ServiceCategory.id"
    )
    lots: Mapped[list[ServiceLot]] = relationship(back_populates="category")


class ServiceLot(CreateUpdateMixin, Base):
    __tablename__ = "catalog_service_lots"
    __table_args__ = (UniqueConstraint("category_id", "slug"),)

    id: Mapped[int_pk]
    category_id: Mapped[category_fk]
    name: Mapped[str255]
    slug: Mapped[str255]
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ServiceLotStatus] = mapped_column(
        SQLEnum(ServiceLotStatus, name="catalog_service_lot_status_enum"),
        default=ServiceLotStatus.DRAFT,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    base_price_eur: Mapped[float] = mapped_column(Float, default=0)
    category: Mapped[ServiceCategory] = relationship(back_populates="lots")
    options: Mapped[list[LotOption]] = relationship(
        back_populates="lot",
        cascade="all, delete-orphan",
    )
    page: Mapped[ServicePage | None] = relationship(
        back_populates="lot",
        uselist=False,
    )


class LotOption(CreateUpdateMixin, Base):
    __tablename__ = "catalog_lot_options"
    __table_args__ = (UniqueConstraint("lot_id", "code"),)

    id: Mapped[int_pk]
    lot_id: Mapped[lot_fk]
    label: Mapped[str255]
    code: Mapped[str100]
    input_type: Mapped[LotOptionInputType] = mapped_column(
        SQLEnum(LotOptionInputType, name="catalog_lot_option_input_type_enum"),
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    depends_on_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_lot_options.id")
    )
    depends_on_value_id: Mapped[option_value_fk | None]

    lot: Mapped[ServiceLot] = relationship(back_populates="options")
    values: Mapped[list[LotOptionValue]] = relationship(
        back_populates="option",
        cascade="all, delete-orphan",
    )


class LotOptionValue(CreateUpdateMixin, Base):
    __tablename__ = "catalog_lot_option_values"
    __table_args__ = (UniqueConstraint("option_id", "code"),)

    id: Mapped[int_pk]
    option_id: Mapped[option_fk]
    label: Mapped[str255]
    code: Mapped[str100]
    description: Mapped[str | None] = mapped_column(Text)
    price_value: Mapped[float] = mapped_column(Float, default=0)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    option: Mapped[LotOption] = relationship(back_populates="values")


class ServicePage(CreateUpdateMixin, Base):
    __tablename__ = "catalog_service_pages"
    __table_args__ = (UniqueConstraint("lot_id"),)

    id: Mapped[int_pk]
    lot_id: Mapped[lot_fk]
    status: Mapped[ServicePageStatus] = mapped_column(
        SQLEnum(ServicePageStatus, name="catalog_service_page_status_enum"),
        default=ServicePageStatus.DRAFT,
    )
    title: Mapped[str255 | None]
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    lot: Mapped[ServiceLot] = relationship(back_populates="page")
    blocks: Mapped[list[ServicePageBlock]] = relationship(back_populates="page")


class ServicePageBlock(CreateUpdateMixin, Base):
    __tablename__ = "catalog_service_page_blocks"
    __table_args__ = (UniqueConstraint("page_id", "position"),)

    id: Mapped[int_pk]
    page_id: Mapped[page_fk]
    position: Mapped[int]
    type: Mapped[str50]
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    page: Mapped[ServicePage] = relationship(back_populates="blocks")
