import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.models.distribution import Distribution, DistributionStatus, DistributionTransition
from app.models.donation import Donation
from app.models.match import DonationMatch
from app.models.need import Need
from app.models.reservation import DonationReservation, ReservationStatus
from app.models.school import School
from app.models.user import User, UserRole
from app.schemas.distributions import DistributionResponse, DistributionTransitionResponse

router = APIRouter(prefix="/distributions", tags=["distributions"])


def _distribution_or_404(db: Session, distribution_id: uuid.UUID) -> Distribution:
    distribution = db.get(Distribution, distribution_id)
    if distribution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution not found")
    return distribution


def _authorized_distribution(db: Session, distribution_id: uuid.UUID, user: User) -> Distribution:
    distribution = _distribution_or_404(db, distribution_id)
    row = db.execute(
        select(Donation, School)
        .select_from(DonationReservation)
        .join(DonationMatch, DonationMatch.id == DonationReservation.match_id)
        .join(Donation, Donation.id == DonationMatch.donation_id)
        .join(Need, Need.id == DonationMatch.need_id)
        .join(School, School.id == Need.school_id)
        .where(DonationReservation.id == distribution.reservation_id)
    ).first()
    if row is None or (row[0].donor_id != user.id and row[1].owner_id != user.id and user.role not in {UserRole.volunteer, UserRole.administrator}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this distribution")
    return distribution


def _transition(
    db: Session,
    distribution_id: uuid.UUID,
    actor: User,
    target: DistributionStatus,
    allowed_roles: set[UserRole],
    note: str | None,
) -> Distribution:
    if actor.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot perform this distribution transition")
    distribution = db.scalar(
        select(Distribution).where(Distribution.id == distribution_id).with_for_update()
    )
    if distribution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Distribution not found")
    _authorized_distribution(db, distribution_id, actor)
    if distribution.status is target:
        return distribution
    allowed: dict[DistributionStatus, set[DistributionStatus]] = {
        DistributionStatus.reserved: {DistributionStatus.in_transit, DistributionStatus.cancelled},
        DistributionStatus.in_transit: {
            DistributionStatus.delivered_pending_confirmation,
            DistributionStatus.cancelled,
        },
        DistributionStatus.delivered_pending_confirmation: {
            DistributionStatus.received,
            DistributionStatus.rejected,
        },
        DistributionStatus.received: {DistributionStatus.verified, DistributionStatus.rejected},
        DistributionStatus.verified: set(),
        DistributionStatus.cancelled: set(),
        DistributionStatus.rejected: set(),
    }
    if target not in allowed[distribution.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Distribution cannot move from {distribution.status.value} to {target.value}",
        )
    previous = distribution.status
    distribution.status = target
    reservation = db.get(DonationReservation, distribution.reservation_id)
    if reservation is not None and target is DistributionStatus.verified:
        reservation.status = ReservationStatus.fulfilled
    if reservation is not None and target is DistributionStatus.cancelled:
        donation = db.scalar(
            select(Donation)
            .join(DonationMatch, DonationMatch.donation_id == Donation.id)
            .where(DonationMatch.id == reservation.match_id)
            .with_for_update()
        )
        need = db.scalar(
            select(Need)
            .join(DonationMatch, DonationMatch.need_id == Need.id)
            .where(DonationMatch.id == reservation.match_id)
            .with_for_update()
        )
        if reservation.status is ReservationStatus.reserved:
            if donation is not None:
                donation.quantity_reserved = max(0, donation.quantity_reserved - reservation.quantity)
            if need is not None:
                need.quantity_fulfilled = max(0, need.quantity_fulfilled - reservation.quantity)
        reservation.status = ReservationStatus.cancelled
    db.add(DistributionTransition(
        distribution_id=distribution.id,
        actor_id=actor.id,
        from_status=previous,
        to_status=target,
        note=note,
    ))
    db.commit()
    db.refresh(distribution)
    return distribution


@router.get("/mine", response_model=list[DistributionResponse])
def list_my_distributions(
    include_terminal: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school, UserRole.volunteer, UserRole.administrator)),
) -> list[Distribution]:
    query = (
        select(Distribution)
        .join(DonationReservation, DonationReservation.id == Distribution.reservation_id)
        .join(DonationMatch, DonationMatch.id == DonationReservation.match_id)
        .join(Donation, Donation.id == DonationMatch.donation_id)
        .join(Need, Need.id == DonationMatch.need_id)
        .join(School, School.id == Need.school_id)
    )
    if current_user.role not in {UserRole.volunteer, UserRole.administrator}:
        query = query.where(or_(Donation.donor_id == current_user.id, School.owner_id == current_user.id))
    if not include_terminal:
        query = query.where(
            Distribution.status.notin_(
                {DistributionStatus.verified, DistributionStatus.cancelled, DistributionStatus.rejected}
            )
        )
    return list(db.scalars(query.order_by(Distribution.created_at.desc())).all())


@router.get("/{distribution_id}/history", response_model=list[DistributionTransitionResponse])
def distribution_history(
    distribution_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school, UserRole.volunteer, UserRole.administrator)),
) -> list[DistributionTransition]:
    _authorized_distribution(db, distribution_id, current_user)
    return list(db.scalars(
        select(DistributionTransition)
        .where(DistributionTransition.distribution_id == distribution_id)
        .order_by(DistributionTransition.created_at.asc())
    ).all())


@router.post("/{distribution_id}/dispatch", response_model=DistributionResponse)
def dispatch_distribution(
    distribution_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school, UserRole.volunteer)),
) -> Distribution:
    return _transition(db, distribution_id, current_user, DistributionStatus.in_transit, {UserRole.donor, UserRole.school, UserRole.volunteer}, note)


@router.post("/{distribution_id}/mark-delivered", response_model=DistributionResponse)
def mark_delivered(
    distribution_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school, UserRole.volunteer)),
) -> Distribution:
    return _transition(db, distribution_id, current_user, DistributionStatus.delivered_pending_confirmation, {UserRole.donor, UserRole.school, UserRole.volunteer}, note)


@router.post("/{distribution_id}/confirm-receipt", response_model=DistributionResponse)
def confirm_receipt(
    distribution_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> Distribution:
    return _transition(db, distribution_id, current_user, DistributionStatus.received, {UserRole.school}, note)


@router.post("/{distribution_id}/verify", response_model=DistributionResponse)
def verify_distribution(
    distribution_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> Distribution:
    return _transition(db, distribution_id, current_user, DistributionStatus.verified, {UserRole.administrator}, note)


@router.post("/{distribution_id}/cancel", response_model=DistributionResponse)
def cancel_distribution(
    distribution_id: uuid.UUID,
    note: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school, UserRole.volunteer)),
) -> Distribution:
    return _transition(db, distribution_id, current_user, DistributionStatus.cancelled, {UserRole.donor, UserRole.school, UserRole.volunteer}, note)
