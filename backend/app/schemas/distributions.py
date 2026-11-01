import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.distribution import DistributionStatus


class DistributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reservation_id: uuid.UUID
    quantity: int
    delivery_method: str | None
    tracking_reference: str | None
    notes: str | None
    status: DistributionStatus
    created_at: datetime
    updated_at: datetime


class DistributionTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    distribution_id: uuid.UUID
    actor_id: uuid.UUID
    from_status: DistributionStatus | None
    to_status: DistributionStatus
    note: str | None
    created_at: datetime
