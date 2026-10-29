from functools import lru_cache

import cloudinary
import cloudinary.exceptions
import cloudinary.uploader
from fastapi import HTTPException, status

from app.config import get_settings


@lru_cache
def configure_cloudinary() -> None:
    settings = get_settings()
    if not all((
        settings.cloudinary_cloud_name,
        settings.cloudinary_api_key,
        settings.cloudinary_api_secret,
    )):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image uploads are not configured",
        )
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload_image(file_object, *, folder: str) -> dict:
    configure_cloudinary()
    return cloudinary.uploader.upload(
        file_object,
        folder=folder,
        resource_type="image",
        overwrite=False,
        unique_filename=True,
        use_filename=False,
    )


def delete_image(public_id: str) -> None:
    configure_cloudinary()
    cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)
