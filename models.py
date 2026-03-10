from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    BANNED = "banned"


class UserRole(str, PyEnum):
    CUSTOMER = "customer"
    BOOSTER = "booster"
    ADMIN = "admin"
    OPERATOR = "operator"


class BoosterTier(str, PyEnum):
    BOOSTER = "booster"
    SUPER_BOOSTER = "super_booster"


class BoosterApprovalStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class BoosterCategory(str, PyEnum):
    MYTHIC_PLUS = "mythic_plus"
    RAID = "raid"
    PVP = "pvp"
    PROFESSIONS = "professions"


class OrderStatus(str, PyEnum):
    CREATED = "created"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    NEEDS_ADMIN_REVIEW = "needs_admin_review"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REQUIREMENTS_PENDING = "requirements_pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CLOSED = "closed"
    CANCELED = "canceled"
    DISPUTED = "disputed"
    REFUNDED = "refunded"
    PARTIAL_REFUND = "partial_refund"


class ExecutionMode(str, PyEnum):
    SELF_PLAY = "self_play"
    PILOTED = "piloted"
    ANYDESK = "anydesk"


class PromotionScope(str, PyEnum):
    CATEGORY = "category"
    LOT = "lot"


class PromotionType(str, PyEnum):
    DISCOUNT_PERCENT = "discount_percent"
    DISCOUNT_FIXED = "discount_fixed"
    TAG_ONLY = "tag_only"


class PricingScope(str, PyEnum):
    CATEGORY = "category"
    LOT = "lot"


class ClaimStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class DisputeStatus(str, PyEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"


class RefundType(str, PyEnum):
    FULL = "full"
    PARTIAL = "partial"


class PaymentStatus(str, PyEnum):
    CONFIRMED = "confirmed"
    CANCELED = "canceled"


class ServicePageStatus(str, PyEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class NotificationChannel(str, PyEnum):
    IN_APP = "in_app"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    EMAIL = "email"


class NotificationStatus(str, PyEnum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    roles: Mapped[list["UserRoleAssignment"]] = relationship(                                                             # для мультирольности ?
        back_populates="user",
        foreign_keys="UserRoleAssignment.user_id",
    )
    booster_profile: Mapped["BoosterProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
    )

class UserRoleAssignment(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), primary_key=True)
    granted_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="roles")


class BoosterProfile(Base):
    __tablename__ = "booster_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    approval_status: Mapped[BoosterApprovalStatus] = mapped_column(                                                     # тут ли должна быть заявка
        Enum(BoosterApprovalStatus),
        default=BoosterApprovalStatus.DRAFT,
    )
    tier: Mapped[BoosterTier] = mapped_column(Enum(BoosterTier), default=BoosterTier.BOOSTER)
    # booster_category: Mapped[BoosterCategory] = mapped_column(Enum(BoosterCategory))
    # can_manage_calendar: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_url: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="booster_profile")


class AdminNote(Base):
    __tablename__ = "admin_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ServiceCategory(Base):
    __tablename__ = "service_categories"
    __table_args__ = (UniqueConstraint("parent_id", "slug", name="uq_category_parent_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("service_categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    parent: Mapped["ServiceCategory | None"] = relationship(remote_side=[id])


class ServiceLot(Base):
    __tablename__ = "service_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # booster_category: Mapped[BoosterCategory] = mapped_column(Enum(BoosterCategory))   для сортировки по категориям бустеру
    execution_modes_allowed: Mapped[list[str] | None] = mapped_column(JSON)
    # tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class ServicePage(Base):
    __tablename__ = "service_pages"
    __table_args__ = (UniqueConstraint("lot_id", name="uq_service_page_lot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("service_lots.id"))
    status: Mapped[ServicePageStatus] = mapped_column(Enum(ServicePageStatus), default=ServicePageStatus.DRAFT)
    title: Mapped[str | None] = mapped_column(String(255))
    meta_json: Mapped[dict | None] = mapped_column(JSON)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ServicePageBlock(Base):
    __tablename__ = "service_page_blocks"
    __table_args__ = (UniqueConstraint("page_id", "position", name="uq_page_block_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("service_pages.id"))
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(50))
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# class PageBlockTypeSchema(Base):
#     __tablename__ = "page_block_type_schemas"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     /type: Mapped[str] = mapped_column(String(50), unique=True)
#     schema_json: Mapped[dict] = mapped_column(JSON)
#     version: Mapped[int] = mapped_column(Integer, default=1)
#     is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ServiceOption(Base):
    __tablename__ = "service_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("service_lots.id"))
    code: Mapped[str] = mapped_column(String(100))
    value_type: Mapped[str] = mapped_column(String(50))
    config_json: Mapped[dict | None] = mapped_column(JSON)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class PricingRuleSet(Base):
    __tablename__ = "pricing_rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[PricingScope] = mapped_column(Enum(PricingScope))
    scope_id: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    rules_json: Mapped[dict | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope_type: Mapped[PromotionScope] = mapped_column(Enum(PromotionScope))
    scope_id: Mapped[int] = mapped_column(Integer)
    promo_type: Mapped[PromotionType] = mapped_column(Enum(PromotionType))
    value: Mapped[float | None] = mapped_column(Float)
    tag: Mapped[str | None] = mapped_column(String(50))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class GuestContact(Base):
    __tablename__ = "guest_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(50))
    value: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MagicLink(Base):
    __tablename__ = "magic_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    token_hash: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(String(50), default="read_only")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("public_number", name="uq_order_public_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_number: Mapped[str] = mapped_column(String(32))
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus))
    execution_mode: Mapped[ExecutionMode] = mapped_column(Enum(ExecutionMode))

    customer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    guest_contact_id: Mapped[int | None] = mapped_column(ForeignKey("guest_contacts.id"))
    booster_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    service_lot_id: Mapped[int] = mapped_column(ForeignKey("service_lots.id"))
    selected_options_json: Mapped[dict | None] = mapped_column(JSON)
    price_snapshot_json: Mapped[dict | None] = mapped_column(JSON)                                                      #нужно ли хранить это прям джсоном?

    booster_character_text: Mapped[str | None] = mapped_column(String(255))
    internal_note: Mapped[str | None] = mapped_column(Text)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    paid_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    in_progress_at: Mapped[datetime | None] = mapped_column(DateTime)
    done_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class OrderClaim(Base):
    __tablename__ = "order_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    booster_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.PENDING)
    decided_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (Index("ix_order_claims_order_id", "order_id"),)


# class OrderTimelineEvent(Base):                                                                                       перенасыщение
#     __tablename__ = "order_timeline_events"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
#     event_type: Mapped[str] = mapped_column(String(100))
#     actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
#     payload_json: Mapped[dict | None] = mapped_column(JSON)
#     created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
#
#     __table_args__ = (Index("ix_order_timeline_order_id", "order_id"),)


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.CONFIRMED)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    confirmed_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# class Dispute(Base):                                                                                                  перенасыщение
#     __tablename__ = "disputes"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
#     status: Mapped[DisputeStatus] = mapped_column(Enum(DisputeStatus), default=DisputeStatus.OPEN)
#     reason: Mapped[str | None] = mapped_column(Text)
#     opened_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
#     resolved_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
#     resolution_json: Mapped[dict | None] = mapped_column(JSON)
#     created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
#     resolved_at: Mapped[datetime | None] = mapped_column(DateTime)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    type: Mapped[RefundType] = mapped_column(Enum(RefundType))
    amount_eur: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("thread_id", "user_id", name="uq_chat_participant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role_in_thread: Mapped[str] = mapped_column(String(20))                                                             #для того что бы отображать в чате роль и не делать каждый рпз запрос
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("chat_threads.id"))
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    attachment_url: Mapped[str | None] = mapped_column(String(1024))                                                    #для скринов? (дублирование логики)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# class NotificationEndpoint(Base):
#     __tablename__ = "notification_endpoints"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
#     channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
#     endpoint_value: Mapped[str] = mapped_column(String(255))
#     is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
#
#
# class SystemNotification(Base):
#     __tablename__ = "system_notifications"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     event_type: Mapped[str] = mapped_column(String(100))
#     target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
#     channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
#     payload_json: Mapped[dict | None] = mapped_column(JSON)
#     status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.QUEUED)
#     created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
#     sent_at: Mapped[datetime | None] = mapped_column(DateTime)
#
#
# class InAppNotification(Base):
#     __tablename__ = "in_app_notifications"
#
#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
#     title: Mapped[str] = mapped_column(String(255))
#     body: Mapped[str | None] = mapped_column(Text)
#     payload_json: Mapped[dict | None] = mapped_column(JSON)
#     is_read: Mapped[bool] = mapped_column(Boolean, default=False)
#     created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
#     expires_at: Mapped[datetime] = mapped_column(DateTime)

