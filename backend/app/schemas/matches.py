import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.match import MatchStatus


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    need_id: uuid.UUID
    donation_id: uuid.UUID
    score: int
    match_factors: dict[str, str | int | bool]
    explanation: str
    status: MatchStatus
    created_at: datetime
    updated_at: datetime


class MatchWithDetails(MatchResponse):
    need_title: str
    donation_title: str
    quantity_remaining: int
    need_city: str
    need_region: str
    donation_city: str
    donation_region: str
