import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.models.donation import Donation
from app.models.match import DonationMatch, MatchStatus
from app.models.need import Need
from app.models.reservation import DonationReservation, ReservationStatus
from app.models.school import AuditEvent, School
from app.models.user import User, UserRole
from app.schemas.reservations import ReservationResponse

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _authorized_match(db: Session, match_id: uuid.UUID, user: User) -> DonationMatch:
    match = db.get(DonationMatch, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    need = db.get(Need, match.need_id)
    donation = db.get(Donation, match.donation_id)
    school = db.get(School, need.school_id) if need else None
    if need is None or donation is None or school is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    if school.owner_id != user.id and donation.donor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this reservation")
    return match


def _reserve_match(db: Session, match_id: uuid.UUID, actor_id: uuid.UUID) -> DonationReservation:
    match = db.scalar(
        select(DonationMatch).where(DonationMatch.id == match_id).with_for_update()
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    existing = db.scalar(
        select(DonationReservation).where(DonationReservation.match_id == match.id)
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This match already has a reservation")
    if match.status is not MatchStatus.proposed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only proposed matches can be reserved")

    need = db.scalar(select(Need).where(Need.id == match.need_id).with_for_update())
    donation = db.scalar(select(Donation).where(Donation.id == match.donation_id).with_for_update())
    if need is None or donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match resources not found")
    donation_remaining = donation.quantity_available - donation.quantity_reserved
    need_remaining = need.quantity_requested - need.quantity_fulfilled
    quantity = min(donation_remaining, need_remaining)
    if quantity <= 0 or donation.status.value != "active" or need.status.value != "published":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No inventory remains for this reservation")

    reservation = DonationReservation(match_id=match.id, quantity=quantity)
    donation.quantity_reserved += quantity
    need.quantity_fulfilled += quantity
    match.status = MatchStatus.accepted
    db.add(reservation)
    db.flush()
    db.add(AuditEvent(
        actor_id=actor_id,
        action="donation.reserved",
        resource_type="donation_reservation",
        resource_id=reservation.id,
        details=json.dumps({"match_id": str(match.id), "quantity": quantity}),
    ))
    return reservation


@router.post("/matches/{match_id}", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def reserve_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school)),
) -> DonationReservation:
    match = _authorized_match(db, match_id, current_user)
    reservation = _reserve_match(db, match.id, current_user.id)
    db.commit()
    db.refresh(reservation)
    return reservation


@router.get("/mine", response_model=list[ReservationResponse])
def list_my_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school)),
) -> list[DonationReservation]:
    rows = db.execute(
        select(DonationReservation)
        .join(DonationMatch, DonationMatch.id == DonationReservation.match_id)
        .join(Donation, Donation.id == DonationMatch.donation_id)
        .join(Need, Need.id == DonationMatch.need_id)
        .join(School, School.id == Need.school_id)
        .where((Donation.donor_id == current_user.id) | (School.owner_id == current_user.id))
        .order_by(DonationReservation.created_at.desc())
    ).scalars().all()
    return list(rows)
