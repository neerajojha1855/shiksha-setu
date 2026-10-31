import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MatchStatus(str, enum.Enum):
    proposed = "proposed"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class DonationMatch(Base):
    __tablename__ = "donation_matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    need_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("school_needs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("donations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    match_factors: Mapped[str] = mapped_column(Text(), nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status"), default=MatchStatus.proposed,
        nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
