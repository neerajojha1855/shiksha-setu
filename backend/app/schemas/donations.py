import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.donation import DonationStatus


class DonorProfileCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    organization: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=2000)
    city: str = Field(min_length=2, max_length=100)
    region: str = Field(min_length=2, max_length=100)


class DonorProfileResponse(DonorProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DonationCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=4000)
    category: str = Field(min_length=2, max_length=80)
    quantity_available: int = Field(gt=0, le=1_000_000)
    condition: str = Field(min_length=2, max_length=80)
    availability: str = Field(min_length=2, max_length=80)
    pickup_available: bool = False
    delivery_available: bool = False
    city: str = Field(min_length=2, max_length=100)
    region: str = Field(min_length=2, max_length=100)


class DonationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=4000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    quantity_available: int | None = Field(default=None, gt=0, le=1_000_000)
    condition: str | None = Field(default=None, min_length=2, max_length=80)
    availability: str | None = Field(default=None, min_length=2, max_length=80)
    pickup_available: bool | None = None
    delivery_available: bool | None = None
    city: str | None = Field(default=None, min_length=2, max_length=100)
    region: str | None = Field(default=None, min_length=2, max_length=100)


class DonationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donor_id: uuid.UUID
    title: str
    description: str
    category: str
    quantity_available: int
    quantity_reserved: int
    condition: str
    availability: str
    pickup_available: bool
    delivery_available: bool
    city: str
    region: str
    status: DonationStatus
    created_at: datetime
    updated_at: datetime


class PublicDonationResponse(DonationResponse):
    donor_name: str
    donor_organization: str | None
    quantity_remaining: int


class PublicDonationListResponse(BaseModel):
    items: list[PublicDonationResponse]
    total: int
    offset: int
    limit: int
