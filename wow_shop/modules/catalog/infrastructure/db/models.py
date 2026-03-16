from __future__ import annotations

from enum import Enum as PyEnum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Enum,
    Text,
    Float,
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, relationship, mapped_column

from wow_shop.infrastructure.db.base import Base


class ServicePageStatus(str, PyEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ServiceCategory(Base):
    __tablename__ = "catalog_service_categories"
    __table_args__ = (UniqueConstraint("parent_id", "slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_service_categories.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped[ServiceCategory | None] = relationship(remote_side=[id])


class ServiceLot(Base):
    __tablename__ = "catalog_service_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_service_categories.id")
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    base_price_eur: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    options: Mapped[list[ServiceOption]] = relationship(back_populates="lot")
    page: Mapped[ServicePage | None] = relationship(
        back_populates="lot",
        uselist=False,
    )


class ServiceOption(Base):
    __tablename__ = "catalog_service_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("catalog_service_lots.id"))
    code: Mapped[str] = mapped_column(String(100))
    value_type: Mapped[str] = mapped_column(String(50))
    config_json: Mapped[dict | None] = mapped_column(JSON)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    lot: Mapped[ServiceLot] = relationship(back_populates="options")


class ServicePage(Base):
    __tablename__ = "catalog_service_pages"
    __table_args__ = (UniqueConstraint("lot_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_service_lots.id"),
    )
    status: Mapped[ServicePageStatus] = mapped_column(
        Enum(ServicePageStatus, name="catalog_service_page_status_enum"),
        default=ServicePageStatus.DRAFT,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    lot: Mapped[ServiceLot] = relationship(back_populates="page")
    blocks: Mapped[list[ServicePageBlock]] = relationship(back_populates="page")


class ServicePageBlock(Base):
    __tablename__ = "catalog_service_page_blocks"
    __table_args__ = (UniqueConstraint("page_id", "position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("catalog_service_pages.id"))
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50))
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    page: Mapped[ServicePage] = relationship(back_populates="blocks")
