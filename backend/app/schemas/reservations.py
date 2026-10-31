import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.reservation import ReservationStatus


class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    quantity: int
    status: ReservationStatus
    created_at: datetime
    updated_at: datetime
