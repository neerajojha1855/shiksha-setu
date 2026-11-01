import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DistributionStatus(str, enum.Enum):
    reserved = "reserved"
    in_transit = "in_transit"
    delivered_pending_confirmation = "delivered_pending_confirmation"
    received = "received"
    verified = "verified"
    cancelled = "cancelled"
    rejected = "rejected"


class Distribution(Base):
    __tablename__ = "distributions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("donation_reservations.id", ondelete="CASCADE"), unique=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_method: Mapped[str | None] = mapped_column(String(80))
    tracking_reference: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text())
    status: Mapped[DistributionStatus] = mapped_column(
        Enum(DistributionStatus, name="distribution_status"),
        default=DistributionStatus.reserved,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DistributionTransition(Base):
    __tablename__ = "distribution_transitions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    distribution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("distributions.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    from_status: Mapped[DistributionStatus | None] = mapped_column(
        Enum(DistributionStatus, name="distribution_status", create_type=False)
    )
    to_status: Mapped[DistributionStatus] = mapped_column(
        Enum(DistributionStatus, name="distribution_status", create_type=False), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
