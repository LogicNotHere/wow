from __future__ import annotations

from enum import StrEnum, auto
from datetime import datetime

from sqlalchemy import (
    JSON,
    Index,
    Enum as SQLEnum,
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
    page_fk,
)


class ServicePageStatus(StrEnum):
    DRAFT = auto()
    PUBLISHED = auto()


class Game(Base):
    __tablename__ = "catalog_games"

    id: Mapped[int_pk]
    name: Mapped[str255]
    slug: Mapped[str255] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(default=0)

    game: Mapped[Game] = relationship(back_populates="categories")
    parent: Mapped[ServiceCategory | None] = relationship(remote_side=[id])
    lots: Mapped[list[ServiceLot]] = relationship(back_populates="category")


class ServiceLot(CreateUpdateMixin, Base):
    __tablename__ = "catalog_service_lots"

    id: Mapped[int_pk]
    category_id: Mapped[category_fk]
    name: Mapped[str255]
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    base_price_eur: Mapped[float] = mapped_column(Float, default=0)
    category: Mapped[ServiceCategory] = relationship(back_populates="lots")
    options: Mapped[list[ServiceOption]] = relationship(back_populates="lot")
    page: Mapped[ServicePage | None] = relationship(
        back_populates="lot",
        uselist=False,
    )


class ServiceOption(Base):
    __tablename__ = "catalog_service_options"

    id: Mapped[int_pk]
    lot_id: Mapped[lot_fk]
    code: Mapped[str100]
    value_type: Mapped[str50]
    config_json: Mapped[dict | None] = mapped_column(JSON)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    lot: Mapped[ServiceLot] = relationship(back_populates="options")


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
