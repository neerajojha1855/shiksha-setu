import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.school import VerificationStatus


class SchoolProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    city: str = Field(min_length=2, max_length=100)
    region: str = Field(min_length=2, max_length=100)
    website: HttpUrl | None = None


class SchoolProfileResponse(SchoolProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    verification_status: VerificationStatus
    created_at: datetime
    updated_at: datetime


class VerificationSubmission(BaseModel):
    registration_reference: str = Field(min_length=2, max_length=160)
    evidence_description: str = Field(min_length=10, max_length=4000)


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    submitted_by: uuid.UUID
    registration_reference: str
    evidence_description: str
    status: VerificationStatus
    decision_reason: str | None
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class VerificationDecision(BaseModel):
    status: Literal[VerificationStatus.approved, VerificationStatus.rejected]
    reason: str = Field(min_length=3, max_length=2000)


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: uuid.UUID
    details: str | None
    created_at: datetime
