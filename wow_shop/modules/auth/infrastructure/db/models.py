from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from wow_shop.infrastructure.db.base import Base


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    BANNED = "banned"


class UserRole(str, PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    CONTENT_MANAGER = "content_manager"


class BoosterTier(str, PyEnum):
    BOOSTER = "booster"
    SUPER_BOOSTER = "super_booster"


class BoosterApprovalStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class User(Base):
    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="auth_user_status_enum"),
        default=UserStatus.ACTIVE,
    )
    staff_role: Mapped[UserRole | None] = mapped_column(
        Enum(UserRole, name="auth_user_staff_role_enum")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    booster_profile: Mapped[BoosterProfile | None] = relationship(
        back_populates="user",
        uselist=False,
    )


class BoosterProfile(Base):
    __tablename__ = "auth_booster_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("auth_users.id"),
        primary_key=True,
    )
    approval_status: Mapped[BoosterApprovalStatus] = mapped_column(
        Enum(
            BoosterApprovalStatus,
            name="auth_booster_profile_approval_status_enum",
        ),
        default=BoosterApprovalStatus.DRAFT,
    )
    tier: Mapped[BoosterTier] = mapped_column(
        Enum(BoosterTier, name="auth_booster_profile_tier_enum"),
        default=BoosterTier.BOOSTER,
    )
    discord_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="booster_profile")


class AdminNote(Base):
    __tablename__ = "auth_admin_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    author_admin_id: Mapped[int] = mapped_column(ForeignKey("auth_users.id"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
