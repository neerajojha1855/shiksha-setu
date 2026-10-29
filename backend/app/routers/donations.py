import json
import logging
import uuid

import cloudinary.exceptions
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.cloudinary_client import delete_image, upload_image
from app.config import get_settings
from app.db import get_db
from app.models.donation import Donation, DonationImage, DonationStatus, DonorProfile
from app.models.school import AuditEvent
from app.models.user import User, UserRole
from app.schemas.donations import (
    DonationCreate,
    DonationResponse,
    DonationUpdate,
    DonationImageResponse,
    DonorProfileCreate,
    DonorProfileResponse,
    PublicDonationListResponse,
    PublicDonationResponse,
)

router = APIRouter(prefix="/donations", tags=["donations"])
logger = logging.getLogger(__name__)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _public_donation(row: tuple[Donation, DonorProfile]) -> PublicDonationResponse:
    donation, profile = row
    return PublicDonationResponse(
        **{column: getattr(donation, column) for column in (
            "id", "donor_id", "title", "description", "category", "quantity_available",
            "quantity_reserved", "condition", "availability", "pickup_available",
            "delivery_available", "city", "region", "status", "created_at", "updated_at",
        )},
        donor_name=profile.display_name,
        donor_organization=profile.organization,
        quantity_remaining=donation.quantity_available - donation.quantity_reserved,
    )


def _donor_profile(db: Session, user_id: uuid.UUID) -> DonorProfile:
    profile = db.scalar(select(DonorProfile).where(DonorProfile.owner_id == user_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor profile not found")
    return profile


def _owned_donation(db: Session, donation_id: uuid.UUID, user_id: uuid.UUID) -> Donation:
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.donor_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this donation")
    return donation


def _owned_image(
    db: Session, donation_id: uuid.UUID, image_id: uuid.UUID, user_id: uuid.UUID
) -> DonationImage:
    donation = _owned_donation(db, donation_id, user_id)
    image = db.scalar(
        select(DonationImage).where(
            DonationImage.id == image_id, DonationImage.donation_id == donation.id
        )
    )
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation image not found")
    return image


def _audit(db: Session, actor_id: uuid.UUID, action: str, resource_id: uuid.UUID) -> None:
    db.add(AuditEvent(
        actor_id=actor_id, action=action, resource_type="donation",
        resource_id=resource_id, details=json.dumps({}),
    ))


@router.get("", response_model=PublicDonationListResponse)
def list_donations(
    category: str | None = None,
    condition: str | None = None,
    city: str | None = None,
    region: str | None = None,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> PublicDonationListResponse:
    filters = [Donation.status == DonationStatus.active]
    if category:
        filters.append(Donation.category == category)
    if condition:
        filters.append(Donation.condition == condition)
    if city:
        filters.append(Donation.city == city)
    if region:
        filters.append(Donation.region == region)
    if search:
        filters.append(Donation.title.ilike(f"%{search}%"))
    base = select(Donation, DonorProfile).join(
        DonorProfile, DonorProfile.owner_id == Donation.donor_id
    ).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(Donation.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return PublicDonationListResponse(
        items=[_public_donation(row) for row in rows], total=total, offset=offset, limit=limit
    )


@router.get("/profile", response_model=DonorProfileResponse)
def get_donor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> DonorProfile:
    return _donor_profile(db, current_user.id)


@router.post("/profile", response_model=DonorProfileResponse, status_code=status.HTTP_201_CREATED)
def create_donor_profile(
    payload: DonorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> DonorProfile:
    if db.scalar(select(DonorProfile).where(DonorProfile.owner_id == current_user.id)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Donor profile already exists")
    profile = DonorProfile(owner_id=current_user.id, **payload.model_dump())
    db.add(profile)
    db.flush()
    _audit(db, current_user.id, "donor.profile_created", profile.id)
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/profile", response_model=DonorProfileResponse)
def update_donor_profile(
    payload: DonorProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> DonorProfile:
    profile = _donor_profile(db, current_user.id)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/mine", response_model=list[DonationResponse])
def list_own_donations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> list[Donation]:
    return list(db.scalars(
        select(Donation).where(Donation.donor_id == current_user.id).order_by(Donation.created_at.desc())
    ).all())


@router.post("", response_model=DonationResponse, status_code=status.HTTP_201_CREATED)
def create_donation(
    payload: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> Donation:
    _donor_profile(db, current_user.id)
    donation = Donation(donor_id=current_user.id, **payload.model_dump())
    db.add(donation)
    db.flush()
    _audit(db, current_user.id, "donation.created", donation.id)
    db.commit()
    db.refresh(donation)
    return donation


@router.post("/{donation_id}/images", response_model=DonationImageResponse, status_code=status.HTTP_201_CREATED)
def upload_donation_image(
    donation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> DonationImage:
    donation = _owned_donation(db, donation_id, current_user.id)
    if donation.status == DonationStatus.withdrawn:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Withdrawn donations cannot receive images")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only JPEG, PNG, and WebP images are supported")

    contents = file.file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image must be 5 MB or smaller")
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")

    settings = get_settings()
    try:
        result = upload_image(
            contents,
            folder=f"{settings.cloudinary_folder}/{current_user.id}/{donation.id}",
        )
    except cloudinary.exceptions.Error as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image upload failed") from exc

    image = DonationImage(
        donation_id=donation.id,
        asset_id=result["asset_id"],
        public_id=result["public_id"],
        secure_url=result["secure_url"],
        format=result.get("format", ""),
        bytes=result["bytes"],
        width=result.get("width", 0),
        height=result.get("height", 0),
    )
    db.add(image)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        try:
            delete_image(result["public_id"])
        except cloudinary.exceptions.Error:
            logger.exception("Cloudinary cleanup failed for %s", result["public_id"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Image metadata could not be saved") from exc
    db.refresh(image)
    return image


@router.get("/{donation_id}/images", response_model=list[DonationImageResponse])
def list_donation_images(
    donation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> list[DonationImage]:
    donation = _owned_donation(db, donation_id, current_user.id)
    return list(db.scalars(
        select(DonationImage).where(DonationImage.donation_id == donation.id).order_by(DonationImage.created_at.desc())
    ).all())


@router.delete("/{donation_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donation_image(
    donation_id: uuid.UUID,
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> None:
    image = _owned_image(db, donation_id, image_id, current_user.id)
    try:
        delete_image(image.public_id)
    except cloudinary.exceptions.Error as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image deletion failed") from exc
    db.delete(image)
    db.commit()


@router.patch("/{donation_id}", response_model=DonationResponse)
def update_donation(
    donation_id: uuid.UUID,
    payload: DonationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> Donation:
    donation = _owned_donation(db, donation_id, current_user.id)
    values = payload.model_dump(exclude_unset=True)
    if "quantity_available" in values and values["quantity_available"] < donation.quantity_reserved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Quantity cannot be less than reserved inventory")
    if donation.status == DonationStatus.withdrawn:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Withdrawn donations cannot be edited")
    for key, value in values.items():
        setattr(donation, key, value)
    _audit(db, current_user.id, "donation.updated", donation.id)
    db.commit()
    db.refresh(donation)
    return donation


@router.post("/{donation_id}/withdraw", response_model=DonationResponse)
def withdraw_donation(
    donation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.donor)),
) -> Donation:
    donation = _owned_donation(db, donation_id, current_user.id)
    if donation.status == DonationStatus.withdrawn:
        return donation
    donation.status = DonationStatus.withdrawn
    _audit(db, current_user.id, "donation.withdrawn", donation.id)
    db.commit()
    db.refresh(donation)
    return donation


@router.get("/{donation_id}", response_model=PublicDonationResponse)
def get_donation(donation_id: uuid.UUID, db: Session = Depends(get_db)) -> PublicDonationResponse:
    row = db.execute(
        select(Donation, DonorProfile)
        .join(DonorProfile, DonorProfile.owner_id == Donation.donor_id)
        .where(Donation.id == donation_id, Donation.status == DonationStatus.active)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    return _public_donation(row)
