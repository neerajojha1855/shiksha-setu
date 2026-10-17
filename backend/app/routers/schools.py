import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_administrator, require_roles
from app.db import get_db
from app.models.school import AuditEvent, School, SchoolVerificationRecord, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.schools import (
    AuditEventResponse,
    SchoolProfileCreate,
    SchoolProfileResponse,
    VerificationDecision,
    VerificationResponse,
    VerificationSubmission,
)

router = APIRouter(prefix="/schools", tags=["schools"])
admin_router = APIRouter(prefix="/admin", tags=["administration"])


def _school_or_404(db: Session, owner_id: uuid.UUID) -> School:
    school = db.scalar(select(School).where(School.owner_id == owner_id))
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School profile not found")
    return school


def _record_audit(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID,
    details: dict[str, str] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
        )
    )


@router.post("/profile", response_model=SchoolProfileResponse, status_code=status.HTTP_201_CREATED)
def create_school_profile(
    payload: SchoolProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> School:
    existing = db.scalar(select(School).where(School.owner_id == current_user.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="School profile already exists")
    school = School(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        city=payload.city,
        region=payload.region,
        website=str(payload.website) if payload.website else None,
    )
    db.add(school)
    db.flush()
    _record_audit(db, current_user.id, "school.profile_created", "school", school.id)
    db.commit()
    db.refresh(school)
    return school


@router.get("/profile", response_model=SchoolProfileResponse)
def get_school_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> School:
    return _school_or_404(db, current_user.id)


@router.post("/profile/verification", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def submit_school_verification(
    payload: VerificationSubmission,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> SchoolVerificationRecord:
    school = _school_or_404(db, current_user.id)
    pending = db.scalar(
        select(SchoolVerificationRecord).where(
            SchoolVerificationRecord.school_id == school.id,
            SchoolVerificationRecord.status == VerificationStatus.pending,
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A verification submission is already pending review",
        )
    record = SchoolVerificationRecord(
        school_id=school.id,
        submitted_by=current_user.id,
        registration_reference=payload.registration_reference,
        evidence_description=payload.evidence_description,
        status=VerificationStatus.pending,
    )
    school.verification_status = VerificationStatus.pending
    db.add(record)
    db.flush()
    _record_audit(db, current_user.id, "school.verification_submitted", "school_verification", record.id)
    db.commit()
    db.refresh(record)
    return record


@router.get("/profile/verifications", response_model=list[VerificationResponse])
def list_own_verifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> list[SchoolVerificationRecord]:
    school = _school_or_404(db, current_user.id)
    return list(
        db.scalars(
            select(SchoolVerificationRecord)
            .where(SchoolVerificationRecord.school_id == school.id)
            .order_by(SchoolVerificationRecord.created_at.desc())
        ).all()
    )


@admin_router.get("/school-verifications", response_model=list[VerificationResponse])
def list_school_verifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_administrator()),
) -> list[SchoolVerificationRecord]:
    return list(
        db.scalars(
            select(SchoolVerificationRecord).order_by(SchoolVerificationRecord.created_at.asc())
        ).all()
    )


@admin_router.post(
    "/school-verifications/{verification_id}/decision",
    response_model=VerificationResponse,
)
def decide_school_verification(
    verification_id: uuid.UUID,
    payload: VerificationDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_administrator()),
) -> SchoolVerificationRecord:
    record = db.get(SchoolVerificationRecord, verification_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification submission not found")
    if record.status is not VerificationStatus.pending:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verification submission was already decided")
    school = db.get(School, record.school_id)
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School profile not found")
    now = datetime.now(timezone.utc)
    record.status = payload.status
    record.decision_reason = payload.reason
    record.reviewed_by = current_user.id
    record.reviewed_at = now
    school.verification_status = payload.status
    db.flush()
    _record_audit(
        db,
        current_user.id,
        f"school.verification_{payload.status.value}",
        "school_verification",
        record.id,
        {"reason": payload.reason},
    )
    db.commit()
    db.refresh(record)
    return record


@admin_router.get("/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_administrator()),
) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc())).all())
