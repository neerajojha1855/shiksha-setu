import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.need import NeedStatus


class NeedCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=4000)
    category: str = Field(min_length=2, max_length=80)
    quantity_requested: int = Field(gt=0, le=1_000_000)
    condition: str = Field(min_length=2, max_length=80)
    urgency: str = Field(min_length=2, max_length=40)
    priority: str = Field(min_length=2, max_length=40)
    intended_use: str = Field(min_length=2, max_length=2000)
    city: str = Field(min_length=2, max_length=100)
    region: str = Field(min_length=2, max_length=100)


class NeedUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=4000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    quantity_requested: int | None = Field(default=None, gt=0, le=1_000_000)
    condition: str | None = Field(default=None, min_length=2, max_length=80)
    urgency: str | None = Field(default=None, min_length=2, max_length=40)
    priority: str | None = Field(default=None, min_length=2, max_length=40)
    intended_use: str | None = Field(default=None, min_length=2, max_length=2000)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    region: str | None = Field(default=None, min_length=2, max_length=100)


class NeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    title: str
    description: str
    category: str
    quantity_requested: int
    quantity_fulfilled: int
    condition: str
    urgency: str
    priority: str
    intended_use: str
    city: str
    region: str
    status: NeedStatus
    created_at: datetime
    updated_at: datetime

