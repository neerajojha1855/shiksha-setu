import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.user import AuthSession, User, UserRole

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_password: str) -> bool:
    return password_hash.verify(password, encoded_password)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _encode_access_token(user: User) -> str:
    settings = get_settings()
    now = _utc_now()
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_session(db: Session, user: User) -> str:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            user_id=user.id,
            refresh_token_hash=_hash_refresh_token(raw_token),
            expires_at=_utc_now() + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    return raw_token


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    return _encode_access_token(user), create_refresh_session(db, user)


def issue_access_token(user: User) -> str:
    return _encode_access_token(user)


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    normalized_identifier = identifier.strip().lower()
    user = db.scalar(
        select(User).where(
            (User.email == normalized_identifier)
            | (User.username == identifier.strip())
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def get_user_from_access_token(token: str, db: Session) -> User:
    settings = get_settings()
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError, jwt.PyJWTError) as exc:
        raise credentials_error from exc

    if payload.get("type") != "access":
        raise credentials_error
    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    return get_user_from_access_token(token, db)


def revoke_refresh_session(db: Session, raw_token: str) -> None:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == _hash_refresh_token(raw_token)
        )
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = _utc_now()


def rotate_refresh_session(db: Session, raw_token: str) -> tuple[User, str]:
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == _hash_refresh_token(raw_token)
        )
    )
    now = _utc_now()
    if (
        session is None
        or session.revoked_at is not None
        or _as_utc(session.expires_at) <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh session",
        )
    session.revoked_at = now
    return user, create_refresh_session(db, user)


def ensure_supported_registration_role(role: UserRole) -> UserRole:
    if role is UserRole.administrator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator accounts must be provisioned by an administrator",
        )
    return role
