from __future__ import annotations

from enum import StrEnum, auto

from sqlalchemy import Enum as SQLEnum, Text, ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column

from wow_shop.infrastructure.db.base import Base
from wow_shop.infrastructure.db.mixins import (
    CreateUpdateMixin,
    CreatedAtMixin,
    CreatedByMixin,
)
from wow_shop.infrastructure.db.types import int_pk, str255


class UserStatus(StrEnum):
    ACTIVE = auto()
    BANNED = auto()


class UserRole(StrEnum):
    CUSTOMER = auto()
    BOOSTER = auto()
    ADMIN = auto()
    MANAGER = auto()
    OPERATOR = auto()
    CONTENT_MANAGER = auto()


class BoosterTier(StrEnum):
    BOOSTER = auto()
    SUPER_BOOSTER = auto()


class BoosterApprovalStatus(StrEnum):
    DRAFT = auto()
    PENDING = auto()
    APPROVED = auto()
    DECLINED = auto()


class User(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "auth_users"

    id: Mapped[int_pk]
    email: Mapped[str255 | None] = mapped_column(unique=True)
    password_hash: Mapped[str255 | None]
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, name="auth_user_status_enum"),
        default=UserStatus.ACTIVE,
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="auth_user_role_enum"),
        default=UserRole.CUSTOMER,
    )
    booster_profile: Mapped[BoosterProfile | None] = relationship(
        back_populates="user",
        uselist=False,
    )


class BoosterProfile(CreateUpdateMixin, Base):
    __tablename__ = "auth_booster_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id"),
        primary_key=True,
    )
    approval_status: Mapped[BoosterApprovalStatus] = mapped_column(
        SQLEnum(
            BoosterApprovalStatus,
            name="auth_booster_profile_approval_status_enum",
        ),
        default=BoosterApprovalStatus.DRAFT,
    )
    tier: Mapped[BoosterTier] = mapped_column(
        SQLEnum(BoosterTier, name="auth_booster_profile_tier_enum"),
        default=BoosterTier.BOOSTER,
    )
    discord_url: Mapped[str255 | None]
    user: Mapped[User] = relationship(back_populates="booster_profile")


class AdminNote(CreatedAtMixin, CreatedByMixin, Base):
    __tablename__ = "auth_admin_notes"

    id: Mapped[int_pk]
    target_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    author_admin_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    note: Mapped[str] = mapped_column(Text)
