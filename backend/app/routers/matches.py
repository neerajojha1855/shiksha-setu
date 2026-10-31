import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.db import get_db
from app.matching import evaluate_match
from app.models.donation import Donation, DonationStatus
from app.models.match import DonationMatch, MatchStatus
from app.models.need import Need, NeedStatus
from app.routers.reservations import _reserve_match
from app.models.school import AuditEvent, School, VerificationStatus
from app.models.user import User, UserRole
from app.schemas.matches import MatchResponse, MatchWithDetails

router = APIRouter(prefix="/matches", tags=["matches"])


def _match_response(match: DonationMatch) -> MatchResponse:
    return MatchResponse(
        id=match.id,
        need_id=match.need_id,
        donation_id=match.donation_id,
        score=match.score,
        match_factors=json.loads(match.match_factors),
        explanation=match.explanation,
        status=match.status,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


def _school_owned_need(db: Session, need_id: uuid.UUID, user_id: uuid.UUID) -> Need:
    need = db.get(Need, need_id)
    if need is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Need not found")
    school = db.get(School, need.school_id)
    if school is None or school.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this need")
    return need


def _donor_owned_donation(db: Session, donation_id: uuid.UUID, user_id: uuid.UUID) -> Donation:
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.donor_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this donation")
    return donation


def _audit(db: Session, actor_id: uuid.UUID, action: str, match_id: uuid.UUID) -> None:
    db.add(AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_type="donation_match",
        resource_id=match_id,
        details=json.dumps({}),
    ))


def _match_or_404(db: Session, match_id: uuid.UUID) -> DonationMatch:
    match = db.get(DonationMatch, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


def _authorized_match(db: Session, match_id: uuid.UUID, user: User) -> DonationMatch:
    match = _match_or_404(db, match_id)
    need = db.get(Need, match.need_id)
    donation = db.get(Donation, match.donation_id)
    if need is None or donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    school = db.get(School, need.school_id)
    if school is None or (school.owner_id != user.id and donation.donor_id != user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this match")
    return match


@router.post("/generate/{need_id}", response_model=list[MatchResponse])
def generate_matches(
    need_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> list[MatchResponse]:
    need = _school_owned_need(db, need_id, current_user.id)
    school = db.get(School, need.school_id)
    if need.status is not NeedStatus.published or school is None or school.verification_status is not VerificationStatus.approved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only published needs from approved schools can be matched")

    donations = db.scalars(select(Donation).where(Donation.status == DonationStatus.active)).all()
    results: list[DonationMatch] = []
    for donation in donations:
        evaluation = evaluate_match(need, donation)
        if evaluation is None:
            continue
        existing = db.scalar(select(DonationMatch).where(
            DonationMatch.need_id == need.id, DonationMatch.donation_id == donation.id
        ))
        if existing is None:
            match = DonationMatch(
                need_id=need.id,
                donation_id=donation.id,
                score=evaluation.score,
                match_factors=json.dumps(evaluation.factors),
                explanation=evaluation.explanation,
                status=MatchStatus.proposed,
            )
            db.add(match)
            results.append(match)
        elif existing.status in {MatchStatus.proposed, MatchStatus.expired}:
            existing.score = evaluation.score
            existing.match_factors = json.dumps(evaluation.factors)
            existing.explanation = evaluation.explanation
            existing.status = MatchStatus.proposed
            results.append(existing)
    db.flush()
    for match in results:
        _audit(db, current_user.id, "donation_match.proposed", match.id)
    db.commit()
    return [_match_response(match) for match in sorted(results, key=lambda item: item.score, reverse=True)]


@router.get("/need/{need_id}", response_model=list[MatchWithDetails])
def list_need_matches(
    need_id: uuid.UUID,
    include_rejected: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.school)),
) -> list[MatchWithDetails]:
    need = _school_owned_need(db, need_id, current_user.id)
    query = select(DonationMatch, Donation).join(Donation, Donation.id == DonationMatch.donation_id).where(
        DonationMatch.need_id == need.id
    )
    if not include_rejected:
        query = query.where(DonationMatch.status != MatchStatus.rejected)
    rows = db.execute(query.order_by(DonationMatch.score.desc(), DonationMatch.created_at.desc())).all()
    return [
        MatchWithDetails(
            **_match_response(match).model_dump(),
            need_title=need.title,
            donation_title=donation.title,
            quantity_remaining=donation.quantity_available - donation.quantity_reserved,
            need_city=need.city,
            need_region=need.region,
            donation_city=donation.city,
            donation_region=donation.region,
        )
        for match, donation in rows
    ]


@router.get("/mine", response_model=list[MatchWithDetails])
def list_donor_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> list[MatchResponse]:
    rows = db.execute(
        select(DonationMatch, Donation, Need)
        .join(Donation, Donation.id == DonationMatch.donation_id)
        .join(Need, Need.id == DonationMatch.need_id)
        .where(Donation.donor_id == current_user.id, DonationMatch.status != MatchStatus.rejected)
        .order_by(DonationMatch.score.desc(), DonationMatch.created_at.desc())
    ).all()
    return [
        MatchWithDetails(
            **_match_response(match).model_dump(),
            need_title=need.title,
            donation_title=donation.title,
            quantity_remaining=donation.quantity_available - donation.quantity_reserved,
            need_city=need.city,
            need_region=need.region,
            donation_city=donation.city,
            donation_region=donation.region,
        )
        for match, donation, need in rows
    ]


@router.post("/{match_id}/accept", response_model=MatchResponse)
def accept_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school)),
) -> MatchResponse:
    match = _authorized_match(db, match_id, current_user)
    if match.status is not MatchStatus.proposed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only proposed matches can be accepted")
    _reserve_match(db, match.id, current_user.id)
    db.commit()
    db.refresh(match)
    return _match_response(match)


@router.post("/{match_id}/reject", response_model=MatchResponse)
def reject_match(
    match_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor, UserRole.school)),
) -> MatchResponse:
    match = _authorized_match(db, match_id, current_user)
    if match.status is not MatchStatus.proposed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only proposed matches can be rejected")
    match.status = MatchStatus.rejected
    _audit(db, current_user.id, "donation_match.rejected", match.id)
    db.commit()
    db.refresh(match)
    return _match_response(match)
