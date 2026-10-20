import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.models.need import Need, NeedStatus
from app.models.school import AuditEvent, School, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.needs import (
    NeedCreate,
    NeedResponse,
    NeedUpdate,
    PublicNeedListResponse,
    PublicNeedResponse,
)

router = APIRouter(prefix="/needs", tags=["needs"])


def _public_need(item: tuple[Need, School]) -> PublicNeedResponse:
    need, school = item
    return PublicNeedResponse(
        **{column: getattr(need, column) for column in (
            "id", "school_id", "title", "description", "category",
            "quantity_requested", "quantity_fulfilled", "condition",
            "urgency", "priority", "intended_use", "city", "region",
            "status", "created_at", "updated_at",
        )},
        school_name=school.name,
        school_verification_status=school.verification_status.value,
        fulfillment_percent=min(
            100, round(need.quantity_fulfilled / need.quantity_requested * 100)
        ),
    )


def _school_for_user(db: Session, user_id: uuid.UUID) -> School:
    school = db.scalar(select(School).where(School.owner_id == user_id))
    if school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School profile not found")
    return school


def _need_or_404(db: Session, need_id: uuid.UUID) -> Need:
    need = db.get(Need, need_id)
    if need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    return need


def _record_audit(
    db: Session, actor_id: uuid.UUID, action: str, need_id: uuid.UUID, details: dict[str, str] | None = None
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor_id,
            action=action,
            resource_type="school_need",
            resource_id=need_id,
            details=json.dumps(details) if details else None,
        )
    )


def _owned_need(db: Session, need_id: uuid.UUID, user_id: uuid.UUID) -> Need:
    need = _need_or_404(db, need_id)
    school = db.get(School, need.school_id)
    if school is None or school.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this need")
    return need


@router.post("", response_model=NeedResponse, status_code=status.HTTP_201_CREATED)
def create_need(
    payload: NeedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Need:
    school = _school_for_user(db, current_user.id)
    need = Need(school_id=school.id, **payload.model_dump())
    db.add(need)
    db.flush()
    _record_audit(db, current_user.id, "school_need.created", need.id)
    db.commit()
    db.refresh(need)
    return need


@router.get("", response_model=list[NeedResponse])
def list_published_needs(
    category: str | None = None,
    urgency: str | None = None,
    priority: str | None = None,
    city: str | None = None,
    region: str | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Need]:
    query = select(Need).where(Need.status == NeedStatus.published)
    if category:
        query = query.where(Need.category == category)
    if urgency:
        query = query.where(Need.urgency == urgency)
    if priority:
        query = query.where(Need.priority == priority)
    if city:
        query = query.where(Need.city == city)
    if region:
        query = query.where(Need.region == region)
    if search:
        query = query.where(Need.title.ilike(f"%{search}%"))
    return list(db.scalars(query.order_by(Need.created_at.desc()).offset(offset).limit(limit)).all())


@router.get("/discover", response_model=PublicNeedListResponse)
def discover_needs(
    category: str | None = None,
    urgency: str | None = None,
    priority: str | None = None,
    city: str | None = None,
    region: str | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PublicNeedListResponse:
    filters = [
        Need.status == NeedStatus.published,
        School.verification_status == VerificationStatus.approved,
    ]
    if category:
        filters.append(Need.category == category)
    if urgency:
        filters.append(Need.urgency == urgency)
    if priority:
        filters.append(Need.priority == priority)
    if city:
        filters.append(Need.city == city)
    if region:
        filters.append(Need.region == region)
    if search:
        term = f"%{search}%"
        filters.append(
            or_(
                Need.title.ilike(term),
                Need.description.ilike(term),
                Need.category.ilike(term),
                School.name.ilike(term),
            )
        )
    total = db.scalar(
        select(func.count(Need.id)).join(School, School.id == Need.school_id).where(*filters)
    ) or 0
    rows = db.execute(
        select(Need, School)
        .join(School, School.id == Need.school_id)
        .where(*filters)
        .order_by(Need.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return PublicNeedListResponse(
        items=[_public_need(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.patch("/{need_id}", response_model=NeedResponse)
def update_need(
    need_id: uuid.UUID,
    payload: NeedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Need:
    need = _owned_need(db, need_id, current_user.id)
    if need.status is NeedStatus.closed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Closed needs cannot be edited")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("quantity_requested", need.quantity_requested) < need.quantity_fulfilled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Requested quantity cannot be less than fulfilled quantity",
        )
    for field, value in changes.items():
        setattr(need, field, value)
    db.flush()
    _record_audit(db, current_user.id, "school_need.updated", need.id)
    db.commit()
    db.refresh(need)
    return need


def _transition_need(
    need_id: uuid.UUID,
    target: NeedStatus,
    action: str,
    db: Session,
    current_user: User,
) -> Need:
    need = _owned_need(db, need_id, current_user.id)
    if target is NeedStatus.published:
        school = db.get(School, need.school_id)
        if school is None or school.verification_status is not VerificationStatus.approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only approved schools can publish needs",
            )
        if need.status not in {NeedStatus.draft, NeedStatus.paused}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Need cannot be published from its current state")
    elif target is NeedStatus.paused:
        if need.status is not NeedStatus.published:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only published needs can be paused")
    elif target is NeedStatus.closed:
        if need.status is NeedStatus.closed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Need is already closed")
    need.status = target
    db.flush()
    _record_audit(db, current_user.id, action, need.id, {"status": target.value})
    db.commit()
    db.refresh(need)
    return need


@router.post("/{need_id}/publish", response_model=NeedResponse)
def publish_need(
    need_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Need:
    return _transition_need(need_id, NeedStatus.published, "school_need.published", db, current_user)


@router.post("/{need_id}/pause", response_model=NeedResponse)
def pause_need(
    need_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Need:
    return _transition_need(need_id, NeedStatus.paused, "school_need.paused", db, current_user)


@router.post("/{need_id}/close", response_model=NeedResponse)
def close_need(
    need_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Need:
    return _transition_need(need_id, NeedStatus.closed, "school_need.closed", db, current_user)


@router.get("/school/mine", response_model=list[NeedResponse])
def list_own_needs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> list[Need]:
    school = _school_for_user(db, current_user.id)
    return list(
        db.scalars(select(Need).where(Need.school_id == school.id).order_by(Need.created_at.desc())).all()
    )


@router.get("/{need_id}", response_model=PublicNeedResponse)
def get_need(need_id: uuid.UUID, db: Session = Depends(get_db)) -> Need:
    row = db.execute(
        select(Need, School)
        .join(School, School.id == Need.school_id)
        .where(
            Need.id == need_id,
            Need.status == NeedStatus.published,
            School.verification_status == VerificationStatus.approved,
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    return _public_need(row)
