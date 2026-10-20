import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class NeedStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    paused = "paused"
    closed = "closed"


class Need(Base):
    __tablename__ = "school_needs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_fulfilled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    condition: Mapped[str] = mapped_column(String(80), nullable=False)
    urgency: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    intended_use: Mapped[str] = mapped_column(Text(), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[NeedStatus] = mapped_column(
        Enum(NeedStatus, name="need_status"),
        default=NeedStatus.draft,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
